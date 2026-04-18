import { useState, useEffect, useCallback, useRef } from 'react';
import mqtt from 'mqtt';
import type { TelemetryPayload, TelemetryHistory, HistoricalDataPoint } from '@/types/telemetry.types';

const BROKER_URL = import.meta.env.VITE_MQTT_BROKER_URL || 'wss://localhost:8884/mqtt';
const MQTT_USER  = import.meta.env.VITE_MQTT_USER || '';
const MQTT_PASS  = import.meta.env.VITE_MQTT_PASS || '';
const TOPIC = import.meta.env.VITE_MQTT_TOPIC || 'hydrov/+/telemetry';

// ─── Hook ─────────────────────────────────────────────────────────────────────

interface UseHydroDataReturn {
  telemetry: TelemetryPayload | null;
  history: TelemetryHistory | null;
  isConnected: boolean;
  isLoading: boolean;
  lastUpdate: Date | null;
  reconnect: () => void;
}

export function useHydroData(): UseHydroDataReturn {
  const [telemetry, setTelemetry] = useState<TelemetryPayload | null>(null);
  
  const [history, setHistory] = useState<TelemetryHistory>({
    turbidity: [],
    flow: [],
    level: [],
  });
  
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  
  const clientRef = useRef<mqtt.MqttClient | null>(null);

  useEffect(() => {
    setIsLoading(true);
    
    // 1. Client ID Dinámico (Moviendo options dentro del useEffect para que sea fresh)
    const options: mqtt.IClientOptions = {
      username: MQTT_USER,
      password: MQTT_PASS,
      clientId: 'hydrov-web-' + Math.random().toString(16).substring(2, 8),
      protocol: 'wss',
      reconnectPeriod: 5000,
      connectTimeout: 30 * 1000,
    };

    // 3. Path del WebSocket está en BROKER_URL arriba
    const client = mqtt.connect(BROKER_URL, options);
    clientRef.current = client;

    client.on('connect', () => {
      console.log(`✅ Conectado al broker MQTT (ID: ${options.clientId})`);
      setIsConnected(true);
      setIsLoading(false);
      
      client.subscribe(TOPIC, (err) => {
        if (!err) {
          console.log(`📡 Suscrito exitosamente a: ${TOPIC}`);
        } else {
          console.error('❌ Error al suscribirse:', err);
        }
      });
    });

    client.on('message', (topic, message) => {
      if (topic === TOPIC) {
        try {
          const raw = JSON.parse(message.toString());
          
          const getStatus = (ntu: number) => {
            if (ntu < 1) return 'clear';
            if (ntu < 4) return 'moderate';
            if (ntu < 10) return 'turbid';
            return 'critical';
          };

          const distance_cm = parseFloat(raw.sensors?.distance_cm || "0");
          const ntu = parseFloat(raw.sensors?.turbidity_ntu || "0");
          const flow_lpm = parseFloat(raw.sensors?.flow_lpm || "0");
          const flow_total = parseFloat(raw.sensors?.flow_total_liters || "0");

          const TANK_CAPACITY = 1100;
          const max_depth_cm = 200;
          let percentage = (1 - (distance_cm / max_depth_cm)) * 100;
          percentage = Math.max(0, Math.min(100, percentage));
          const liters = parseFloat(((percentage / 100) * TANK_CAPACITY).toFixed(1));

          const consumption_rate_lpd = 68.3;
          const days_remaining = Math.round(liters / consumption_rate_lpd);
          const emptyDate = new Date();
          emptyDate.setDate(emptyDate.getDate() + days_remaining);

          const payload: TelemetryPayload = {
            device_id: raw.device_id || 'HYDRO-V-001',
            timestamp: new Date().toISOString(),
            turbidity: {
              raw_ntu: Math.round(ntu * 80 + 200),
              ntu: ntu,
              status: getStatus(ntu),
            },
            level: {
              distance_cm: distance_cm,
              liters: liters,
              percentage: parseFloat(percentage.toFixed(1)),
              tank_capacity_liters: TANK_CAPACITY,
            },
            flow: {
              rate_lpm: flow_lpm,
              total_liters: flow_total,
            },
            leak: {
              status: raw.system_state?.error_count > 0 ? 'leak_detected' : 'stable',
              confidence: 0.95,
              last_checked: new Date().toISOString()
            },
            autonomy: {
              days_remaining: days_remaining,
              consumption_rate_lpd: consumption_rate_lpd,
              predicted_empty_date: emptyDate.toISOString().split('T')[0],
              regression_r2: 0.89,
              confidence: days_remaining > 5 ? 'high' : 'medium'
            },
            connection_status: 'online',
            uptime_seconds: typeof raw.timestamp === 'number' ? Math.floor(raw.timestamp / 1000) : 0
          };
          
          setTelemetry(payload);
          const now = new Date();
          setLastUpdate(now);

          setHistory(prev => {
            const addPoint = (arr: HistoricalDataPoint[], value: number) =>
              [...arr.slice(-23), { timestamp: now.toISOString(), value }];

            return {
              turbidity: addPoint(prev.turbidity, payload.turbidity.ntu),
              flow: addPoint(prev.flow, payload.flow.rate_lpm),
              level: addPoint(prev.level, payload.level.liters),
            };
          });
        } catch (error) {
          console.error('❌ Error al parsear JSON MQTT y mapear a Telemetría:', error);
        }
      }
    });

    client.on('reconnect', () => {
      console.warn('⚠️ Intentando reconectar a MQTT...');
      setIsConnected(false);
    });

    client.on('offline', () => {
      console.warn('🔌 Cliente MQTT desconectado (offline).');
      setIsConnected(false);
      setIsLoading(false);
    });

    client.on('error', (err) => {
      console.error('🚨 Error MQTT:', err);
      setIsConnected(false);
      setIsLoading(false);
    });

    // 2. Limpieza estricta: matar la conexión cuando el componente se desmonte
    return () => {
      console.log('🧹 Limpiando conexión MQTT...');
      client.end(true); // force close
    };
  }, []); // <-- 2. Arreglo de dependencias vacío para inicializar una sola vez

  const manualReconnect = useCallback(() => {
    if (clientRef.current) {
      console.log('🔄 Reconexión manual solicitada');
      clientRef.current.reconnect();
    }
  }, []);

  return { 
    telemetry, 
    history, 
    isConnected, 
    isLoading, 
    lastUpdate, 
    reconnect: manualReconnect 
  };
}
