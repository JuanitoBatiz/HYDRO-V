import json
import os

filepath = r'c:\Users\jesus\OneDrive\Desktop\HYDRO-V\infra\grafana\dashboards\hydrov_mission_control.json'
with open(filepath, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. Update templating variable
for var in data.get('templating', {}).get('list', []):
    if var.get('name') == 'Nodo':
        var['name'] = 'device_id'
        var['label'] = 'Nodo'

def update_panels(panels):
    for panel in panels:
        if panel.get('title') == 'Autonomía Hídrica (IA)':
            for target in panel.get('targets', []):
                # Update infinity URL
                target['url'] = '/api/v1/predictions/${device_id}/autonomy'
                target['url_path'] = '/api/v1/predictions/${device_id}/autonomy'

        # 3. Search for ${Nodo} in other panels
        for target in panel.get('targets', []):
            for key, val in target.items():
                if isinstance(val, str) and '${Nodo}' in val:
                    target[key] = val.replace('${Nodo}', '${device_id}')
                    
        # Check inside options (sometimes queries are nested)
        options = panel.get('options', {})
        if isinstance(options, dict):
            pass # Usually not here, but could be nested deeper. Just target lists mostly.

        # Check rawSql manually just in case
        for target in panel.get('targets', []):
            if 'query' in target and isinstance(target['query'], str):
                target['query'] = target['query'].replace('${Nodo}', '${device_id}')

        # Replace in panel description/title if any? Usually just query is needed
        # It asks "Revisa si hay otros paneles en el JSON que usaban ${Nodo} en sus queries SQL y cámbialos"
        
        # also check inner panels if any
        if 'panels' in panel:
            update_panels(panel['panels'])

# For anything else, we can do a global string replace as well but JSON parse/dump is safer.
# Let's also do a string replace on the dumped JSON just to catch anything we missed in target hierarchies or variables
# Wait, let's just do a recursive dict replace for better safety!

def recursive_replace(d):
    if isinstance(d, dict):
        for k, v in d.items():
            if k == 'title' and v == 'Autonomía Hídrica (IA)':
                # specific rule for this panel's targets
                targets = d.get('targets', [])
                for t in targets:
                    if 'url' in t:
                        t['url'] = '/api/v1/predictions/${device_id}/autonomy'
                    if 'url_path' in t:
                        t['url_path'] = '/api/v1/predictions/${device_id}/autonomy'
            if isinstance(v, str):
                if '${Nodo}' in v:
                    d[k] = v.replace('${Nodo}', '${device_id}')
            else:
                recursive_replace(v)
    elif isinstance(d, list):
        for item in d:
            recursive_replace(item)

recursive_replace(data.get('panels', []))

with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print('Modifications complete.')
