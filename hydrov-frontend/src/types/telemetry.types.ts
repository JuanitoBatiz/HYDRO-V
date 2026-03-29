// Telemetry payload types matching the Hydro-V MQTT standard
export interface SensorTurbidity {
  raw_ntu: number;      // 0-4095 raw ADC value from ESP32
  ntu: number;          // Calibrated NTU value
  status: 'clear' | 'moderate' | 'turbid' | 'critical';
}

export interface SensorLevel {
  distance_cm: number;  // Distance from sensor to water surface
  liters: number;       // Calculated volume in liters
  percentage: number;   // 0-100% of tank capacity
  tank_capacity_liters: number;
}

export interface SensorFlow {
  rate_lpm: number;     // Liters per minute
  total_liters: number; // Cumulative total
}

export interface LeakStatus {
  status: 'stable' | 'leak_detected' | 'investigating';
  confidence: number;   // 0-1 GNN confidence score
  location_hint?: string;
  last_checked: string; // ISO timestamp
}

export interface AutonomyPrediction {
  days_remaining: number;
  consumption_rate_lpd: number; // Liters per day
  predicted_empty_date: string; // ISO date string
  regression_r2: number;        // Linear regression R² score
  confidence: 'high' | 'medium' | 'low';
}

export interface TelemetryPayload {
  device_id: string;
  timestamp: string;
  turbidity: SensorTurbidity;
  level: SensorLevel;
  flow: SensorFlow;
  leak: LeakStatus;
  autonomy: AutonomyPrediction;
  connection_status: 'online' | 'offline' | 'degraded';
  uptime_seconds: number;
}

export interface HistoricalDataPoint {
  timestamp: string;
  value: number;
}

export interface TelemetryHistory {
  turbidity: HistoricalDataPoint[];
  flow: HistoricalDataPoint[];
  level: HistoricalDataPoint[];
}
