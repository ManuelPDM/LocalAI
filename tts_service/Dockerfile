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
COPY requirements.txt .

# Install Python dependencies for this service
RUN pip install --no-cache-dir -r requirements.txt

# --- Download and Extract the Model ---
# Create a directory for the specific model
RUN mkdir -p /app/models/en_GB-semaine-medium
WORKDIR /app/models/en_GB-semaine-medium

# Download the two required model files directly from Hugging Face
RUN wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx
RUN wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx.json

# Return to the main app directory
WORKDIR /app

# Copy the server script into the container
COPY tts_server.py .

# Expose the port the server will run on
EXPOSE 5001

# Command to run the TTS server, explicitly pointing to the app
CMD ["flask", "--app", "tts_server", "run", "--host=0.0.0.0", "--port=5001"]