# services/image-gen-service/app/main.py
import os
import torch
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from diffusers import StableDiffusionPipeline
from io import BytesIO
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Configuration ---
CHECKPOINT_DIR = "./checkpoints"  # Mounted volume where models are stored
# --- CHANGED: Specify your local model filename ---
MODEL_FILENAME = "beautifulRealistic_v1.safetensors"  # <--- REPLACE WITH YOUR MODEL'S FILENAME
MODEL_PATH = os.path.join(CHECKPOINT_DIR, MODEL_FILENAME)

PROMPT_PREFIX = ""
API_PREFIX = "/api/image"

# --- Global Model Pipeline and Status ---
pipeline = None
current_loaded_model_filename = None
device = "cpu"  # Default to CPU, will be updated by get_device()


def get_device():
    """Determine the device (cuda or cpu) once."""
    global device
    if torch.cuda.is_available():
        device = "cuda"
        logger.info("CUDA (GPU) is available and will be used.")
        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        logger.info(f"Total GPU VRAM: {total_vram:.2f} GB")
    else:
        device = "cpu"
        logger.warning("CUDA (GPU) not available. Using CPU, which will be very slow.")


def unload_model():
    """Unloads the current model from VRAM."""
    global pipeline, current_loaded_model_filename
    if pipeline is not None:
        logger.info(f"Unloading model: {current_loaded_model_filename}")
        del pipeline  # Delete the pipeline object
        if device == "cuda":
            # Important: Set pipeline to None BEFORE clearing cache to ensure
            # no references are held, allowing VRAM to be freed.
            pipeline = None
            torch.cuda.empty_cache()  # Clear CUDA cache
        else:
            pipeline = None
        current_loaded_model_filename = None
        logger.info("Model unloaded successfully.")


def load_specific_model(model_filename: str):
    """Loads a specific model by filename."""
    global pipeline, current_loaded_model_filename

    model_path = os.path.join(CHECKPOINT_DIR, model_filename)

    if not os.path.exists(model_path):
        logger.error(f"Model file not found: {model_path}")
        return False, f"Model file not found: {model_filename}"

    if current_loaded_model_filename == model_filename and pipeline is not None:
        logger.info(f"Model {model_filename} is already loaded.")
        return True, "Model already loaded."

    # Unload any currently loaded model before loading a new one
    if pipeline is not None:
        unload_model()

    try:
        logger.info(f"Attempting to load model from: {model_path}")
        new_pipeline = StableDiffusionPipeline.from_single_file(
            model_path,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            use_safetensors=True
        )
        new_pipeline.to(device)
        pipeline = new_pipeline
        current_loaded_model_filename = model_filename
        logger.info(f"Model '{model_filename}' loaded successfully.")
        return True, "Model loaded successfully."
    except Exception as e:
        logger.error(f"Failed to load model '{model_filename}': {e}", exc_info=True)
        unload_model()  # Ensure VRAM is cleared on failure
        return False, f"Failed to load model: {str(e)}"


# --- API Endpoints ---
@app.route(f"{API_PREFIX}/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify service and model status."""
    return jsonify({
        "status": "ok",
        "model_loaded": pipeline is not None,
        "loaded_model_name": current_loaded_model_filename,
        "device": device
    })


@app.route(f"{API_PREFIX}/models", methods=["GET"])
def list_models():
    """Returns a list of available model filenames."""
    models = []
    if os.path.exists(CHECKPOINT_DIR):
        for f in os.listdir(CHECKPOINT_DIR):
            if f.endswith((".safetensors", ".ckpt")):
                models.append(f)
    return jsonify({"models": sorted(models)})


@app.route(f"{API_PREFIX}/load", methods=["POST"])
def api_load_model():
    """API endpoint to load a specific model."""
    data = request.get_json()
    model_filename = data.get("model_filename")
    if not model_filename:
        return Response("Model filename not provided.", status=400)

    success, message = load_specific_model(model_filename)
    if success:
        return jsonify({"status": "success", "message": message, "loaded_model_name": current_loaded_model_filename})
    else:
        return jsonify({"status": "error", "message": message}), 500


@app.route(f"{API_PREFIX}/unload", methods=["POST"])
def api_unload_model():
    """API endpoint to unload the current model."""
    if pipeline is None:
        return jsonify({"status": "success", "message": "No model loaded to unload."})

    unload_model()
    return jsonify({"status": "success", "message": "Model unloaded."})


@app.route(f"{API_PREFIX}/generate", methods=["POST"])
def generate_image():
    """Generates an image using the loaded SD 1.5 model."""
    if pipeline is None:
        return Response("Stable Diffusion 1.5 model is not currently loaded. Please load a model first.", status=503)

    data = request.get_json()
    if not data or "prompt" not in data:
        return Response("Invalid request. 'prompt' is required.", status=400)

    try:
        prompt = data.get("prompt")
        negative_prompt = data.get("negative_prompt",
                                   "ugly, deformed, disfigured, poor quality, lowres, bad anatomy, extra limbs, blurry")
        height = data.get("height", 512)
        width = data.get("width", 512)
        num_inference_steps = data.get("num_inference_steps", 25)
        guidance_scale = data.get("guidance_scale", 7.0)

        full_prompt = PROMPT_PREFIX + prompt

        logger.info(f"Generating SD 1.5 image with '{current_loaded_model_filename}' for prompt: '{full_prompt}'")

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


# --- Model Loading and App Initialization Logic ---
# This code block executes once when the Python module is loaded.
# With Gunicorn --preload, this runs in the master process before workers are forked.
get_device()  # Detect GPU presence

# Attempt to load a default model if any exist on startup
available_models = []
if os.path.exists(CHECKPOINT_DIR):
    for f in os.listdir(CHECKPOINT_DIR):
        if f.endswith((".safetensors", ".ckpt")):
            available_models.append(f)

if available_models:
    available_models.sort()
    success, msg = load_specific_model(available_models[0])
    if not success:
        logger.error(f"Failed to load default model on startup: {msg}")
else:
    logger.warning(f"No models found in {CHECKPOINT_DIR}. Image generation service will start unloaded.")

if __name__ == '__main__':
    # This block is only for local development runs (python main.py),
    # and is not executed when Gunicorn is used in Docker.
    # The setup logic above (get_device, initial model load) already handles startup for both.
    app.run(host='0.0.0.0', port=8000, debug=True)