const API_BASE = '/api/v1';

function authHeader() {
  const token = localStorage.getItem('hydrov_token');
  return {
    'Authorization': token ? `Bearer ${token}` : '',
    'Content-Type': 'application/json'
  };
}

export const DeviceService = {
  async sendCommand(deviceCode: string, action: string, notes?: string) {
    const res = await fetch(`${API_BASE}/devices/${deviceCode}/command`, {
      method: 'POST',
      headers: authHeader(),
      body: JSON.stringify({ action, notes })
    });
    if (!res.ok) throw new Error('Failed to send command');
    return res.json();
  },

  async getActiveZoneAlerts(zoneCode: string) {
    const res = await fetch(`${API_BASE}/zones/${zoneCode}/alerts/active`, { headers: authHeader() });
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return res.json();
  }
};
