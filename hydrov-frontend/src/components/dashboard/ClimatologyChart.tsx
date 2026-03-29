import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  ComposedChart, Bar, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import { Thermometer, Droplets, RefreshCw, Lightbulb, TrendingUp } from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────────
interface ClimatologyPoint {
  day: string;
  date: string;
  liters: number;    // Water consumption
  tempC: number;     // Temperature °C (NASA POWER T2M parameter)
}

interface NasaApiResponse {
  data: ClimatologyPoint[];
  source: 'api' | 'mock';
}

// ─── NASA POWER API stub ───────────────────────────────────────────────────────
// Parameter: T2M (Temperature at 2 Meters)
// Community:  RE (Renewable Energy)
// Docs: https://power.larc.nasa.gov/docs/services/api/
//
// To activate: remove the mock block and un-comment the fetch call below.
async function fetchNasaPowerData(lat: number, lon: number): Promise<NasaApiResponse> {
  // ── 🛰 API Integration Point ───────────────────────────────────────────────
  // const end   = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  // const start = new Date(Date.now() - 6 * 86400_000).toISOString().slice(0, 10).replace(/-/g, '');
  //
  // const url = [
  //   `https://power.larc.nasa.gov/api/temporal/daily/point`,
  //   `?parameters=T2M`,
  //   `&community=RE`,
  //   `&longitude=${lon}`,
  //   `&latitude=${lat}`,
  //   `&start=${start}`,
  //   `&end=${end}`,
  //   `&format=JSON`,
  // ].join('');
  //
  // const res  = await fetch(url);
  // const json = await res.json();
  // const temps = json.properties.parameter.T2M;
  // return {
  //   source: 'api',
  //   data: Object.entries(temps).map(([dateStr, t], i) => ({
  //     day:    ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'][i] ?? dateStr,
  //     date:   `${dateStr.slice(6,8)} ${['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic')[parseInt(dateStr.slice(4,6)) - 1]} `,
  //     liters: Math.round(175 + (t as number - 18) * 6.5 + Math.random() * 20),
  //     tempC:  Number((t as number).toFixed(1)),
  //   })),
  // };
  // ────────────────────────────────────────────────────────────────────────────

  void lat; void lon; // suppress unused-var warning until API is hooked up
  await new Promise((r) => setTimeout(r, 280)); // simulate network

  // Mock data showing a clear positive correlation: more heat → more water consumption
  const data: ClimatologyPoint[] = [
    { day: 'Lun', date: '24 Mar', liters: 195, tempC: 22.1 },
    { day: 'Mar', date: '25 Mar', liters: 218, tempC: 24.4 },
    { day: 'Mié', date: '26 Mar', liters: 247, tempC: 26.8 },
    { day: 'Jue', date: '27 Mar', liters: 271, tempC: 28.9 },
    { day: 'Vie', date: '28 Mar', liters: 298, tempC: 30.5 },
    { day: 'Sáb', date: '29 Mar', liters: 315, tempC: 32.3 },
    { day: 'Dom', date: '30 Mar', liters: 178, tempC: 20.6 },
  ];

  return { source: 'mock', data };
}

// ─── Custom tooltip ────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.95)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(186,230,253,0.7)',
        borderRadius: '1rem',
        boxShadow: '0 8px 32px rgba(14,141,230,0.15)',
        padding: '0.875rem 1.125rem',
        minWidth: 160,
      }}
    >
      <p
        className="text-xs font-bold uppercase tracking-widest mb-2"
        style={{ color: '#64748b' }}
      >
        {label}
      </p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center justify-between gap-4 text-sm">
          <span className="flex items-center gap-1.5 font-medium" style={{ color: '#475569' }}>
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: p.color }} />
            {p.name}
          </span>
          <span className="font-black" style={{ color: p.color }}>
            {p.name === 'Temperatura' ? `${p.value}°C` : `${p.value} L`}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────
const NEZA_LAT = 19.4017;
const NEZA_LON = -99.0153;

interface ClimatologyChartProps {
  delay?: number;
}

export function ClimatologyChart({ delay = 0 }: ClimatologyChartProps) {
  const [data, setData]       = useState<ClimatologyPoint[]>([]);
  const [source, setSource]   = useState<'api' | 'mock'>('mock');
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchNasaPowerData(NEZA_LAT, NEZA_LON);
      setData(result.data);
      setSource(result.source);
    } catch {
      setError('No se pudieron cargar los datos climáticos.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Compute insight: consumption increase % on hot days (tempC > 28)
  const hotDays  = data.filter((d) => d.tempC > 28);
  const coldDays = data.filter((d) => d.tempC <= 28);
  const hotAvg   = hotDays.length  ? hotDays.reduce((s, d) => s + d.liters, 0)  / hotDays.length  : 0;
  const coldAvg  = coldDays.length ? coldDays.reduce((s, d) => s + d.liters, 0) / coldDays.length : 0;
  const increasePercent = coldAvg > 0 ? Math.round(((hotAvg - coldAvg) / coldAvg) * 100) : 0;

  return (
    <motion.div
      className="overflow-hidden rounded-2xl"
      style={{
        background: 'linear-gradient(160deg, rgba(255,255,255,1) 0%, rgba(239,248,255,0.6) 100%)',
        border: '1px solid rgba(186,230,253,0.6)',
        boxShadow: '0 4px 24px rgba(14,141,230,0.07)',
      }}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay }}
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-3 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <Thermometer className="w-5 h-5" style={{ color: '#ef4444' }} aria-hidden="true" />
            <h3 className="text-lg font-bold text-neutral-900">Correlación Temperatura · Consumo</h3>
          </div>
          <div className="flex items-center gap-2">
            <p className="text-sm text-neutral-500">Datos climáticos NASA POWER · Neza, Edo. Méx.</p>
            {source === 'mock' && (
              <span
                className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                style={{ background: '#fffbeb', color: '#92400e', border: '1px solid #fde68a' }}
              >
                DEMO
              </span>
            )}
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          title="Actualizar datos"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: '0.5rem', minHeight: 36 }}
          aria-label="Actualizar datos nasa"
        >
          <motion.div animate={loading ? { rotate: 360 } : { rotate: 0 }} transition={loading ? { duration: 1, repeat: Infinity, ease: 'linear' } : {}}>
            <RefreshCw className="w-4 h-4" />
          </motion.div>
        </button>
      </div>

      {/* Chart */}
      <div style={{ height: 280, paddingLeft: 4, paddingRight: 12, paddingBottom: 8 }}>
        {error ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-neutral-400">{error}</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 16, left: -14, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(203,213,225,0.4)" vertical={false} />

              {/* X axis */}
              <XAxis
                dataKey="day"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#64748b', fontSize: 12, fontWeight: 600, fontFamily: 'Inter' }}
              />

              {/* Left Y: liters */}
              <YAxis
                yAxisId="liters"
                orientation="left"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'Inter' }}
                tickFormatter={(v) => `${v}L`}
                domain={[0, 380]}
              />

              {/* Right Y: temperature */}
              <YAxis
                yAxisId="temp"
                orientation="right"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#fca5a5', fontSize: 11, fontFamily: 'Inter' }}
                tickFormatter={(v) => `${v}°`}
                domain={[15, 38]}
              />

              <Tooltip content={<ChartTooltip />} />

              <Legend
                wrapperStyle={{ paddingTop: 12, fontSize: 12, fontFamily: 'Inter', color: '#64748b' }}
                formatter={(value) => <span style={{ color: '#64748b', fontWeight: 600 }}>{value}</span>}
              />

              {/* Bar — water consumption */}
              <Bar
                yAxisId="liters"
                dataKey="liters"
                name="Consumo"
                fill="url(#consumoGrad)"
                radius={[8, 8, 0, 0]}
                barSize={30}
              />

              {/* Line — temperature */}
              <Line
                yAxisId="temp"
                dataKey="tempC"
                name="Temperatura"
                stroke="#f87171"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#f87171', strokeWidth: 2, stroke: 'white' }}
                activeDot={{ r: 6, fill: '#ef4444', strokeWidth: 0 }}
                type="monotone"
              />

              {/* Gradient def */}
              <defs>
                <linearGradient id="consumoGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#38bdf8" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#0e8de6" stopOpacity="0.8" />
                </linearGradient>
              </defs>
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Insight Generator ─────────────────────────────────────────────── */}
      {!loading && !error && increasePercent > 0 && (
        <motion.div
          className="mx-5 mb-5 rounded-2xl p-4"
          style={{
            background: 'linear-gradient(135deg, rgba(239,248,255,0.9) 0%, rgba(207,250,254,0.7) 100%)',
            border: '1px solid rgba(186,230,253,0.7)',
          }}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: delay + 0.6, duration: 0.5 }}
        >
          <div className="flex items-start gap-3">
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
            >
              <Lightbulb className="w-6 h-6 shrink-0 mt-0.5" style={{ color: '#f59e0b' }} aria-hidden="true" />
            </motion.div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <p className="text-sm font-black text-neutral-800">Descubrimiento Hydro-V</p>
                <span
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(239,246,255,0.8)', color: '#1e40af', border: '1px solid #bfdbfe' }}
                >
                  NASA POWER
                </span>
              </div>
              <p className="text-sm text-neutral-700 leading-relaxed">
                💡 Tu consumo aumenta un{' '}
                <strong style={{ color: '#0e8de6' }}>{increasePercent}%</strong> en días con
                temperatura superior a <strong style={{ color: '#ef4444' }}>28°C</strong>.
                Considera almacenar agua extra cuando el pronóstico supere ese umbral.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 mt-3">
            <TrendingUp className="w-4 h-4" style={{ color: '#0e8de6' }} aria-hidden="true" />
            <p className="text-xs font-semibold text-neutral-500">
              Basado en {hotDays.length} días calurosos vs {coldDays.length} días frescos · últimos 7 días
            </p>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
