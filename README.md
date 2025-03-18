
# LM Studio Chat Flask App

This is a simple Flask application that provides a basic chat interface to interact with a locally hosted language model (LLM) using LM Studio. LM Studio is a great option for running your own LLM locally because it exposes endpoints similar to the OpenAI API, making it easy to integrate with existing tools and workflows.

## Features

- **Chat Interface:** A minimal web-based UI for sending messages and receiving real-time responses.
- **Streaming Responses:** Uses streaming to display the response as it is generated.
- **Simple Setup:** Designed for local testing and quick demos.
- **Dark Mode:** Built-in dark mode toggle for an improved user experience.
- **In-Memory Conversation History:** Stores conversation history in a global variable (ideal for demos; consider using sessions or a database in production).

## Prerequisites

- Python 3.6 or later
- [Flask](https://flask.palletsprojects.com/)
- [Requests](https://docs.python-requests.org/)

You can install the required packages using pip:

```bash
pip install flask requests
```

## Configuration

Before running the app, update the `LM_STUDIO_URL` in the code to point to your LM Studio endpoint. For example:

```python
LM_STUDIO_URL = "http://xxxx/v1/chat/completions"
```

## Running the Application

To start the Flask application, simply run:

```bash
python app.py
```

The app will run on `http://0.0.0.0:8000`. Open your browser and navigate to this URL to use the chat interface.

## Usage

- **Send a Message:** Type your message into the text box and click the **Send** button (or press Enter). The chat interface will display your message along with the LM Studio response.
- **New Chat:** Click the **New Chat** button to clear the conversation history and start fresh.
- **Dark Mode:** Toggle between light and dark modes by clicking the **Toggle Dark Mode** button.
- **Cancel Request:** If needed, click the **Cancel** button to abort a running request.


## Customization

This application is built with flexibility in mind. The conversation history starts with a default system prompt that you can easily modify—simply change the text in the `conversation_history` variable or reset it when starting a new conversation. You’re free to include any instructions you want here, whether it's for setting a tone, defining behavior, or other purposes.

## Turning the App into an Executable

If you’d like to distribute this application as a standalone executable, you can use **PyInstaller** to package it. Here’s a quick guide:

1. **Install PyInstaller:**

   ```bash
   pip install pyinstaller
2. **Create the Executable:**

   Navigate to the directory containing your `app.py` file and run:

   ```bash
   pyinstaller --onefile app.py

3. **Run the Executable**:

    After PyInstaller finishes, the executable will be located in the dist folder. You can run it directly:

## Notes

- This application is intended for local testing and demonstration purposes.
- In a production setting, consider implementing session management and storing conversation history in a secure database.
- LM Studio's API mimics OpenAI's endpoints, allowing for seamless integration with existing tools designed for OpenAI's API.

## License

This project is open source; feel free to modify and change as wanted.