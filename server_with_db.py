import http.server
import json
import sqlite3
import os
import urllib.parse

PORT = 3031
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'tracker.db')

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Таблица статусов (отправлено, ответ компании, способ, заметка)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_states (
            id INTEGER PRIMARY KEY,
            sent INTEGER DEFAULT 0,
            status TEXT DEFAULT 'none',
            channel TEXT DEFAULT 'email',
            note TEXT DEFAULT ''
        )
    ''')
    # Таблица пользовательских компаний
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_companies (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT NOT NULL,
            is_sakhalin INTEGER DEFAULT 0,
            sphere TEXT DEFAULT '',
            email TEXT DEFAULT '',
            role TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()

class TrackerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        url_parsed = urllib.parse.urlparse(self.path)
        if url_parsed.path == '/api/data':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Получаем все статусы
            cursor.execute('SELECT id, sent, status, channel, note FROM company_states')
            states_rows = cursor.fetchall()
            states = {}
            for r in states_rows:
                states[r[0]] = {
                    'sent': bool(r[1]),
                    'status': r[2],
                    'channel': r[3],
                    'note': r[4]
                }
                
            # Получаем пользовательские компании
            cursor.execute('SELECT id, name, region, is_sakhalin, sphere, email, role FROM custom_companies')
            custom_rows = cursor.fetchall()
            custom_list = []
            for c in custom_rows:
                custom_list.append({
                    'id': c[0],
                    'name': c[1],
                    'region': c[2],
                    'isSakhalin': bool(c[3]),
                    'isCustom': True,
                    'sphere': c[4],
                    'email': c[5],
                    'role': c[6]
                })
            conn.close()
            
            response_data = {
                'states': states,
                'customCompanies': custom_list
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        url_parsed = urllib.parse.urlparse(self.path)
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len).decode('utf-8')
        
        if url_parsed.path == '/api/save_state':
            data = json.loads(post_body)
            company_id = int(data['id'])
            sent = 1 if data.get('sent', False) else 0
            status = data.get('status', 'none')
            channel = data.get('channel', 'email')
            note = data.get('note', '')
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO company_states (id, sent, status, channel, note)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    sent=excluded.sent,
                    status=excluded.status,
                    channel=excluded.channel,
                    note=excluded.note
            ''', (company_id, sent, status, channel, note))
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success": true}')
            
        elif url_parsed.path == '/api/add_company':
            data = json.loads(post_body)
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Получаем следующий ID > 100
            cursor.execute('SELECT MAX(id) FROM custom_companies')
            max_id = cursor.fetchone()[0]
            new_id = (max_id + 1) if (max_id and max_id >= 101) else 101
            
            is_sakh = 1 if data.get('region') == 'Сахалин' else 0
            cursor.execute('''
                INSERT INTO custom_companies (id, name, region, is_sakhalin, sphere, email, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (new_id, data['name'], data['region'], is_sakh, data.get('sphere', ''), data.get('email', ''), data.get('role', '')))
            
            # Сразу создаем запись статуса
            cursor.execute('''
                INSERT INTO company_states (id, sent, status, channel, note)
                VALUES (?, 1, 'none', ?, ?)
            ''', (new_id, data.get('channel', 'email'), data.get('note', '')))
            
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'id': new_id}).encode('utf-8'))
        else:
            self.send_error(404)

if __name__ == '__main__':
    init_db()
    print(f"=== Сервер базы данных SQLite запущен на http://localhost:{PORT} ===")
    print(f"База данных: {DB_FILE}")
    server = http.server.HTTPServer(('0.0.0.0', PORT), TrackerHandler)
    server.serve_forever()
