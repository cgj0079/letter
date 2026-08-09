from flask import Flask, jsonify, request, send_from_directory, abort
import sqlite3
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'letters.db'
HTML_FILE = 'index2.html'

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path='')


def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not DB_PATH.exists():
        with get_db_connection() as conn:
            conn.execute(
                '''
                CREATE TABLE letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dateRaw TEXT NOT NULL,
                    theme TEXT NOT NULL,
                    content TEXT NOT NULL,
                    createdAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            conn.commit()


def serialize_letter(row):
    return {
        'id': row['id'],
        'dateRaw': row['dateRaw'],
        'theme': row['theme'],
        'content': row['content'],
    }


@app.after_request
def apply_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response


@app.route('/')
def index():
    return send_from_directory(BASE_DIR, HTML_FILE)


@app.route('/api/letters', methods=['OPTIONS'])
def letters_options():
    return '', 204


@app.route('/api/letters', methods=['GET', 'POST'])
def letters_collection():
    if request.method == 'GET':
        with get_db_connection() as conn:
            rows = conn.execute(
                'SELECT id, dateRaw, theme, content FROM letters ORDER BY dateRaw DESC, id DESC'
            ).fetchall()
        return jsonify([serialize_letter(row) for row in rows])

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    theme = (data.get('theme') or '').strip() or 'night'
    date_raw = (data.get('dateRaw') or '').strip() or date.today().isoformat()

    if not content:
        abort(400, 'content is required')

    with get_db_connection() as conn:
        cursor = conn.execute(
            'INSERT INTO letters (dateRaw, theme, content) VALUES (?, ?, ?)',
            (date_raw, theme, content)
        )
        conn.commit()
        letter_id = cursor.lastrowid
        row = conn.execute(
            'SELECT id, dateRaw, theme, content FROM letters WHERE id = ?', (letter_id,)
        ).fetchone()

    return jsonify(serialize_letter(row)), 201


@app.route('/api/letters/<int:letter_id>', methods=['OPTIONS'])
def letter_options(letter_id):
    return '', 204


@app.route('/api/letters/<int:letter_id>', methods=['PUT', 'DELETE'])
def letter_item(letter_id):
    if request.method == 'DELETE':
        with get_db_connection() as conn:
            conn.execute('DELETE FROM letters WHERE id = ?', (letter_id,))
            conn.commit()
        return '', 204

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    theme = (data.get('theme') or '').strip() or 'night'
    date_raw = (data.get('dateRaw') or '').strip() or date.today().isoformat()

    if not content:
        abort(400, 'content is required')

    with get_db_connection() as conn:
        conn.execute(
            'UPDATE letters SET dateRaw = ?, theme = ?, content = ? WHERE id = ?',
            (date_raw, theme, content, letter_id)
        )
        conn.commit()
        row = conn.execute(
            'SELECT id, dateRaw, theme, content FROM letters WHERE id = ?', (letter_id,)
        ).fetchone()

    if row is None:
        abort(404, 'Letter not found')

    return jsonify(serialize_letter(row))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
