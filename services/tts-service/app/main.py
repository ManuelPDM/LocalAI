from flask import Flask, request, send_file, Response
from flask_cors import CORS
from piper.voice import PiperVoice
import io
import logging
import wave
import os
import json
import platform
import sys

# ==============================================================================
# EXHAUSTIVE LOGGING SETUP
# ==============================================================================
# Configure logger to be extremely detailed.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log system and library information at startup to compare environments.
logger.info("==========================================================")
logger.info("            TTS SERVICE STARTUP DIAGNOSTICS")
logger.info("==========================================================")
try:
    import onnxruntime

    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"ONNX Runtime Version: {onnxruntime.__version__}")
    logger.info(f"ONNX Runtime Providers: {onnxruntime.get_available_providers()}")
except Exception as e:
    logger.error(f"Could not import or inspect onnxruntime: {e}")
logger.info("==========================================================")

app = Flask(__name__)
CORS(app)

# ==============================================================================
# MODEL LOADING
# ==============================================================================
MODEL_PATH = '/app/models/en_GB-semaine-medium/en_GB-semaine-medium.onnx'
CONFIG_PATH = f"{MODEL_PATH}.json"

logger.info("--- Piper TTS Model Initialization ---")
logger.info(f"Model path: {MODEL_PATH}")
logger.info(f"Config path: {CONFIG_PATH}")

voice = None

try:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found at: {CONFIG_PATH}")

    logger.info("Model and config files exist. Proceeding to load PiperVoice.")
    voice = PiperVoice.load(MODEL_PATH, config_path=CONFIG_PATH)
    logger.info("PiperVoice.load() completed without throwing an exception.")

    # Log the configuration of the loaded voice model to compare environments.
    if voice and voice.config:
        config_dict = {
            "sample_rate": voice.config.sample_rate,
            "sample_width": voice.config.sample_width,
            "num_channels": voice.config.num_channels,
            "num_speakers": voice.config.num_speakers,
            "speaker_id_map_keys": list(voice.config.speaker_id_map.keys()) if voice.config.speaker_id_map else []
        }
        logger.info(f"--- SUCCESS: Loaded Voice Config: {json.dumps(config_dict)} ---")
    else:
        logger.error("--- CRITICAL FAILURE: PiperVoice object is NULL or has no config after loading! ---")

except Exception as e:
    logger.exception("--- FATAL EXCEPTION during model loading. The TTS service will not be available. ---")


# ==============================================================================
# API ROUTE
# ==============================================================================
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """
    Receives text in a JSON payload and returns synthesized speech as a WAV file.
    """
    if not voice:
        logger.error("TTS request received, but model is not loaded. Returning 503.")
        return Response("TTS model is not available.", status=503, mimetype='text/plain')

    if not request.json or 'text' not in request.json:
        logger.error("TTS request received with no 'text' field. Returning 400.")
        return Response("No text provided.", status=400, mimetype='text/plain')

    text_to_synthesize = request.json['text']
    if not text_to_synthesize.strip():
        logger.warning("TTS request received with empty text. Returning 400.")
        return Response("Text is empty.", status=400, mimetype='text/plain')

    logger.info("----------------------------------------------------------")
    logger.info(f"Received valid request. Synthesizing text snippet: '{text_to_synthesize[:80]}...'")

    try:
        audio_buffer = io.BytesIO()
        logger.info("Preparing to synthesize into in-memory WAV file.")

        with wave.open(audio_buffer, 'wb') as wave_file:
            wave_file.setnchannels(1)
            wave_file.setsampwidth(voice.config.sample_width)
            wave_file.setframerate(voice.config.sample_rate)

            logger.info(f"Calling voice.synthesize() with sample rate {voice.config.sample_rate}...")
            # This is the core synthesis operation
            voice.synthesize(text_to_synthesize, wave_file)
            logger.info("voice.synthesize() call completed.")

        # Go to the beginning of the buffer before reading
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()
        audio_buffer.seek(0)  # Rewind again for send_file

        # --- START: Critical Post-Synthesis Logging ---
        audio_length = len(audio_bytes)
        logger.info(f"Synthesis complete. Total audio bytes generated: {audio_length}")

        if audio_length <= 44:
            logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.warning("!!! CRITICAL FAILURE: Generated audio is only a header (<= 44 bytes). !!!")
            logger.warning("!!! This confirms a silent failure in the synthesis engine.           !!!")
            logger.warning("!!! LIKELY CAUSE: Runtime environment incompatibility (e.g., CPU).      !!!")
            logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        else:
            logger.info("Audio data appears valid (> 44 bytes). Sending response.")
        # --- END: Critical Post-Synthesis Logging ---

        return send_file(
            audio_buffer,
            mimetype='audio/wav',
            as_attachment=False
        )
    except Exception as e:
        logger.exception(
            f"--- An exception occurred during the synthesis process for text: '{text_to_synthesize[:80]}...' ---")
        return Response("Error during audio synthesis.", status=500, mimetype='text/plain')


if __name__ == '__main__':
    # This block is for local testing only and is not used by Gunicorn.
    host = '0.0.0.0'
    port = 5001
    logger.info(f"--- Starting Flask development server on http://{host}:{port} ---")
    app.run(host=host, port=port, debug=False)