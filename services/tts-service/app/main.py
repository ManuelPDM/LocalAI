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

    voice = PiperVoice.load(MODEL_PATH, config_path=CONFIG_PATH)
    logger.info("PiperVoice.load() completed without throwing an exception.")

    # --- START: NEW DIAGNOSTIC LOGGING ---
    # Safely inspect the voice.config object to see its state after loading.
    if voice and hasattr(voice, 'config'):
        # Use getattr to safely access attributes that might be missing
        sample_rate = getattr(voice.config, 'sample_rate', 'NOT FOUND')
        logger.info(f"DIAGNOSTIC: Inspected voice.config.sample_rate. Value is: [{sample_rate}]")

        # Also check its type for more detail
        logger.info(f"DIAGNOSTIC: Type of voice.config.sample_rate is: [{type(sample_rate)}]")
    else:
        logger.error("DIAGNOSTIC: voice object is NULL or has no 'config' attribute after loading!")
    # --- END: NEW DIAGNOSTIC LOGGING ---

except Exception as e:
    logger.exception("FATAL: An exception occurred during model loading.")


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """
    Receives text in a JSON payload and returns synthesized speech as a WAV file.
    """
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

            # --- START: PRE-SYNTHESIS LOGGING ---
            # Log the values JUST BEFORE they are used.
            # This is the original, functional code.
            sample_rate_to_use = voice.config.sample_rate
            logger.info(
                f"DIAGNOSTIC: Value of sample_rate_to_use (from voice.config.sample_rate) is: [{sample_rate_to_use}]")
            # --- END: PRE-SYNTHESIS LOGGING ---

            wave_file.setnchannels(1)
            wave_file.setsampwidth(2)
            wave_file.setframerate(sample_rate_to_use)
            voice.synthesize(text_to_synthesize, wave_file)

        audio_buffer.seek(0)

        # Log the size of the generated audio
        audio_bytes_len = len(audio_buffer.getvalue())
        logger.info(f"Synthesis complete. Generated {audio_bytes_len} bytes.")
        if audio_bytes_len <= 44:
            logger.warning(
                "!!! WARNING: Generated audio is only a header (<= 44 bytes). This confirms a silent failure in the synthesis engine. The sample rate used was likely invalid. !!!")

        audio_buffer.seek(0)  # Rewind for send_file

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
    logger.info(f"--- Starting Flask development server on http://{host}:{port} ---")
    app.run(host=host, port=port, debug=False)