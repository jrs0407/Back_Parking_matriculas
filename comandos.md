## **📌 Cómo Construir y Ejecutar el Contenedor**
Después de actualizar el `Dockerfile`, vuelve a **compilar y ejecutar** el contenedor:

```bash
# Construir la imagen
docker build -t openalpr-api .

# Ejecutar el contenedor
docker run -d -p 5000:5000 --name openalpr-api openalpr-api
```

### **📌 ¿Qué Hace Este Código?**
✅ **Filtra la salida de OpenALPR** para extraer solo los resultados con formato de matrícula.  
✅ **Usa expresiones regulares (`re`)** para encontrar líneas con **matrícula y confianza**.  
✅ **Ordena los resultados por confianza** y devuelve la mejor coincidencia.  
✅ Si no encuentra ninguna matrícula, devuelve `"No plate detected"`.

---
5. **Prueba la API otra vez**:
   ```bash
   curl -X POST -F "file=@matricula.jpg" http://localhost:5000/recognize
   ```

### Probar la API de Flask

```bash
 curl -X POST -F "file=@matricula2.jpg" http://localhost:8080/process_plate
 ```
Respuesta:

```bash
{
  "best_plate": "3245LCX",
  "confidence": 92.2743
}
```