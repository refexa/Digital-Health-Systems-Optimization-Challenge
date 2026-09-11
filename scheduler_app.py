from flask import Flask, request, jsonify, send_file, make_response
from datetime import datetime, timedelta
import sqlite3
import os
import io
import csv

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'scheduler.db')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS slots (
  id TEXT PRIMARY KEY,
  time TEXT NOT NULL,
  capacity INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot_id TEXT NOT NULL,
  patient TEXT,
  booked_at TEXT,
  priority INTEGER DEFAULT 0,
  FOREIGN KEY(slot_id) REFERENCES slots(id)
);
'''

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(default_capacity=1):
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    cur.execute('SELECT COUNT(1) as c FROM slots')
    if cur.fetchone()[0] == 0:
        base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        for d in range(0, 7):
            day = base + timedelta(days=d)
            for i in range(0, 16):
                slot_time = day + timedelta(minutes=30 * i)
                sid = slot_time.isoformat()
                cur.execute('INSERT INTO slots (id, time, capacity) VALUES (?, ?, ?)', (sid, sid, default_capacity))
        conn.commit()
    conn.close()

init_db()

def is_admin(req):
    token = req.headers.get('X-Admin-Token')
    return token is not None and token == os.environ.get('ADMIN_TOKEN', 'adminpass')

def fetch_slots():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, time, capacity FROM slots ORDER BY time')
    slots = []
    for r in cur.fetchall():
        cur.execute('SELECT patient, booked_at, priority FROM bookings WHERE slot_id = ? ORDER BY booked_at', (r['id'],))
        b = [dict(x) for x in cur.fetchall()]
        slots.append({'id': r['id'], 'time': r['time'], 'capacity': r['capacity'], 'bookings': b})
    conn.close()
    return slots

def find_nearest_available_db(requested_time_iso):
    try:
        req = datetime.fromisoformat(requested_time_iso)
    except Exception:
        return None
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT s.id, s.time, s.capacity, (SELECT COUNT(1) FROM bookings b WHERE b.slot_id = s.id) as booked FROM slots s')
    best = None
    best_delta = None
    for s in cur.fetchall():
        if s['booked'] < s['capacity']:
            s_time = datetime.fromisoformat(s['time'])
            delta = abs((s_time - req).total_seconds())
            if best_delta is None or delta < best_delta:
                best = dict(s)
                best_delta = delta
    conn.close()
    return best

@app.route('/slots', methods=['GET'])
def get_slots():
    return jsonify(fetch_slots())

@app.route('/')
def ui():
    return send_file(os.path.join(os.path.dirname(__file__), 'ui.html'))

@app.route('/book', methods=['POST'])
def book():
    data = request.json or {}
    slot_id = data.get('slot_id')
    patient = data.get('patient', 'unknown')
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT capacity FROM slots WHERE id = ?', (slot_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'slot not found'}), 404
    capacity = row['capacity']
    cur.execute('SELECT COUNT(1) as c FROM bookings WHERE slot_id = ?', (slot_id,))
    booked = cur.fetchone()['c']
    if booked < capacity:
        cur.execute('INSERT INTO bookings (slot_id, patient, booked_at, priority) VALUES (?, ?, ?, ?)', (slot_id, patient, datetime.now().isoformat(), 0))
        conn.commit()
        conn.close()
        return jsonify({'status':'booked'}), 201
    conn.close()
    suggested = find_nearest_available_db(slot_id)
    if suggested:
        return jsonify({'status':'full','suggested': suggested}), 409
    return jsonify({'status':'full','message':'no available slots'}), 409

@app.route('/book_priority', methods=['POST'])
def book_priority():
    # staff-only: require admin token
    if not is_admin(request):
        return jsonify({'error': 'unauthorized'}), 401
    data = request.json or {}
    slot_id = data.get('slot_id')
    patient = data.get('patient', 'unknown')
    try:
        priority = int(data.get('priority', 0))
    except Exception:
        priority = 0
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT capacity FROM slots WHERE id = ?', (slot_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'error':'slot not found'}), 404
    capacity = row['capacity']
    cur.execute('SELECT id, priority FROM bookings WHERE slot_id = ? ORDER BY priority ASC, booked_at ASC', (slot_id,))
    bookings = cur.fetchall()
    if len(bookings) < capacity:
        cur.execute('INSERT INTO bookings (slot_id, patient, booked_at, priority) VALUES (?, ?, ?, ?)', (slot_id, patient, datetime.now().isoformat(), priority))
        conn.commit()
        conn.close()
        return jsonify({'status':'booked'}), 201
    lowest = bookings[0]
    if lowest and lowest['priority'] < priority:
        cur.execute('DELETE FROM bookings WHERE id = ?', (lowest['id'],))
        cur.execute('INSERT INTO bookings (slot_id, patient, booked_at, priority) VALUES (?, ?, ?, ?)', (slot_id, patient, datetime.now().isoformat(), priority))
        conn.commit()
        conn.close()
        return jsonify({'status':'booked_preempt','preempted_id': lowest['id']}), 201
    conn.close()
    suggested = find_nearest_available_db(slot_id)
    if suggested:
        return jsonify({'status':'full','suggested': suggested}), 409
    return jsonify({'status':'full','message':'no available slots'}), 409

@app.route('/set_capacity', methods=['POST'])
def set_capacity():
    # staff-only operation
    if not is_admin(request):
        return jsonify({'error':'unauthorized'}), 401
    data = request.json or {}
    slot_id = data.get('slot_id')
    try:
        cap = int(data.get('capacity', 0))
    except Exception:
        return jsonify({'error':'invalid capacity'}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE slots SET capacity = ? WHERE id = ?', (cap, slot_id))
    conn.commit()
    cur.execute('SELECT id, time, capacity FROM slots WHERE id = ?', (slot_id,))
    r = cur.fetchone()
    conn.close()
    if r:
        return jsonify({'status':'ok','slot': dict(r)})
    return jsonify({'error':'slot not found'}), 404

@app.route('/export', methods=['GET'])
def export_csv():
    # staff-only export
    if not is_admin(request):
        return jsonify({'error':'unauthorized'}), 401
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT s.id, s.time, s.capacity, (SELECT COUNT(1) FROM bookings b WHERE b.slot_id = s.id) as booked FROM slots s ORDER BY s.time')
    rows = cur.fetchall()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['slot_id','slot_time','capacity','booked_count','bookings'])
    for r in rows:
        cur.execute('SELECT patient, booked_at, priority FROM bookings WHERE slot_id = ? ORDER BY booked_at', (r[0],))
        bookings = cur.fetchall()
        details = ';'.join([f"{b[0]}|{b[1]}|p{b[2]}" for b in bookings])
        cw.writerow([r[0], r[1], r[2], r[3], details])
    conn.close()
    output = make_response(si.getvalue())
    output.headers['Content-Type'] = 'text/csv'
    output.headers['Content-Disposition'] = 'attachment; filename=schedule_export.csv'
    return output


@app.route('/metrics', methods=['GET'])
def metrics():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(1) as total FROM slots')
    total = cur.fetchone()['total']
    cur.execute('SELECT COUNT(1) as booked FROM bookings')
    booked = cur.fetchone()['booked']
    cur.execute('SELECT booked, COUNT(1) as cnt FROM (SELECT s.id, (SELECT COUNT(1) FROM bookings b WHERE b.slot_id = s.id) as booked FROM slots s) GROUP BY booked')
    dist_rows = cur.fetchall()
    dist = {row[0]: row[1] for row in dist_rows}
    conn.close()
    utilization = booked / total if total else 0
    avg = booked / total if total else 0
    return jsonify({'total_slots': total, 'booked': booked, 'utilization': utilization, 'avg_bookings_per_slot': avg, 'distribution': dist})

@app.route('/reset', methods=['POST'])
def reset():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    return jsonify({'status':'reset'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
