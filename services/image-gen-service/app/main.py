# services/image-gen-service/app/main.py
import os
import torch
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from diffusers import StableDiffusionXLPipeline
from io import BytesIO
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Configuration ---
CHECKPOINT_DIR = "./checkpoints"
MODEL_FILENAME = "cyberrealisticPony_v125.safetensors"
MODEL_PATH = os.path.join(CHECKPOINT_DIR, MODEL_FILENAME)
PROMPT_PREFIX = "score_9, score_8_up, score_7_up, "
API_PREFIX = "/api/image"

# --- Global Model Pipeline ---
pipeline = None


def load_model():
    """Load the SDXL model into memory. This is called once on startup."""
    global pipeline
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    if not os.path.exists(MODEL_PATH):
        logger.error(f"FATAL: Model file not found at {MODEL_PATH}")
        return

    try:
        logger.info(f"Loading SDXL model from single file: {MODEL_PATH}")
        pipeline = StableDiffusionXLPipeline.from_single_file(
            MODEL_PATH,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16"
        )
        pipeline.to(device)
        logger.info("SDXL fine-tuned model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load model: {e}", exc_info=True)
        pipeline = None


@app.route(f"{API_PREFIX}/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify service and model status."""
    return jsonify({"status": "ok", "model_loaded": pipeline is not None})


@app.route(f"{API_PREFIX}/generate", methods=["POST"])
def generate_image():
    """Generates an image using the loaded SDXL model."""
    if pipeline is None:
        return Response("SDXL model is not available.", status=503)

    data = request.get_json()
    if not data or "prompt" not in data:
        return Response("Invalid request. 'prompt' is required.", status=400)

    try:
        # Extract parameters with defaults, similar to Pydantic
        prompt = data.get("prompt")
        negative_prompt = data.get("negative_prompt",
                                   "score 6, score 5, score 4, (worst quality:1.2), (low quality:1.2), (normal quality:1.2), lowres, bad anatomy, bad hands, signature, watermarks, ugly, imperfect eyes, skewed eyes, unnatural face, unnatural body, error, extra limb, missing limbs")
        height = data.get("height", 1152)
        width = data.get("width", 896)
        num_inference_steps = data.get("num_inference_steps", 30)
        guidance_scale = data.get("guidance_scale", 5.0)

        # Prepend the recommended keywords to the prompt
        full_prompt = PROMPT_PREFIX + prompt

        logger.info(f"Generating SDXL image for full prompt: '{full_prompt}'")

        image = pipeline(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            height=height,
            width=width,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale
        ).images[0]

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        logger.info("Image generated successfully.")

        return Response(buffer.getvalue(), mimetype='image/png')

    except Exception as e:
        logger.error(f"An error occurred during image generation: {e}", exc_info=True)
        return Response(f"Internal server error: {str(e)}", status=500)


# --- Model Loading and App Startup ---
# This part runs when the container starts, loading the model into memory.
load_model()

if __name__ == '__main__':
    # For local development only
    app.run(host='0.0.0.0', port=8000, debug=True)