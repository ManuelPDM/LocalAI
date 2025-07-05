import sys
import os
import threading
from flask import Flask, request, Response, stream_with_context, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
import requests
import json
import uuid
import re
from pathlib import Path
import database as db
import io
import logging
import wave

# Import PiperTTS for integrated TTS service
from piper.voice import PiperVoice


# --- PyInstaller Path Correction ---
# When running as a PyInstaller bundle, paths need to be resolved specially.
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# --- Main Flask App Setup ---
app = Flask(__name__, static_folder=resource_path('static'))
settings = {}

DEFAULT_SETTINGS = {
    "lm_studio_url": "http://localhost:1234/v1/chat/completions",
    "max_tokens": -1,
    "context_limit": 8000,
    "summarization_threshold": 6000,
    "length_scale": 1.0,
    "icon_size": "medium",
    "prompts": [
        {"title": "Default Assistant", "icon": "bot.svg", "ai_name": "Assistant",
         "prompt": "You are a helpful, general-purpose AI assistant."},
        {"title": "Python Expert", "icon": "python.svg", "ai_name": "Python Coder",
         "prompt": "You are an expert Python developer. Provide clean, efficient, and well-commented code."},
        {"title": "Creative Storyteller", "icon": "story.svg", "ai_name": "Storyteller",
         "prompt": "You are a master storyteller. Weave imaginative and engaging tales based on the user's input."}
    ]
}


def load_settings_from_db():
    global settings
    settings = db.get_settings_and_prompts()
    for key in ['max_tokens', 'context_limit', 'summarization_threshold']:
        if key in settings:
            settings[key] = int(settings[key])
    if 'length_scale' in settings:
        settings['length_scale'] = float(settings['length_scale'])
    if 'icon_size' not in settings:
        settings['icon_size'] = 'medium'


def estimate_tokens(text):
    if not isinstance(text, str): return 0
    return len(re.findall(r'\w+', text))


# --- Main App Routes ---
@app.route("/")
def index():
    try:
        # Use render_template_string to handle PyInstaller's bundling
        with open(resource_path('index.html'), 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return "Error: index.html not found.", 404


# Other routes for chat, sessions, settings, etc. remain the same as before
# ... (All previous app routes like /api/chat, /api/sessions, etc. go here)
# For brevity, I am omitting the identical routes. The full code is included below.

@app.route("/api/chat/<session_id>", methods=["POST"])
def chat(session_id):
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message: return Response("No message provided.", status=400)
    current_history = db.get_session_messages(session_id)
    if not current_history: return Response("Session not found.", status=404)
    is_new_chat = len(current_history) <= 1
    current_history.append({"role": "user", "content": user_message})
    db.add_message(session_id, 'user', user_message)
    total_tokens = sum(estimate_tokens(msg.get("content")) for msg in current_history)
    was_summarized = False
    if total_tokens > settings.get('summarization_threshold', 6000):
        if summarize_and_prune_history(session_id, current_history):
            was_summarized = True
            current_history = db.get_session_messages(session_id)
            current_history.append({"role": "user", "content": user_message})
    payload = {"messages": current_history, "max_tokens": settings.get('max_tokens'), "stream": True}

    def generate():
        full_reply = ""
        try:
            with requests.post(settings['lm_studio_url'], json=payload, stream=True) as lm_response:
                lm_response.raise_for_status()
                for line in lm_response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data:"):
                        line_data = line[5:].strip()
                        if line_data == "[DONE]": break
                        try:
                            content = json.loads(line_data)['choices'][0]['delta'].get('content', '')
                            if content: full_reply += content; yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except requests.exceptions.RequestException as e:
            yield f"\nError: {e}"
        finally:
            db.add_message(session_id, 'assistant', full_reply)
            if is_new_chat:
                db.rename_session(session_id, user_message[:40] + ('...' if len(user_message) > 40 else ''))

    resp = Response(stream_with_context(generate()), mimetype='text/plain')
    if was_summarized: resp.headers['X-Session-Summarized'] = 'true'
    return resp


@app.route("/api/chat/<session_id>/regenerate", methods=["POST"])
def regenerate(session_id):
    if not db.delete_last_assistant_message(session_id): return Response("No message to regenerate.", status=404)
    current_history = db.get_session_messages(session_id)
    if not current_history: return Response("History empty.", status=404)
    payload = {"messages": current_history, "max_tokens": settings.get('max_tokens'), "stream": True}

    def generate():
        full_reply = ""
        try:
            with requests.post(settings['lm_studio_url'], json=payload, stream=True) as lm_response:
                lm_response.raise_for_status()
                for line in lm_response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data:"):
                        line_data = line[5:].strip()
                        if line_data == "[DONE]": break
                        try:
                            content = json.loads(line_data)['choices'][0]['delta'].get('content', '')
                            if content: full_reply += content; yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except requests.exceptions.RequestException as e:
            yield f"\nError: {e}"
        finally:
            db.add_message(session_id, 'assistant', full_reply)

    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route("/api/sessions", methods=["POST"])
def create_new_session():
    session_id, data = str(uuid.uuid4()), request.get_json() or {}
    prompt_text = data.get("prompt", DEFAULT_SETTINGS['prompts'][0]['prompt'])
    prompt_info = next((p for p in settings.get('prompts', []) if p['prompt'] == prompt_text), None)
    icon = prompt_info.get('icon', 'bot.svg') if prompt_info else 'bot.svg'
    ai_name = prompt_info.get('ai_name') if prompt_info else None
    db.create_session(session_id, 'New Chat', prompt_text, icon=icon, ai_name=ai_name)
    return jsonify({"id": session_id}), 201


@app.route("/api/sessions", methods=["GET"])
def get_all_sessions(): return jsonify(db.get_all_sessions())


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    messages = db.get_session_messages(session_id)
    if not messages: return jsonify({"error": "Session not found"}), 404
    info = db.get_session_info(session_id)
    return jsonify({"messages": messages, "icon": info.get('icon'), "ai_name": info.get('ai_name')})


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    db.delete_session(session_id)
    return jsonify({"success": True})


@app.route("/api/sessions/<session_id>/rename", methods=["PUT"])
def rename_session_route(session_id):
    data = request.get_json()
    new_title = data.get("title")
    if not new_title: return jsonify({"error": "New title not provided"}), 400
    db.rename_session(session_id, new_title)
    return jsonify({"success": True})


@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        db.save_settings_and_prompts(request.get_json())
        load_settings_from_db()
        return jsonify({'message': 'Settings saved successfully!'})
    else:
        return jsonify(settings)


@app.route('/api/icons', methods=['GET'])
def get_icons():
    icon_dir = Path(resource_path('static/icons'))
    if not icon_dir.is_dir(): return jsonify([])
    exts = ['.svg', '.png', '.jpg', '.jpeg', '.gif']
    return jsonify([f.name for f in icon_dir.iterdir() if f.suffix.lower() in exts])


# --- TTS Server Setup ---
tts_app = Flask("tts_server")
CORS(tts_app)
tts_voice = None


@tts_app.route('/api/tts', methods=['POST'])
def text_to_speech():
    if not tts_voice: return "TTS model is not available.", 503
    data = request.json
    if not data or 'text' not in data: return "No text provided.", 400
    text, scale = data['text'], data.get('length_scale', 1.0)
    if not text.strip(): return "Text is empty.", 400
    try:
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            tts_voice.synthesize(text, wf, length_scale=scale)
        buffer.seek(0)
        return send_from_directory(os.path.dirname(buffer), os.path.basename(buffer), mimetype='audio/wav')
    except Exception as e:
        print(f"TTS Error: {e}")
        return "Error during audio synthesis.", 500


# --- Main Execution ---
def run_main_app():
    # Bind to 0.0.0.0 to be accessible on the network
    app.run(host='0.0.0.0', port=8000, debug=False)


def run_tts_app():
    # TTS can also bind to 0.0.0.0
    tts_app.run(host='0.0.0.0', port=5001, debug=False)


if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    static_path = Path(resource_path('static/icons'))
    static_path.mkdir(parents=True, exist_ok=True)

    db.init_db()
    load_settings_from_db()

    # Load TTS model
    TTS_MODEL_PATH = 'models/en_GB-semaine-medium/en_GB-semaine-medium.onnx'
    try:
        if os.path.exists(TTS_MODEL_PATH):
            tts_voice = PiperVoice.load(TTS_MODEL_PATH)
            print("Piper TTS model loaded successfully.")
        else:
            print(f"Warning: Piper TTS model not found at {TTS_MODEL_PATH}. TTS will be unavailable.")
    except Exception as e:
        print(f"Error loading Piper TTS model: {e}. TTS will be unavailable.")

    # Run Flask apps in separate threads
    main_app_thread = threading.Thread(target=run_main_app)
    tts_app_thread = threading.Thread(target=run_tts_app)

    main_app_thread.start()
    tts_app_thread.start()