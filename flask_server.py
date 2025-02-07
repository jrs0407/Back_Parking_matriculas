import cv2
import tempfile
import os
from flask import Flask, request, jsonify
import requests
import re
import logging

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)

# URL de tu servicio OpenALPR (ajusta según tu contenedor/puerto)
OPENALPR_URL = "http://localhost:5000/recognize"

# URL de tu servidor de plazas (placas.py)
PLATES_SERVICE_URL = "http://localhost:6000/api/spots"

def get_best_plate(output_text):
    """
    Extrae y devuelve la matrícula con mayor confianza de la respuesta de OpenALPR.
    """
    plate_candidates = []
    output_lines = output_text.split("\n")

    # Buscamos líneas con: "-    ABC123  confidence: 89.9"
    plate_regex = r"-\s+([A-Z0-9]+)\s+confidence:\s+([\d\.]+)"

    for line in output_lines:
        match = re.search(plate_regex, line)
        if match:
            plate, confidence = match.groups()
            plate_candidates.append((plate, float(confidence)))
            logging.debug(f"Encontrada placa: {plate} con confianza: {confidence}")

    if plate_candidates:
        plate_candidates.sort(key=lambda x: x[1], reverse=True)
        best_plate, confidence = plate_candidates[0]
        logging.info(f"Mejor placa: {best_plate} con confianza: {confidence}")
        return {"best_plate": best_plate, "confidence": confidence}
    else:
        logging.warning("No se detectó ninguna placa.")
        return {"best_plate": None, "confidence": 0}


@app.route("/process_plate", methods=["POST"])
def process_plate():
    """
    Recibe una imagen en form-data con clave "file".
    La envía a OpenALPR y si hay una matrícula, la registra en placas.py.
    """
    if "file" not in request.files:
        logging.error("No se encontró el archivo en la solicitud.")
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    files = {"file": (file.filename, file.stream, file.mimetype)}

    try:
        response = requests.post(OPENALPR_URL, files=files)
        logging.debug(f"Respuesta de OpenALPR: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Error al comunicarse con OpenALPR: {e}")
        return jsonify({"error": "Failed to connect to OpenALPR"}), 500

    if response.status_code == 200:
        try:
            response_json = response.json()
            logging.debug(f"JSON de respuesta de OpenALPR: {response_json}")
        except ValueError:
            logging.error("Respuesta de OpenALPR no es un JSON válido.")
            return jsonify({"error": "Invalid response from OpenALPR"}), 500

        output = response_json.get("output", "")
        plate_data = get_best_plate(output)
        best_plate = plate_data["best_plate"]

        if best_plate:
            # Intentar registrar la plaza en placas.py
            try:
                r = requests.post(PLATES_SERVICE_URL, json={"plate": best_plate})
                if r.status_code == 409:
                    # Significa que esa matrícula ya está en el parking
                    logging.info(f"La matrícula {best_plate} ya estaba en el parking (409 Conflict).")
                else:
                    # Si no es 409, verificar si hay otro error
                    r.raise_for_status()
                    logging.info(f"Plaza creada para {best_plate} en placas.py.")
            except requests.RequestException as e:
                logging.error(f"No se pudo crear la plaza en placas.py: {e}")

        return jsonify(plate_data), 200
    else:
        logging.error(f"OpenALPR respondió con error: {response.status_code}")
        return jsonify({"error": "OpenALPR failed"}), 500


@app.route("/process_video", methods=["POST"])
def process_video():
    """
    Recibe un video (form-data clave "video"), extrae fotogramas cada X frames,
    envía a OpenALPR, y registra cada matrícula detectada en placas.py 
    (si no está ya ocupada).
    """
    if "video" not in request.files:
        logging.error("No se encontró el archivo de video en la solicitud.")
        return jsonify({"error": "No video uploaded"}), 400

    video_file = request.files["video"]
    temp_dir = tempfile.gettempdir()
    temp_video_path = os.path.join(temp_dir, video_file.filename)
    video_file.save(temp_video_path)

    cap = cv2.VideoCapture(temp_video_path)
    if not cap.isOpened():
        logging.error("No se pudo abrir el video con OpenCV.")
        return jsonify({"error": "Failed to open video"}), 500

    frame_count = 0
    plates_detected = []
    frame_skip = 10  # Ajusta según quieras

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # Fin del video

        if frame_count % frame_skip == 0:
            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                logging.error("No se pudo codificar el fotograma.")
                frame_count += 1
                continue

            files = {"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")}

            try:
                response = requests.post(OPENALPR_URL, files=files)
            except requests.RequestException as e:
                logging.error(f"Error al comunicarse con OpenALPR: {e}")
                frame_count += 1
                continue

            if response.status_code == 200:
                try:
                    response_json = response.json()
                except ValueError:
                    logging.error("OpenALPR no devolvió JSON válido.")
                    frame_count += 1
                    continue

                output = response_json.get("output", "")
                plate_data = get_best_plate(output)
                best_plate = plate_data["best_plate"]
                confidence = plate_data["confidence"]

                if best_plate:
                    # Intentar registrar la plaza en placas.py
                    try:
                        r = requests.post(PLATES_SERVICE_URL, json={"plate": best_plate})
                        if r.status_code == 409:
                            logging.info(f"Matrícula {best_plate} ya estaba en el parking (409).")
                        else:
                            r.raise_for_status()
                            logging.info(f"Plaza creada para {best_plate}.")
                    except requests.RequestException as e:
                        logging.error(f"No se pudo crear la plaza en placas.py: {e}")

                plates_detected.append({
                    "frame": frame_count,
                    "plate": best_plate,
                    "confidence": confidence
                })
            else:
                logging.error(f"OpenALPR error en frame {frame_count}: {response.status_code}")

        frame_count += 1

    cap.release()
    if os.path.exists(temp_video_path):
        os.remove(temp_video_path)

    return jsonify({"plates_detected": plates_detected}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
