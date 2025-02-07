from fastapi import FastAPI, File, UploadFile
import subprocess
import shutil
import os

app = FastAPI()

@app.post("/recognize")
async def recognize_plate(file: UploadFile = File(...)):
    file_location = f"/tmp/{file.filename}"

    # Guardar la imagen temporalmente
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Ejecutar OpenALPR sobre la imagen
    # command = f"alpr -c us {file_location}" # USA
    command = f"alpr -c eu {file_location}"
    process = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Eliminar la imagen después de procesarla
    os.remove(file_location)

    return {"output": process.stdout.strip()}
