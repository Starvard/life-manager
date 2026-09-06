"""Family species ownership; durable atomic JSON writes with cross-worker locking."""
import csv
import fcntl
import io
import json
import os
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from flask import Blueprint, jsonify, render_template, request, Response
import config

bp = Blueprint('pokedex', __name__)
CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'static/data/pokedex.json').read_text())
IDS = {p['id'] for p in CATALOG}
PEOPLE = ['Ben', 'Jenna', 'Rosemary']

@contextmanager
def storage():
    root = Path(config.DATA_DIR) / 'pokedex'
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / 'collections.json'
        state = json.loads(path.read_text()) if path.exists() else {'people': PEOPLE[:], 'counts': {}, 'wishes': {}}
        yield state, path
        fcntl.flock(lock, fcntl.LOCK_UN)

def save(state, path):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as output:
        json.dump(state, output)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)

def same_origin():
    # Match the existing household access model, but reject cross-site mutations.
    origin = request.headers.get('Origin')
    # Fly terminates TLS before forwarding HTTP to Flask. Compare the public
    # host rather than Flask's internal scheme; never trust forwarded headers.
    parsed = urlsplit(origin) if origin else None
    return (not parsed or (parsed.scheme in ('http', 'https') and parsed.netloc == request.host)) and request.headers.get('Sec-Fetch-Site') != 'cross-site'

@bp.get('/pokedex')
def page():
    return render_template('pokedex.html')

@bp.get('/api/pokedex')
def state():
    with storage() as (data, _):
        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-store'
        return response

@bp.post('/api/pokedex')
def update():
    if not same_origin():
        return jsonify(error='Please save from Life Manager.'), 403
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Expected a JSON object.'), 400
    with storage() as (state, path):
        person = data.get('person')
        species = data.get('species')
        if person not in state['people'] or type(species) is not int or species not in IDS:
            return jsonify(error='Choose a collector and valid Pokémon.'), 400
        key = str(species)
        if data.get('action') == 'wish' and type(data.get('value')) is bool:
            state['wishes'].setdefault(person, {})[key] = data['value']
        elif data.get('action') == 'count' and type(data.get('delta')) is int and data['delta'] in (-1, 1):
            counts = state['counts'].setdefault(person, {})
            counts[key] = max(0, min(9999, counts.get(key, 0) + data['delta']))
        else:
            return jsonify(error='Invalid change.'), 400
        save(state, path)
        return jsonify(state)

@bp.get('/api/pokedex/export')
def export():
    with storage() as (state, _):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(['Collector', 'Pokedex number', 'Pokemon', 'Quantity', 'Wishlist'])
        for person in state['people']:
            for p in CATALOG:
                key = str(p['id'])
                count = state['counts'].get(person, {}).get(key, 0)
                wish = state['wishes'].get(person, {}).get(key, False)
                if count or wish:
                    writer.writerow([person, p['id'], p['name'], count, wish])
        return Response(stream.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=family-pokedex.csv', 'Cache-Control': 'no-store'})
