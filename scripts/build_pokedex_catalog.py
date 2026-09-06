"""Refresh bundled species data from the PokeAPI project's CSV dataset."""
import csv
import io
import json
from pathlib import Path
from urllib.request import urlopen

BASE = 'https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/'
def rows(name):
    with urlopen(BASE + name + '.csv', timeout=30) as response:
        return list(csv.DictReader(io.StringIO(response.read().decode())))

names = {int(r['pokemon_species_id']): r['name'] for r in rows('pokemon_species_names') if r['local_language_id'] == '9'}
types = {r['id']: r['identifier'] for r in rows('types')}
pt = {}
for r in rows('pokemon_types'):
    pt.setdefault(int(r['pokemon_id']), []).append(types[r['type_id']])
pokemon = {int(r['species_id']): int(r['id']) for r in rows('pokemon') if r['is_default'] == '1'}
data = [dict(id=int(r['id']), name=names[int(r['id'])], generation=int(r['generation_id']),
             chain=int(r['evolution_chain_id']), parent=int(r['evolves_from_species_id'] or 0),
             types=pt.get(pokemon[int(r['id'])], []), sprite=pokemon[int(r['id'])]) for r in rows('pokemon_species')]
path = Path(__file__).resolve().parents[1] / 'static/data/pokedex.json'
path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
print(f'Saved {len(data)} species')
