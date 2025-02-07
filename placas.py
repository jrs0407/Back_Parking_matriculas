from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Base de datos en memoria (lista de plazas)
spots_data = []

@app.route('/api/spots', methods=['GET'])
def get_spots():
    """
    Devuelve la lista de todas las plazas registradas en memoria.
    """
    return jsonify(spots_data), 200

@app.route('/api/spots', methods=['POST'])
def create_spot():
    """
    Crea una plaza nueva con la matrícula dada y estado "occupied".
    Espera un JSON con { "plate": "XYZ-1234" }.

    - Si la matrícula ya existe en status "occupied", devolvemos 409 (conflicto).
    - Si no existe, se crea la nueva plaza y se responde con 201.
    """
    data = request.json
    if not data or 'plate' not in data:
        return jsonify({"error": "No plate provided"}), 400

    plate = data["plate"]

    # Comprobar si ya existe esa matrícula con estado "occupied"
    existing_spot = next((
        s for s in spots_data
        if s["plate"] == plate and s["status"] == "occupied"
    ), None)

    if existing_spot:
        # Matrícula ya está dentro del parking, no creamos otra plaza
        return jsonify({"error": "Plate already in parking"}), 409

    # Si no existe, crear plaza
    new_id = len(spots_data) + 1
    new_spot = {
        "id": new_id,
        "plate": plate,
        "status": "occupied"
    }
    spots_data.append(new_spot)

    return jsonify(new_spot), 201


@app.route('/api/spots/<int:spot_id>', methods=['GET'])
def get_spot(spot_id):
    """
    Devuelve la información de una plaza específica, si existe.
    """
    spot = next((s for s in spots_data if s["id"] == spot_id), None)
    if not spot:
        return jsonify({"error": "Spot not found"}), 404
    return jsonify(spot), 200

# (Opcional) Ruta para liberar la plaza
@app.route('/api/spots/<int:spot_id>/exit', methods=['POST'])
def exit_spot(spot_id):
    """
    Marca la plaza como 'free' (simulando que el vehículo salió).
    """
    spot = next((s for s in spots_data if s["id"] == spot_id), None)
    if not spot:
        return jsonify({"error": "Spot not found"}), 404

    spot["status"] = "free"
    return jsonify({"message": "Spot is now free", "spot": spot}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)
