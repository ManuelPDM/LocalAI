# File: services/core-services/app/main.py

import os
from flask import Flask, jsonify, request
from pathlib import Path
import database as db

app = Flask(__name__)

# --- Default Settings ---
DEFAULT_SETTINGS = {
    "lm_studio_url": "http://localhost:1234/v1/chat/completions",
    "max_tokens": -1,
    "context_limit": 8000,
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


# --- Initialization ---
# CORRECTED: This code now runs when each Gunicorn worker process starts.
# It is more robust because any database errors will cause the container
# to fail on startup, making debugging much easier.
# The database functions are idempotent (safe to run multiple times).
print("CORE-SERVICE: Initializing database and settings for worker process...")
try:
    Path("data").mkdir(exist_ok=True)
    db.init_db()
    db.migrate_from_json(DEFAULT_SETTINGS)
    print("CORE-SERVICE: Initialization complete for worker process.")
except Exception as e:
    print(f"CORE-SERVICE: FATAL - An error occurred during initialization: {e}")
    # Re-raise the exception to ensure the worker process fails to start
    raise


# --- Public API Routes (for Frontend via Traefik) ---

@app.route("/api/sessions", methods=["GET"])
def get_all_sessions():
    return jsonify(db.get_all_sessions())


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    messages = db.get_session_messages(session_id)
    if not messages:
        return jsonify({"error": "Session not found"}), 404
    info = db.get_session_info(session_id)
    return jsonify({"messages": messages, "icon": info.get('icon'), "ai_name": info.get('ai_name')})


@app.route("/api/sessions", methods=["POST"])
def create_new_session():
    import uuid
    session_id = str(uuid.uuid4())
    data = request.get_json() or {}
    settings = db.get_settings_and_prompts()
    prompt_text = data.get("prompt", settings.get('prompts', [{}])[0].get('prompt', 'You are helpful.'))
    prompt_info = next((p for p in settings.get('prompts', []) if p['prompt'] == prompt_text), None)
    icon = prompt_info.get('icon', 'bot.svg') if prompt_info else 'bot.svg'
    ai_name = prompt_info.get('ai_name') if prompt_info else None
    db.create_session(session_id, 'New Chat', prompt_text, icon=icon, ai_name=ai_name)
    return jsonify({"id": session_id}), 201


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    db.delete_session(session_id)
    return jsonify({"success": True})


@app.route("/api/sessions/<session_id>/rename", methods=["PUT"])
def rename_session_route(session_id):
    data = request.get_json()
    new_title = data.get("title")
    if not new_title:
        return jsonify({"error": "New title not provided"}), 400
    db.rename_session(session_id, new_title)
    return jsonify({"success": True})


@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        db.save_settings_and_prompts(request.get_json())
        return jsonify({'message': 'Settings saved successfully!'})
    else:
        settings = db.get_settings_and_prompts()
        return jsonify(settings)


# --- Internal API Routes (for Chat Service, not exposed by Traefik) ---

@app.route('/api/core/settings', methods=['GET'])
def internal_settings():
    settings = db.get_settings_and_prompts()
    return jsonify(settings)


@app.route('/api/core/sessions/<session_id>/messages', methods=['GET', 'POST'])
def internal_messages(session_id):
    if request.method == 'GET':
        messages = db.get_session_messages(session_id)
        return jsonify(messages)
    elif request.method == 'POST':
        data = request.get_json()
        role = data.get("role")
        content = data.get("content")
        db.add_message(session_id, role, content)
        return jsonify({"success": True})


@app.route('/api/core/sessions/<session_id>/rename', methods=['PUT'])
def internal_rename(session_id):
    data = request.get_json()
    title = data.get("title")
    db.rename_session(session_id, title)
    return jsonify({"success": True})


@app.route('/api/core/sessions/<session_id>/regenerate', methods=['POST'])
def internal_regenerate(session_id):
    success = db.delete_last_assistant_message(session_id)
    return jsonify({"success": success})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)