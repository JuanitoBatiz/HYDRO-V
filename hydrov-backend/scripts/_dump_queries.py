import json
from pathlib import Path
f = Path('infra/grafana/dashboards/hydrov_mission_control.json')
d = json.loads(f.read_text(encoding='utf-8'))
for p in d['panels']:
    print(f"=== {p['title']} (type={p['type']}) ===")
    for t in p.get('targets', []):
        q = t.get('query','') or t.get('rawSql','')
        print(f"  [{t.get('refId','?')}] {q[:300]}")
    print()
