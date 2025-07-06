# This Dockerfile is for the TTS SERVICE ONLY

FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required by piper-tts and wget
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file for this specific service
# (Ensure you have a requirements.txt in the tts_service directory)
COPY requirements.txt .

# Install Python dependencies for this service
RUN pip install --no-cache-dir -r requirements.txt

# --- Download and Extract the Model ---
# Create a directory for the model, download the files, and return to /app
RUN mkdir -p /app/models/en_GB-semaine-medium && \
    cd /app/models/en_GB-semaine-medium && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx.json && \
    cd /app

# Copy the server script into the container
COPY tts_server.py .

# Expose the port the server will run on
EXPOSE 5001

# --- CORRECTED COMMAND ---
# Run the script directly with python to ensure the __main__ block is executed,
# which contains the logic for loading SSL certificates.
CMD ["python", "tts_server.py"]