from flask import Flask, request, send_file, Response
from flask_cors import CORS
from piper.voice import PiperVoice
from piper.config import PiperConfig
import onnxruntime
import io
import logging
import wave
import os
import sys
import json

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

    # --- START: THE FINAL AND CORRECT FIX ---
    # Manually create the ONNX InferenceSession to force the use of the stable CPUExecutionProvider.
    # This bypasses the faulty auto-selection of a buggy code path in the server's VM environment.
    logger.info("Creating ONNX InferenceSession with explicit 'CPUExecutionProvider'.")
    sess_options = onnxruntime.SessionOptions()
    onnx_model = onnxruntime.InferenceSession(
        MODEL_PATH,
        sess_options=sess_options,
        providers=['CPUExecutionProvider']
    )

    # Correctly load the config by reading the JSON file into a dictionary first.
    logger.info("Reading config JSON file.")
    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        config_dict = json.load(config_file)

    logger.info("Instantiating PiperConfig from dictionary using 'from_dict'.")
    config = PiperConfig.from_dict(config_dict)

    # Instantiate the PiperVoice object with our custom session and config.
    logger.info("Instantiating PiperVoice with custom session and config.")
    voice = PiperVoice(config=config, session=onnx_model)
    # --- END: THE FINAL AND CORRECT FIX ---

    logger.info("Piper TTS model loaded successfully using manual provider selection.")

except Exception as e:
    logger.exception("FATAL: An exception occurred during model loading.")


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """
    Receives text in a JSON payload and returns synthesized speech as a WAV file.
    """
    if not voice:
        logger.error("TTS request received, but model is not loaded.")
        return "TTS model is not available.", 503

    if not request.json or 'text' not in request.json:
        return "No text provided.", 400

    text_to_synthesize = request.json['text']
    if not text_to_synthesize.strip():
        return "Text is empty.", 400

    logger.info(f"Synthesizing text: '{text_to_synthesize[:50]}...'")

    try:
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, 'wb') as wave_file:
            # Revert to the original, correct logic. The synthesize() method
            # correctly sets the WAV parameters on the wave_file object.
            voice.synthesize(text_to_synthesize, wave_file)

        audio_buffer.seek(0)
        logger.info(f"Synthesis complete. Generated {len(audio_buffer.getvalue())} bytes.")
        audio_buffer.seek(0)

        return send_file(
            audio_buffer,
            mimetype='audio/wav',
            as_attachment=False
        )
    except Exception as e:
        logger.exception("An exception occurred during the /api/tts request.")
        return "Error during audio synthesis.", 500


if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5001
    app.run(host=host, port=port, debug=False)