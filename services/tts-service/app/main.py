from flask import Flask, request, send_file
from flask_cors import CORS
from piper.voice import PiperVoice
import io
import logging
import wave
import os

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# --- Model Loading ---
MODEL_PATH = '/app/models/en_GB-semaine-medium/en_GB-semaine-medium.onnx'
CONFIG_PATH = f"{MODEL_PATH}.json"

logging.info("--- Piper TTS Server Initialization ---")
logging.info(f"Attempting to load Piper TTS model.")
logging.info(f"Model path: {MODEL_PATH}")
logging.info(f"Config path: {CONFIG_PATH}")

voice = None

try:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found at: {CONFIG_PATH}")

    voice = PiperVoice.load(MODEL_PATH, config_path=CONFIG_PATH)
    logging.info("Piper TTS model loaded successfully.")

except Exception as e:
    logger.exception("FATAL: Failed to load Piper TTS model. The TTS service will not be available.")


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """
    Receives text in a JSON payload and returns synthesized speech as a WAV file.
    """
    if not voice:
        logging.error("TTS request received, but model is not loaded.")
        return "TTS model is not available.", 503

    if not request.json or 'text' not in request.json:
        return "No text provided.", 400

    text_to_synthesize = request.json['text']
    if not text_to_synthesize.strip():
        return "Text is empty.", 400

    logging.info(f"Synthesizing text: '{text_to_synthesize[:50]}...'")

    try:
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, 'wb') as wave_file:

            wave_file.setnchannels(1)
            wave_file.setsampwidth(2)
            wave_file.setframerate(voice.config.sample_rate)
            voice.synthesize(text_to_synthesize, wave_file)

        audio_buffer.seek(0)

        logging.info("Synthesis complete. Sending audio data.")
        return send_file(
            audio_buffer,
            mimetype='audio/wav',
            as_attachment=False
        )
    except Exception as e:
        logger.exception("Exception on /api/tts [POST]")
        return "Error during audio synthesis.", 500


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5001
    print(f"--- Starting TTS server for local development on http://{host}:{port} ---")
    app.run(host=host, port=port, debug=False)