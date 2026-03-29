import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sun, CloudRain, Cloud, CloudSnow, CloudLightning,
  Wind, Droplets, Eye, Thermometer, MapPin, RefreshCw,
} from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────────
type WeatherCondition =
  | 'sunny' | 'partly_cloudy' | 'cloudy'
  | 'drizzle' | 'rain' | 'heavy_rain'
  | 'thunderstorm' | 'snow';

interface HourlyForecast {
  hour: string;       // e.g. "3 PM"
  condition: WeatherCondition;
  tempC: number;
  precipMm: number;   // mm of precipitation expected
}

interface WeatherData {
  locationName: string;
  condition: WeatherCondition;
  tempC: number;
  feelsLikeC: number;
  humidityPct: number;
  windKph: number;
  visibilityKm: number;
  uvIndex: number;
  description: string;        // Human-readable summary
  alertMessage?: string;      // Urgent alert (e.g. heavy rain approaching)
  hourly: HourlyForecast[];
  lastFetched: Date;
}

// ─── Mock Data Generator ───────────────────────────────────────────────────────
// Nezahualcóyotl, Estado de México: 19.4017° N, 99.0153° W
const NEZA_LAT = 19.4017;
const NEZA_LON = -99.0153;
const NEZA_NAME = 'Nezahualcóyotl, Edo. Méx.';

// ── Replace this function body with a real API call (e.g. Open-Meteo, WeatherAPI)
// Signature is kept identical so the rest of the component never needs to change.
async function fetchLocalWeather(_lat: number, _lon: number): Promise<WeatherData> {
  // ── 🔌 API Integration Point ──────────────────────────────────────────────────
  // Example with Open-Meteo (free, no key required):
  //
  // const url = `https://api.open-meteo.com/v1/forecast?latitude=${_lat}&longitude=${_lon}`
  //   + `&current=temperature_2m,relative_humidity_2m,apparent_temperature,`
  //   + `weather_code,wind_speed_10m,visibility`
  //   + `&hourly=temperature_2m,precipitation_probability,weather_code&timezone=America/Mexico_City`
  //   + `&forecast_days=1`;
  //
  // const res  = await fetch(url);
  // const json = await res.json();
  // return parseOpenMeteoResponse(json, _lat, _lon);
  // ─────────────────────────────────────────────────────────────────────────────

  // Simulated 300ms network latency
  await new Promise((r) => setTimeout(r, 300));

  // Pick a realistic condition for Mexico City metro area
  const conditions: WeatherCondition[] = ['sunny', 'partly_cloudy', 'cloudy', 'drizzle', 'rain', 'heavy_rain'];
  const idx = Math.floor(Math.random() * conditions.length);
  const main = conditions[idx];

  const baseTemp = 18 + Math.round(Math.random() * 8);

  const hourly: HourlyForecast[] = ['11 AM', '12 PM', '1 PM', '2 PM', '3 PM', '4 PM'].map((h, i) => {
    const hourConditions: WeatherCondition[] = ['partly_cloudy', 'cloudy', 'rain', 'heavy_rain', 'cloudy', 'partly_cloudy'];
    return {
      hour: h,
      condition: hourConditions[i] ?? 'partly_cloudy',
      tempC: baseTemp + Math.round((Math.random() - 0.4) * 4),
      precipMm: i >= 2 && i <= 4 ? +(Math.random() * 8).toFixed(1) : 0,
    };
  });

  const descriptionMap: Record<WeatherCondition, string> = {
    sunny:        'Cielo despejado y soleado',
    partly_cloudy:'Parcialmente nublado',
    cloudy:       'Nublado',
    drizzle:      'Llovizna ligera',
    rain:         'Lluvia moderada',
    heavy_rain:   'Lluvia fuerte',
    thunderstorm: 'Tormenta eléctrica',
    snow:         'Nieve',
  };

  const alertMap: Partial<Record<WeatherCondition, string>> = {
    heavy_rain:   '🌧 Lluvia fuerte en los próximos 20 min. Abre tu trampilla de captación.',
    thunderstorm: '⛈ Tormenta eléctrica cerca. Permanece en casa.',
    rain:         '🌦 Lluvia moderada esperada esta tarde.',
  };

  return {
    locationName: NEZA_NAME,
    condition: main,
    tempC: baseTemp,
    feelsLikeC: baseTemp - 2,
    humidityPct: 55 + Math.round(Math.random() * 30),
    windKph: 10 + Math.round(Math.random() * 20),
    visibilityKm: main === 'heavy_rain' ? 3 : main === 'rain' ? 6 : 10,
    uvIndex: main === 'sunny' ? 7 : main === 'partly_cloudy' ? 4 : 2,
    description: descriptionMap[main],
    alertMessage: alertMap[main],
    hourly,
    lastFetched: new Date(),
  };
}

// ─── Icon + color config per condition ────────────────────────────────────────
interface ConditionStyle {
  Icon: React.ElementType;
  cardGrad: string;   // card background gradient
  iconColor: string;
  badge: string;
}

const CONDITION_STYLES: Record<WeatherCondition, ConditionStyle> = {
  sunny: {
    Icon: Sun,
    cardGrad: 'linear-gradient(160deg, rgba(255,251,235,1) 0%, rgba(254,243,199,0.8) 100%)',
    iconColor: '#f59e0b',
    badge: 'background:rgba(254,243,199,0.9);color:#92400e;border:1px solid rgba(253,230,138,0.8)',
  },
  partly_cloudy: {
    Icon: Cloud,
    cardGrad: 'linear-gradient(160deg, rgba(239,248,255,1) 0%, rgba(224,242,254,0.8) 100%)',
    iconColor: '#60a5fa',
    badge: 'background:rgba(224,242,254,0.9);color:#1e40af;border:1px solid rgba(191,219,254,0.8)',
  },
  cloudy: {
    Icon: Cloud,
    cardGrad: 'linear-gradient(160deg, rgba(248,250,252,1) 0%, rgba(241,245,249,0.9) 100%)',
    iconColor: '#94a3b8',
    badge: 'background:rgba(241,245,249,0.9);color:#334155;border:1px solid rgba(203,213,225,0.8)',
  },
  drizzle: {
    Icon: CloudRain,
    cardGrad: 'linear-gradient(160deg, rgba(239,246,255,1) 0%, rgba(219,234,254,0.9) 100%)',
    iconColor: '#3b82f6',
    badge: 'background:rgba(219,234,254,0.9);color:#1e40af;border:1px solid rgba(191,219,254,0.8)',
  },
  rain: {
    Icon: CloudRain,
    cardGrad: 'linear-gradient(160deg, rgba(239,246,255,1) 0%, rgba(207,226,255,0.9) 100%)',
    iconColor: '#2563eb',
    badge: 'background:rgba(207,226,255,0.9);color:#1e3a8a;border:1px solid rgba(147,197,253,0.8)',
  },
  heavy_rain: {
    Icon: CloudRain,
    cardGrad: 'linear-gradient(160deg, rgba(238,242,255,1) 0%, rgba(199,210,254,0.9) 100%)',
    iconColor: '#4f46e5',
    badge: 'background:rgba(199,210,254,0.9);color:#312e81;border:1px solid rgba(165,180,252,0.8)',
  },
  thunderstorm: {
    Icon: CloudLightning,
    cardGrad: 'linear-gradient(160deg, rgba(245,243,255,1) 0%, rgba(233,213,255,0.9) 100%)',
    iconColor: '#7c3aed',
    badge: 'background:rgba(233,213,255,0.9);color:#4c1d95;border:1px solid rgba(196,181,253,0.8)',
  },
  snow: {
    Icon: CloudSnow,
    cardGrad: 'linear-gradient(160deg, rgba(240,249,255,1) 0%, rgba(224,242,254,0.9) 100%)',
    iconColor: '#38bdf8',
    badge: 'background:rgba(224,242,254,0.9);color:#0c4a6e;border:1px solid rgba(186,230,253,0.8)',
  },
};

// Lucide icon per condition (for hourly forecast pills)
function ConditionIcon({ condition, size = 'md' }: { condition: WeatherCondition; size?: 'sm' | 'md' | 'lg' }) {
  const { Icon, iconColor } = CONDITION_STYLES[condition];
  const sz = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-10 h-10' : 'w-6 h-6';
  return <Icon className={sz} style={{ color: iconColor }} aria-hidden="true" />;
}

// ─── Main Widget ───────────────────────────────────────────────────────────────
export function RainPredictorWidget() {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadWeather = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLocalWeather(NEZA_LAT, NEZA_LON);
      setWeather(data);
    } catch (e) {
      setError('No se pudo cargar el clima. Revisa tu conexión.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWeather();
    // Refresh every 10 min
    const interval = setInterval(loadWeather, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, [loadWeather]);

  if (loading && !weather) {
    return (
      <div
        className="rounded-2xl p-6 flex items-center justify-center gap-3"
        style={{
          background: 'linear-gradient(160deg, rgba(239,248,255,1) 0%, rgba(224,242,254,0.8) 100%)',
          border: '1px solid rgba(186,230,253,0.7)',
          minHeight: 180,
        }}
        aria-label="Cargando clima..."
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
        >
          <RefreshCw className="w-5 h-5 text-brand-400" aria-hidden="true" />
        </motion.div>
        <span className="text-base text-neutral-500 font-medium">Cargando clima local…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-2xl p-6"
        style={{ background: '#fff1f2', border: '1px solid #fecdd3' }}
        role="alert"
      >
        <p className="text-base font-semibold text-rose-700">{error}</p>
        <button onClick={loadWeather} className="mt-3 text-sm font-bold text-rose-600 underline">
          Intentar de nuevo
        </button>
      </div>
    );
  }

  if (!weather) return null;

  const style = CONDITION_STYLES[weather.condition];
  const MainIcon = style.Icon;

  const timeStr = weather.lastFetched.toLocaleTimeString('es-MX', {
    hour: '2-digit', minute: '2-digit',
  });

  return (
    <motion.section
      aria-label="Pronóstico del clima"
      className="overflow-hidden rounded-2xl"
      style={{
        background: style.cardGrad,
        border: '1px solid rgba(186,230,253,0.6)',
        boxShadow: '0 4px 20px rgba(14,141,230,0.07), 0 1px 4px rgba(0,0,0,0.05)',
      }}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-neutral-400 shrink-0" aria-hidden="true" />
          <div>
            <h2 className="text-base font-bold text-neutral-800 leading-tight">{weather.locationName}</h2>
            <p className="text-xs text-neutral-500">Actualizado a las {timeStr}</p>
          </div>
        </div>
        <button
          onClick={loadWeather}
          disabled={loading}
          className="p-2 rounded-xl hover:bg-white/60 transition-colors text-neutral-400 hover:text-neutral-700"
          aria-label="Actualizar clima"
          title="Actualizar"
          style={{ minHeight: 36, minWidth: 36 }}
        >
          <motion.div animate={loading ? { rotate: 360 } : { rotate: 0 }} transition={loading ? { duration: 1, repeat: Infinity, ease: 'linear' } : {}}>
            <RefreshCw className="w-4 h-4" aria-hidden="true" />
          </motion.div>
        </button>
      </div>

      {/* Main condition row */}
      <div className="px-5 pb-4 flex items-center gap-5">
        {/* Animated main icon */}
        <motion.div
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          className="shrink-0"
        >
          <MainIcon
            style={{ color: style.iconColor, width: 56, height: 56 }}
            aria-hidden="true"
          />
        </motion.div>

        <div className="flex-1">
          <div className="flex items-baseline gap-2">
            <span className="text-5xl font-black text-neutral-900 tabular-nums">{weather.tempC}</span>
            <span className="text-2xl font-semibold text-neutral-400">°C</span>
          </div>
          <p className="text-base font-semibold text-neutral-700 mt-0.5">{weather.description}</p>
          <p className="text-sm text-neutral-500">Sensación: {weather.feelsLikeC}°C</p>
        </div>
      </div>

      {/* Alert banner (if active) */}
      <AnimatePresence>
        {weather.alertMessage && (
          <motion.div
            className="mx-5 mb-4 px-4 py-3 rounded-xl"
            style={{
              background: 'rgba(99,102,241,0.08)',
              border: '1px solid rgba(99,102,241,0.2)',
            }}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <p className="text-sm font-semibold text-indigo-800 leading-snug">{weather.alertMessage}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Quick stats row */}
      <div className="grid grid-cols-3 gap-2 px-5 pb-4">
        {[
          { Icon: Droplets,    label: 'Humedad',    value: `${weather.humidityPct}%` },
          { Icon: Wind,        label: 'Viento',     value: `${weather.windKph} km/h` },
          { Icon: Eye,         label: 'Visibilidad',value: `${weather.visibilityKm} km` },
        ].map(({ Icon, label, value }) => (
          <div
            key={label}
            className="flex flex-col items-center text-center rounded-xl py-2.5 px-1"
            style={{ background: 'rgba(255,255,255,0.55)', border: '1px solid rgba(255,255,255,0.8)' }}
          >
            <Icon className="w-4 h-4 text-neutral-500 mb-1" aria-hidden="true" />
            <span className="text-[10px] font-semibold uppercase tracking-wide text-neutral-500">{label}</span>
            <span className="text-sm font-bold text-neutral-800 mt-0.5">{value}</span>
          </div>
        ))}
      </div>

      {/* Hourly forecast strip */}
      <div
        className="px-5 pb-5"
      >
        <p className="text-xs font-bold text-neutral-500 uppercase tracking-wider mb-2">Pronóstico por hora</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {weather.hourly.map((h, i) => (
            <motion.div
              key={h.hour}
              className="flex flex-col items-center gap-1 rounded-xl px-3 py-2.5 shrink-0"
              style={{
                background: 'rgba(255,255,255,0.65)',
                border: '1px solid rgba(255,255,255,0.9)',
                minWidth: 60,
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i + 0.3 }}
            >
              <span className="text-[11px] font-semibold text-neutral-500">{h.hour}</span>
              <ConditionIcon condition={h.condition} size="sm" />
              <span className="text-sm font-bold text-neutral-800">{h.tempC}°</span>
              {h.precipMm > 0 && (
                <span className="text-[10px] font-semibold text-blue-600">{h.precipMm}mm</span>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </motion.section>
  );
}
