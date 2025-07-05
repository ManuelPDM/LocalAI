import sqlite3
import json
from pathlib import Path
import os

DATABASE_NAME = "data/database.db"


def get_db():
    """Establishes a connection to the database."""
    db = sqlite3.connect(DATABASE_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db


def run_migrations(cursor):
    """Checks for and applies necessary schema migrations."""

    # --- Migration for 'prompts' table ---
    cursor.execute("PRAGMA table_info(prompts)")
    prompt_columns = [row['name'] for row in cursor.fetchall()]

    if 'icon' not in prompt_columns:
        print("Migrating prompts table: adding 'icon' column.")
        cursor.execute("ALTER TABLE prompts ADD COLUMN icon TEXT NOT NULL DEFAULT 'bot.svg'")
    if 'ai_name' not in prompt_columns:
        print("Migrating prompts table: adding 'ai_name' column.")
        cursor.execute("ALTER TABLE prompts ADD COLUMN ai_name TEXT")

    # --- Migration for 'sessions' table ---
    cursor.execute("PRAGMA table_info(sessions)")
    session_columns = [row['name'] for row in cursor.fetchall()]

    if 'icon' not in session_columns:
        print("Migrating sessions table: adding 'icon' column.")
        cursor.execute("ALTER TABLE sessions ADD COLUMN icon TEXT NOT NULL DEFAULT 'bot.svg'")
    if 'ai_name' not in session_columns:
        print("Migrating sessions table: adding 'ai_name' column.")
        cursor.execute("ALTER TABLE sessions ADD COLUMN ai_name TEXT")


def init_db():
    """Initializes the database with the required tables and runs migrations."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS settings
                   (
                       key
                       TEXT
                       PRIMARY
                       KEY,
                       value
                       TEXT
                       NOT
                       NULL
                   )
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS prompts
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       title
                       TEXT
                       NOT
                       NULL,
                       prompt
                       TEXT
                       NOT
                       NULL,
                       icon
                       TEXT
                       NOT
                       NULL
                       DEFAULT
                       'bot.svg',
                       ai_name
                       TEXT
                   )""")

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS sessions
                   (
                       id
                       TEXT
                       PRIMARY
                       KEY,
                       title
                       TEXT
                       NOT
                       NULL,
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       icon
                       TEXT
                       NOT
                       NULL
                       DEFAULT
                       'bot.svg',
                       ai_name
                       TEXT
                   )""")

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS messages
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       session_id
                       TEXT
                       NOT
                       NULL,
                       role
                       TEXT
                       NOT
                       NULL,
                       content
                       TEXT
                       NOT
                       NULL,
                       timestamp
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       FOREIGN
                       KEY
                   (
                       session_id
                   ) REFERENCES sessions
                   (
                       id
                   ) ON DELETE CASCADE
                       )""")

    # Run schema migrations to update existing databases
    run_migrations(cursor)

    db.commit()
    db.close()


# --- Settings and Prompts Functions ---
def get_settings_and_prompts():
    db = get_db()
    settings_rows = db.execute("SELECT key, value FROM settings").fetchall()
    prompts_rows = db.execute("SELECT title, prompt, icon, ai_name FROM prompts ORDER BY id").fetchall()
    db.close()

    settings = {row['key']: row['value'] for row in settings_rows}
    prompts = [{"title": row['title'], "prompt": row['prompt'], "icon": row['icon'], "ai_name": row['ai_name']} for row
               in prompts_rows]
    settings['prompts'] = prompts
    return settings


def save_settings_and_prompts(settings_data):
    db = get_db()
    cursor = db.cursor()

    prompts = settings_data.pop('prompts', [])
    cursor.execute("DELETE FROM prompts")
    if prompts:
        prompt_data = [(p['title'], p['prompt'], p.get('icon', 'bot.svg'), p.get('ai_name')) for p in prompts]
        cursor.executemany(
            "INSERT INTO prompts (title, prompt, icon, ai_name) VALUES (?, ?, ?, ?)",
            prompt_data
        )

    for key, value in settings_data.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

    db.commit()
    db.close()


# --- Session and Message Functions ---
def get_all_sessions():
    db = get_db()
    sessions = db.execute("SELECT id, title, icon FROM sessions ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(row) for row in sessions]


def get_session_info(session_id):
    db = get_db()
    session = db.execute("SELECT icon, ai_name FROM sessions WHERE id = ?", (session_id,)).fetchone()
    db.close()
    return dict(session) if session else None


def get_session_messages(session_id):
    db = get_db()
    messages = db.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
                          (session_id,)).fetchall()
    db.close()
    return [dict(row) for row in messages]


def create_session(session_id, title, system_prompt, icon='bot.svg', ai_name=None):
    db = get_db()
    db.execute("INSERT INTO sessions (id, title, icon, ai_name) VALUES (?, ?, ?, ?)",
               (session_id, title, icon, ai_name))
    db.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
               (session_id, 'system', system_prompt))
    db.commit()
    db.close()


def add_message(session_id, role, content):
    db = get_db()
    db.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (session_id, role, content))
    db.commit()
    db.close()


def delete_session(session_id):
    db = get_db()
    db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    db.commit()
    db.close()


def rename_session(session_id, new_title):
    db = get_db()
    db.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, session_id))
    db.commit()
    db.close()


def replace_history_with_summary(session_id, system_prompt, summary_content):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ? AND role != 'system'", (session_id,))
    cursor.execute("UPDATE messages SET content = ? WHERE session_id = ? AND role = 'system'",
                   (system_prompt['content'], session_id))
    cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (?, 'assistant', ?)",
                   (session_id, f"Previous conversation summary: {summary_content}"))
    db.commit()
    db.close()


def delete_last_assistant_message(session_id):
    db = get_db()
    cursor = db.cursor()
    last_message_id_row = cursor.execute(
        "SELECT id FROM messages WHERE session_id = ? AND role = 'assistant' ORDER BY timestamp DESC, id DESC LIMIT 1",
        (session_id,)).fetchone()
    if last_message_id_row:
        cursor.execute("DELETE FROM messages WHERE id = ?", (last_message_id_row['id'],))
        db.commit()
        db.close()
        return True
    db.close()
    return False


def migrate_from_json(default_settings):
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
    db.close()
    if count == 0:
        print("No database found. Populating with default settings.")
        save_settings_and_prompts(default_settings)