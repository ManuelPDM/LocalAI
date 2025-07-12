from flask import Flask, request, send_file, Response
from flask_cors import CORS
from piper.voice import PiperVoice
import io
import logging
import wave
import os
import sys

# Set up detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# --- Model Loading ---
MODEL_PATH = '/app/models/en_GB-semaine-medium/en_GB-semaine-medium.onnx'
CONFIG_PATH = f"{MODEL_PATH}.json"

logger.info("--- Piper TTS Server Initialization ---")
logger.info(f"Model path: {MODEL_PATH}")
logger.info(f"Config path: {CONFIG_PATH}")

voice = None

try:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found at: {CONFIG_PATH}")

    # --- START: THE FINAL FIX ---
    # Explicitly specify the 'CPUExecutionProvider'. This forces ONNX Runtime to use its most
    # stable, non-optimized code path and prevents it from auto-detecting CPU features
    # that may be causing the silent failure in the virtualized environment.
    logger.info("Attempting to load PiperVoice with explicit 'CPUExecutionProvider' to ensure VM compatibility.")
    onnx_providers = ['CPUExecutionProvider']
    voice = PiperVoice.load(MODEL_PATH, config_path=CONFIG_PATH, use_cuda=False, onnx_providers=onnx_providers)
    # --- END: THE FINAL FIX ---

    logger.info("PiperVoice.load() completed successfully.")

except Exception as e:
    logger.exception("FATAL: An exception occurred during model loading.")


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    if not voice:
        logger.error("TTS request received, but model is not loaded.")
        return Response("TTS model is not available.", status=503, mimetype='text/plain')

    if not request.json or 'text' not in request.json:
        return Response("No text provided.", status=400, mimetype='text/plain')

    text_to_synthesize = request.json['text']
    if not text_to_synthesize.strip():
        return Response("Text is empty.", status=400, mimetype='text/plain')

    logger.info(f"Synthesizing text: '{text_to_synthesize[:50]}...'")

    try:
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, 'wb') as wave_file:
            wave_file.setnchannels(1)
            wave_file.setsampwidth(2)
            wave_file.setframerate(voice.config.sample_rate)
            voice.synthesize(text_to_synthesize, wave_file)

        audio_buffer.seek(0)
        audio_bytes_len = len(audio_buffer.getvalue())
        logger.info(f"Synthesis complete. Generated {audio_bytes_len} bytes.")
        audio_buffer.seek(0)

        return send_file(
            audio_buffer,
            mimetype='audio/wav',
            as_attachment=False
        )
    except Exception as e:
        logger.exception("An exception occurred during the /api/tts request.")
        return Response("Error during audio synthesis.", status=500, mimetype='text/plain')


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5001
    app.run(host=host, port=port, debug=False)