# **📌 Explicación del Funcionamiento de la API de OpenALPR y Flask**

En este proyecto, **OpenALPR** es el motor de reconocimiento de matrículas, y **Flask** actúa como un servidor HTTP intermediario para procesar y filtrar los resultados. Vamos a desglosar cómo funciona cada parte.

---

## **📌 1️⃣ ¿Cómo Funciona OpenALPR?**
### **🛠️ Descripción de OpenALPR**
OpenALPR (**Open Automatic License Plate Recognition**) es una herramienta de reconocimiento automático de matrículas basado en **OCR (Reconocimiento Óptico de Caracteres)** y **Machine Learning**.

**📌 Funciones clave:**
- Procesa imágenes y detecta matrículas en diferentes países.
- Devuelve **varias posibles matrículas** con diferentes niveles de **confianza**.
- Es rápido y eficiente, y puede ejecutarse en **Docker** o como aplicación nativa.

### **📝 Ejemplo de Uso de OpenALPR en la Línea de Comandos**
Si tienes una imagen llamada `matricula.jpg`, puedes analizarla con:
```bash
alpr -c us matricula.jpg
```
Salida esperada:
```bash
plate0: 10 results
    - 0724   confidence: 84.0282
    - B0724  confidence: 80.9354
    - 80724  confidence: 76.3656
    - 30724  confidence: 76.0828
```
Aquí, OpenALPR ha detectado **10 posibles matrículas** con distintos niveles de confianza.

### **📡 OpenALPR como API HTTP en Docker**
En lugar de ejecutarlo manualmente, lo corremos como un servicio en un contenedor Docker:
```bash
docker run -d -p 5000:5000 --name openalpr-api openalpr-api
```
Esto nos permite **enviar imágenes a OpenALPR** a través de una API HTTP.

📌 **Ejemplo de llamada a la API HTTP de OpenALPR**:
```bash
curl -X POST -F "file=@matricula.jpg" http://localhost:5000/recognize
```
Salida esperada:
```json
{
  "output": "plate0: 10 results\n
    - 0724   confidence: 84.0282\n
    - B0724  confidence: 80.9354\n
    - 80724  confidence: 76.3656\n"
}
```
El problema es que **OpenALPR devuelve múltiples opciones y necesitamos elegir la mejor**. Para eso, usamos Flask.

---

## **📌 2️⃣ ¿Cómo Funciona el Servidor Flask?**
### **🌐 Flask como Servidor HTTP Intermediario**
Flask nos permite construir un **servidor HTTP** que:
1. **Recibe imágenes** a través de una API (`/process_plate`).
2. **Envía las imágenes a OpenALPR**.
3. **Filtra el mejor resultado** basándose en la confianza.
4. **Devuelve una respuesta limpia** con solo la mejor matrícula.

### **📡 Cómo Flask Se Comunica con OpenALPR**
1. Un cliente envía una imagen a Flask (`POST /process_plate`).
2. Flask reenvía la imagen a OpenALPR (`POST /recognize` en el contenedor Docker).
3. Flask analiza la respuesta y extrae la **mejor matrícula**.
4. Devuelve un **JSON** con la mejor matrícula y su confianza.

---

## **📌 3️⃣ Explicación del Código en `flask_server.py`**
### **1️⃣ Recibir la imagen**
📌 En Flask, el endpoint `/process_plate` recibe una imagen como un **archivo multipart/form-data**.
```python
@app.route("/process_plate", methods=["POST"])
def process_plate():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
```
🔹 **Si no hay archivo**, devuelve un error `400`.

---

### **2️⃣ Enviar la imagen a OpenALPR**
📌 Flask reenvía la imagen a la API de OpenALPR.
```python
file = request.files["file"]
files = {"file": (file.filename, file.stream, file.mimetype)}
response = requests.post(OPENALPR_URL, files=files)
```
🔹 `requests.post(OPENALPR_URL, files=files)` envía la imagen a OpenALPR.  
🔹 `OPENALPR_URL = "http://localhost:5000/recognize"` es la API que corre en Docker.

---

### **3️⃣ Filtrar el mejor resultado**
📌 Flask analiza la respuesta de OpenALPR y selecciona **la matrícula con mayor confianza**:
```python
def get_best_plate(response_text):
    plate_candidates = []
    output_lines = response_text.split("\n")

    plate_regex = r"-\s+([A-Z0-9]+)\s+confidence:\s+([\d\.]+)"

    for line in output_lines:
        match = re.search(plate_regex, line)
        if match:
            plate, confidence = match.groups()
            plate_candidates.append((plate, float(confidence)))

    if plate_candidates:
        plate_candidates.sort(key=lambda x: x[1], reverse=True)
        best_plate, confidence = plate_candidates[0]
        return {"best_plate": best_plate, "confidence": confidence}
    else:
        return {"best_plate": "No plate detected", "confidence": 0}
```
🔹 **Extrae solo líneas que contengan matrículas y confianza** usando **expresiones regulares (`re.search`)**.  
🔹 **Ordena por confianza** (`sort(key=lambda x: x[1], reverse=True)`).  
🔹 **Devuelve la mejor opción** o `"No plate detected"` si no hay matrículas.

---

### **4️⃣ Devolver el resultado en JSON**
📌 Una vez extraída la mejor matrícula, Flask la devuelve como JSON.
```python
if response.status_code == 200:
    plate_data = get_best_plate(response.text)
    return jsonify(plate_data)
else:
    return jsonify({"error": "OpenALPR failed"}), 500
```
🔹 Si OpenALPR responde correctamente (`200 OK`), se procesa la matrícula.  
🔹 Si hay un error (`500`), Flask informa que OpenALPR falló.

---

## **📌 4️⃣ Ejemplo de Uso**
### **Enviar una imagen a Flask**
```bash
curl -X POST -F "file=@matricula.jpg" http://localhost:8080/process_plate
```
Salida esperada:
```json
{
  "best_plate": "0724",
  "confidence": 84.0282
}
```
Si OpenALPR no detecta nada:
```json
{
  "best_plate": "No plate detected",
  "confidence": 0
}
```

---

## **📌 5️⃣ Beneficios de Esta Arquitectura**
✅ **Separación de responsabilidades** → OpenALPR solo detecta matrículas, Flask las procesa.  
✅ **Flexibilidad** → Se puede mejorar el filtrado en Flask sin tocar OpenALPR.  
✅ **Escalabilidad** → Flask puede enviar peticiones a OpenALPR en servidores distintos.  
✅ **Mantenimiento más fácil** → Si OpenALPR falla, solo Flask necesita manejar errores.  

🚀 **¡Ahora tienes una API robusta para reconocer matrículas!** 🚗💨