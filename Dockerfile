FROM ubuntu:20.04

# Configurar la zona horaria de forma no interactiva
ENV DEBIAN_FRONTEND=noninteractive
RUN ln -fs /usr/share/zoneinfo/Europe/Madrid /etc/localtime && \
    echo "Europe/Madrid" > /etc/timezone

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libopencv-dev \
    libtesseract-dev \
    libleptonica-dev \
    tesseract-ocr \
    wget \
    python3 \
    python3-pip \
    libcurl4-openssl-dev \
    liblog4cplus-dev

# Clonar y compilar OpenALPR
WORKDIR /opt
RUN git clone https://github.com/openalpr/openalpr.git && \
    cd openalpr/src && \
    mkdir build && cd build && \
    cmake .. && make -j$(nproc) && make install && \
    ldconfig

# Instalar FastAPI, Uvicorn y python-multipart
RUN pip3 install fastapi uvicorn python-multipart

WORKDIR /app
COPY app.py /app/app.py

# Exponer el puerto 5000
EXPOSE 5000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
