import os
import json
import glob

DASHBOARDS_DIR = r"c:\Users\jesus\OneDrive\Desktop\HYDRO-V\infra\grafana\dashboards"

def process_query(query: str) -> str:
    # 1. Measurement changes
    # By default, most things are sensor_reading
    query = query.replace('_measurement == "sensor_telemetry"', '_measurement == "sensor_reading"')
    
    # But state is device_state
    if 'r._field == "state"' in query or 'r._field == "fsm_state"' in query or 'r._field == "valve_rejection"' in query or 'r._field == "valve_admission"' in query:
        query = query.replace('_measurement == "sensor_reading"', '_measurement == "device_state"')
        query = query.replace('r._field == "state"', 'r._field == "fsm_state"')

    # 2. Tag changes
    query = query.replace('r.node_id ==', 'r.device_id ==')

    return query

def update_dashboard(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    changes = 0
    
    # Traverse dashboard panels
    panels = data.get('panels', [])
    for panel in panels:
        targets = panel.get('targets', [])
        for target in targets:
            if 'query' in target:
                old_query = target['query']
                new_query = process_query(old_query)
                if old_query != new_query:
                    target['query'] = new_query
                    changes += 1

    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Updated {changes} queries in {filepath}")
    else:
        print(f"No changes for {filepath}")

if __name__ == "__main__":
    for f in glob.glob(os.path.join(DASHBOARDS_DIR, "*.json")):
        update_dashboard(f)
