import requests, random, time

BASE = 'http://127.0.0.1:5000'

def list_slots():
    return requests.get(f'{BASE}/slots').json()

def attempt_booking(slot_id, patient):
    return requests.post(f'{BASE}/book', json={'slot_id': slot_id, 'patient': patient})

def simulate(n=100, delay=0.01):
    slots = list_slots()
    slot_ids = [s['id'] for s in slots]
    for i in range(n):
        slot = random.choice(slot_ids)
        r = attempt_booking(slot, f'patient-{i}')
        try:
            payload = r.json()
        except Exception:
            payload = r.text
        print(i, r.status_code, payload)
        time.sleep(delay)

if __name__ == '__main__':
    simulate()
