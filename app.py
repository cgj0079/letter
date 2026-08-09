from flask import Flask, jsonify, request, send_from_directory, abort
import sqlite3
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'letters.db'
HTML_FILE = 'index.html'

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path='')


def get_db_connection():
    # SQLite DB 연결 객체 생성 및 반환
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # letters.db 파일 유무와 상관없이 테이블이 없으면 자동 생성
    with get_db_connection() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dateRaw TEXT NOT NULL,
                theme TEXT NOT NULL,
                content TEXT NOT NULL,
                createdAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        conn.commit()

# Render/Gunicorn 환경에서도 모듈이 로드될 때 DB와 테이블을 즉시 초기화
init_db()


def serialize_letter(row):
    # DB Row 객체를 JSON 응답용 딕셔너리로 변환
    return {
        'id': row['id'],
        'dateRaw': row['dateRaw'],
        'theme': row['theme'],
        'content': row['content'],
    }


@app.after_request
def apply_cors(response):
    # CORS 헤더 추가 (크로스 도메인 요청 허용)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response


@app.route('/')
def index():
    # 메인 HTML 페이지 응답
    return send_from_directory(BASE_DIR, HTML_FILE)


@app.route('/api/letters', methods=['OPTIONS'])
def letters_options():
    # Preflight 요청 처리
    return '', 204


@app.route('/api/letters', methods=['GET', 'POST'])
def letters_collection():
    if request.method == 'GET':
        # 편지 목록 조회
        with get_db_connection() as conn:
            rows = conn.execute(
                'SELECT id, dateRaw, theme, content FROM letters ORDER BY dateRaw DESC, id DESC'
            ).fetchall()
        return jsonify([serialize_letter(row) for row in rows])

    # 새 편지 작성 (POST)
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
    # 단일 항목 Preflight 요청 처리
    return '', 204


@app.route('/api/letters/<int:letter_id>', methods=['PUT', 'DELETE'])
def letter_item(letter_id):
    if request.method == 'DELETE':
        # 편지 삭제
        with get_db_connection() as conn:
            conn.execute('DELETE FROM letters WHERE id = ?', (letter_id,))
            conn.commit()
        return '', 204

    # 편지 수정 (PUT)
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
    app.run(host='0.0.0.0', port=5000, debug=True)
