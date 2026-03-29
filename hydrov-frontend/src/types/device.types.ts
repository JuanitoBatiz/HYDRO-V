export interface HydroDevice {
  id: string;
  name: string;
  location: string;
  firmware_version: string;
  hardware: 'ESP32-DOIT-V1';
  is_active: boolean;
  last_seen: string;
}

export interface ValveState {
  id: string;
  label: string;
  is_open: boolean;
  auto_mode: boolean;
}

export interface SystemAlert {
  id: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  timestamp: string;
  acknowledged: boolean;
}
