from flask import Flask, request, Response, stream_with_context, jsonify
import requests
import json

app = Flask(__name__)

# Global conversation history. In production, use sessions or a database.
conversation_history = [
    {
        "role": "system",
        "content": (
            "You are a roleplaying AI, an imaginative and engaging character who "
            "always responds in the first person. No matter what the user describes, "
            "you adapt to the scenario and stay fully in character, offering a rich, "
            "immersive narrative experience. Speak naturally as if you are a living character "
            "with your own personality, thoughts, and emotions. Embrace the role, interact "
            "with creativity, and never break character."
        )
    }
]

LM_STUDIO_URL = ""

@app.route("/")
def index():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>LM Studio Chat Interface</title>
    <style>
        /* Container to center content and provide max width */
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 10px;
        }
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0;
            background: #f9f9f9;
            color: #000;
        }
        #chatBox { 
            width: 100%; 
            height: 300px; 
            border: 1px solid #ccc; 
            overflow-y: scroll; 
            padding: 10px; 
            background: #fff;
            box-sizing: border-box;
        }
        input[type="text"] { 
            width: 100%; 
            padding: 10px; 
            box-sizing: border-box; 
            margin-bottom: 10px;
            font-size: 16px;
        }
        button { 
            padding: 10px; 
            width: 48%; 
            margin-bottom: 10px;
            box-sizing: border-box;
        }
        .button-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .message { 
            margin-bottom: 10px; 
            word-wrap: break-word;
        }
        .User { 
            font-weight: bold; 
        }
        .LMStudio { 
            font-style: italic; 
        }
        /* Dark mode styles */
        body.dark-mode {
            background: #333;
            color: #f9f9f9;
        }
        body.dark-mode #chatBox {
            background: #555;
            border-color: #888;
        }
        body.dark-mode input[type="text"] {
            background: #666;
            color: #f9f9f9;
            border: 1px solid #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>LM Studio Chat</h1>
        <div class="button-row">
            <button id="newChatButton">New Chat</button>
            <button id="sendButton">Send</button>
        </div>
        <div class="button-row">
            <button id="darkModeButton">Toggle Dark Mode</button>
            <button id="cancelButton">Cancel</button>
        </div>
        <div id="chatBox"></div>
        <input type="text" id="inputMessage" placeholder="Type your message here..." />
    </div>
    <script>
        const chatBox = document.getElementById('chatBox');
        const inputMessage = document.getElementById('inputMessage');
        const sendButton = document.getElementById('sendButton');
        const newChatButton = document.getElementById('newChatButton');
        const darkModeButton = document.getElementById('darkModeButton');
        const cancelButton = document.getElementById('cancelButton');

        // Global variable to hold the AbortController for the current request.
        let currentAbortController = null;

        // Function to add a new message element.
        function addMessageElement(sender, text) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            messageDiv.innerHTML = '<span class="' + sender + '">' + sender + ':</span> ' + text;
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
            return messageDiv;
        }

        sendButton.addEventListener('click', () => {
            const message = inputMessage.value;
            if (message.trim() === '') return;
            addMessageElement('User', message);
            inputMessage.value = '';

            // Create a placeholder element for LMStudio's response.
            const lmMessageElement = addMessageElement('LMStudio', '');
            let fullResponse = '';

            // Create a new AbortController for this request.
            currentAbortController = new AbortController();

            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message }),
                signal: currentAbortController.signal
            })
            .then(response => {
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                function read() {
                    return reader.read().then(({done, value}) => {
                        if (done) return;
                        const chunk = decoder.decode(value, { stream: true });
                        fullResponse += chunk;
                        lmMessageElement.innerHTML = '<span class="LMStudio">LMStudio:</span> ' + fullResponse;
                        chatBox.scrollTop = chatBox.scrollHeight;
                        return read();
                    });
                }
                return read();
            })
            .catch(error => {
                if (error.name === 'AbortError') {
                    addMessageElement('System', 'Message generation cancelled.');
                } else {
                    addMessageElement('Error', 'There was an error processing your request.');
                    console.error('Error:', error);
                }
            })
            .finally(() => {
                currentAbortController = null;
            });
        });

        // New Chat button resets the chat history on the server and clears the UI.
        newChatButton.addEventListener('click', () => {
            fetch('/new_chat', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                chatBox.innerHTML = '';
                addMessageElement('System', data.message);
            })
            .catch(error => {
                addMessageElement('Error', 'There was an error starting a new chat.');
                console.error('Error:', error);
            });
        });

        // Dark Mode toggle button.
        darkModeButton.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
        });

        // Cancel button to abort the current message generation.
        cancelButton.addEventListener('click', () => {
            if (currentAbortController) {
                currentAbortController.abort();
            }
        });

        inputMessage.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                sendButton.click();
            }
        });
    </script>
</body>
</html>
'''

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message:
        return Response("No message provided.", status=400)

    # Append the user message to the conversation history.
    conversation_history.append({"role": "user", "content": user_message})

    payload = {
        "model": "hermes-3-llama-3.1-8b",
        "messages": conversation_history,
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": True
    }

    def generate():
        reply = ""
        try:
            with requests.post(LM_STUDIO_URL, json=payload, stream=True) as lm_response:
                lm_response.raise_for_status()
                for line in lm_response.iter_lines(decode_unicode=True):
                    if line:
                        if line.startswith("data:"):
                            line = line[5:].strip()
                        if line == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            reply += content
                            yield content
                        except Exception:
                            continue
        except Exception as e:
            yield f"\nError communicating with LM Studio: {str(e)}"
        finally:
            # Even if the stream is cancelled, save the conversation up to this point.
            conversation_history.append({"role": "assistant", "content": reply})

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route("/new_chat", methods=["POST"])
def new_chat():
    global conversation_history
    conversation_history = [
        {
            "role": "system",
            "content": (
                "You are a role playing AI, an imaginative and engaging character who "
                "always responds in the first person. No matter what the user describes, "
                "you adapt to the scenario and stay fully in character, offering a rich, "
                "immersive narrative experience. Speak naturally as if you are a living character "
                "with your own personality, thoughts, and emotions. Embrace the role, interact "
                "with creativity, and never break character."
            )
        }
    ]
    return jsonify({"message": "New chat started with no background."})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=False)
