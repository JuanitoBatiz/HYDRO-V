const API_BASE = '/api/v1';

function authHeader() {
  const token = localStorage.getItem('hydrov_token');
  return {
    'Authorization': token ? `Bearer ${token}` : '',
    'Content-Type': 'application/json'
  };
}

export const TelemetryService = {
  async getLatestTelemetry(deviceCode: string) {
    const res = await fetch(`${API_BASE}/devices/${deviceCode}/latest`, { headers: authHeader() });
    if (!res.ok) throw new Error('Failed to fetch telemetry');
    return res.json();
  },

  async getDeviceStatus(deviceCode: string) {
    const res = await fetch(`${API_BASE}/devices/${deviceCode}/status`, { headers: authHeader() });
    if (!res.ok) throw new Error('Failed to fetch status');
    return res.json();
  },

  async getAutonomyPrediction(deviceCode: string) {
    const res = await fetch(`${API_BASE}/devices/${deviceCode}/predict`, { headers: authHeader() });
    if (!res.ok) throw new Error('Failed to fetch prediction');
    return res.json();
  },

  async getTelemetryHistory(deviceCode: string, hours: number = 24) {
    const res = await fetch(`${API_BASE}/telemetry/${deviceCode}/history?hours=${hours}`, { headers: authHeader() });
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
  }
};
