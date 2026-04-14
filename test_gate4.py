import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def print_step(msg):
    print(f"\n[{time.strftime('%X')}] {msg}")

def run_tests():
    # 4.3 Registrar zona y dispositivo
    print_step("Paso 4.3: Registrando Zona (NEZ-01)...")
    try:
        r = requests.post(f"{BASE_URL}/zones", json={
            "zone_code": "NEZ-01",
            "name": "Juárez Pantitlán",
            "municipality": "Ciudad Nezahualcóyotl",
            "state": "Estado de México",
            "latitude": 19.4072,
            "longitude": -99.0148
        })
        print(f"Status: {r.status_code}")
        print(r.text)
    except Exception as e:
        print(f"Error conectando a API: {e}")
        return

    print_step("Paso 4.3: Registrando Dispositivo (HV-NEZ-001)...")
    r = requests.post(f"{BASE_URL}/devices", json={
        "zone_id": 1,
        "device_code": "HV-NEZ-001",
        "latitude": 19.4072,
        "longitude": -99.0148,
        "status": "active",
        "firmware_version": "1.0.0",
        "cistern_capacity_liters": 1100.0,
        "cistern_height_cm": 120.0
    })
    print(f"Status: {r.status_code}")
    print(r.text)

    # 4.4 Gate de Verificación
    print_step("Check 4.A: Autenticación funciona (Login)")
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@hydrov.mx",
        "password": "admin123"
    })
    print(f"Status: {r.status_code}")
    print(r.text)

    token = None
    if r.status_code == 200:
        token = r.json().get("access_token")
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    print_step("Check 4.B: Endpoint de estado lee Redis")
    r = requests.get(f"{BASE_URL}/devices/HV-NEZ-001/status", headers=headers)
    print(f"Status: {r.status_code}")
    print(r.text)

    print_step("Check 4.C: Endpoint de historial lee InfluxDB")
    r = requests.get(f"{BASE_URL}/telemetry/HV-NEZ-001/history?hours=1", headers=headers)
    print(f"Status: {r.status_code}")
    print(r.text)

    print_step("Check 4.D: Ruta protegida sin token retorna 401")
    r = requests.get(f"{BASE_URL}/devices/HV-NEZ-001/status")
    print(f"Status: {r.status_code}")
    print(r.text)

if __name__ == "__main__":
    run_tests()
