FROM python:3.11-slim
WORKDIR /app

# Install system libraries needed for model download (wget) and audio (libsndfile1)
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 wget && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the directory for the models and download them into the image
RUN mkdir -p /app/models/en_GB-semaine-medium && \
    cd /app/models/en_GB-semaine-medium && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx.json && \
    cd /app

# Copy the application code
COPY ./app .

# Expose the port the service runs on
EXPOSE 5001

# Use gunicorn to run the application. It looks for the 'app' object in the 'main.py' file.
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:5001", "main:app"]