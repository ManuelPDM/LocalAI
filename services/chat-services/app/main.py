import os
import requests
import json
from flask import Flask, request, Response, jsonify, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Get Core Service URL from environment variable
CORE_SERVICE_URL = os.environ.get("CORE_SERVICE_URL", "http://core-service:8000")
API_PREFIX = "/api/chat"


def get_settings():
    try:
        response = requests.get(f"{CORE_SERVICE_URL}/api/core/settings")
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        # Return empty settings on failure
        return {}


@app.route(f"{API_PREFIX}/<session_id>", methods=["POST"])
def chat(session_id):
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message:
        return Response("No message provided.", status=400)

    settings = get_settings()
    lm_studio_url = settings.get("lm_studio_url")
    if not lm_studio_url:
        return Response("LM Studio URL not configured.", status=500)

    try:
        # 1. Get history from core-service
        messages_resp = requests.get(f"{CORE_SERVICE_URL}/api/core/sessions/{session_id}/messages")
        messages_resp.raise_for_status()
        current_history = messages_resp.json()
        is_new_chat = len(current_history) <= 1

        # 2. Add new user message to history (in core-service)
        add_msg_payload = {"role": "user", "content": user_message}
        requests.post(f"{CORE_SERVICE_URL}/api/core/sessions/{session_id}/messages",
                      json=add_msg_payload).raise_for_status()
        current_history.append(add_msg_payload)

    except requests.RequestException as e:
        return Response(f"Error communicating with core service: {e}", status=500)

    payload = {
        "messages": current_history,
        "max_tokens": settings.get('max_tokens', -1),
        "stream": True
    }

    def generate():
        full_reply = ""
        try:
            with requests.post(lm_studio_url, json=payload, stream=True) as lm_response:
                lm_response.raise_for_status()
                for line in lm_response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data:"):
                        line_data = line[5:].strip()
                        if line_data == "[DONE]":
                            break
                        try:
                            content = json.loads(line_data)['choices'][0]['delta'].get('content', '')
                            if content:
                                full_reply += content
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except requests.exceptions.RequestException as e:
            yield f"\nError connecting to LLM: {e}"
        finally:
            # 3. Add final assistant message to history (in core-service)
            requests.post(f"{CORE_SERVICE_URL}/api/core/sessions/{session_id}/messages",
                          json={"role": "assistant", "content": full_reply}).raise_for_status()
            if is_new_chat:
                title = user_message[:40] + ('...' if len(user_message) > 40 else '')
                requests.put(f"{CORE_SERVICE_URL}/api/core/sessions/{session_id}/rename",
                             json={"title": title}).raise_for_status()

    return Response(stream_with_context(generate()), mimetype='text/plain')


@app.route(f"{API_PREFIX}/<session_id>/regenerate", methods=["POST"])
def regenerate(session_id):
    settings = get_settings()
    lm_studio_url = settings.get("lm_studio_url")
    if not lm_studio_url:
        return Response("LM Studio URL not configured.", status=500)

    try:
        # 1. Delete last message in core-service
        requests.post(f"{CORE_SERVICE_URL}/api/core/sessions/{session_id}/regenerate").raise_for_status()

        # 2. Get updated history
        messages_resp = requests.get(f"{CORE_SERVICE_URL}/api/core/sessions/{session_id}/messages")
        messages_resp.raise_for_status()
        current_history = messages_resp.json()
    except requests.RequestException as e:
        return Response(f"Error communicating with core service: {e}", status=500)

    payload = {"messages": current_history, "max_tokens": settings.get('max_tokens', -1), "stream": True}

    def generate():
        full_reply = ""
        try:
            with requests.post(lm_studio_url, json=payload, stream=True) as lm_response:
                # ... (streaming logic is identical to chat endpoint)
                lm_response.raise_for_status()
                for line in lm_response.iter_lines(decode_unicode=True):
                    if line and line.startswith("data:"):
                        line_data = line[5:].strip()
                        if line_data == "[DONE]": break
                        try:
                            content = json.loads(line_data)['choices'][0]['delta'].get('content', '')
                            if content:
                                full_reply += content
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except requests.exceptions.RequestException as e:
            yield f"\nError connecting to LLM: {e}"
        finally:
            # 3. Add new assistant message to history
            requests.post(f"{CORE_SERVICE_URL}/api/core/sessions/{session_id}/messages",
                          json={"role": "assistant", "content": full_reply}).raise_for_status()

    return Response(stream_with_context(generate()), mimetype='text/plain')