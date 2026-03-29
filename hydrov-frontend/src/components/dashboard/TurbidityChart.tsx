import { motion } from 'framer-motion';
import { Waves, AlertTriangle, CheckCircle2, Gauge } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { SensorTurbidity, HistoricalDataPoint } from '@/types/telemetry.types';

interface TurbidityChartProps {
  turbidity: SensorTurbidity;
  history?: HistoricalDataPoint[];
}

const STATUS_CONFIG = {
  clear: {
    label: 'Agua Clara',
    color: '#00d4ff',
    bg: 'bg-neon-blue/10',
    border: 'border-neon-blue/20',
    text: 'text-neon-blue',
    icon: CheckCircle2,
    glow: '0 0 20px rgba(0,212,255,0.3)',
    threshold: '< 1 NTU',
  },
  moderate: {
    label: 'Moderada',
    color: '#fb923c',
    bg: 'bg-orange-400/10',
    border: 'border-orange-400/20',
    text: 'text-orange-400',
    icon: Gauge,
    glow: '0 0 20px rgba(251,146,60,0.3)',
    threshold: '1–4 NTU',
  },
  turbid: {
    label: 'Turbia',
    color: '#fbbf24',
    bg: 'bg-amber-400/10',
    border: 'border-amber-400/20',
    text: 'text-amber-400',
    icon: AlertTriangle,
    glow: '0 0 20px rgba(251,191,36,0.3)',
    threshold: '4–10 NTU',
  },
  critical: {
    label: 'Crítica',
    color: '#ff0040',
    bg: 'bg-neon-red/10',
    border: 'border-neon-red/30',
    text: 'text-neon-red',
    icon: AlertTriangle,
    glow: '0 0 20px rgba(255,0,64,0.4)',
    threshold: '> 10 NTU',
  },
};

// Gauge needle arc for NTU visualization (0–20 NTU range displayed)
const MAX_NTU_DISPLAY = 20;

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="px-3 py-2 rounded-lg bg-dark-700 border border-neon-blue/20 text-xs font-mono">
      <p className="text-slate-400">{label}</p>
      <p className="text-neon-blue font-bold">{payload[0].value.toFixed(2)} NTU</p>
    </div>
  );
}

export function TurbidityChart({ turbidity, history = [] }: TurbidityChartProps) {
  const { ntu, raw_ntu, status } = turbidity;
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;

  // For the radial gauge indicator: 0–20 NTU → 0°–180°
  const clampedNtu = Math.min(ntu, MAX_NTU_DISPLAY);
  const angle = (clampedNtu / MAX_NTU_DISPLAY) * 180 - 90; // -90 to +90

  // Format history for chart
  const chartData = history.slice(-12).map((p) => ({
    time: new Date(p.timestamp).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }),
    ntu: p.value,
  }));

  return (
    <motion.div
      className="glass-card p-5 flex flex-col gap-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
            <Waves className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Monitor de Turbidez</h3>
            <p className="text-[10px] font-mono text-slate-500">ESP32 · Sensor Analógico ADC</p>
          </div>
        </div>
        <motion.div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium ${cfg.bg} ${cfg.border} ${cfg.text}`}
          animate={status === 'critical' ? { opacity: [1, 0.5, 1] } : {}}
          transition={{ duration: 1, repeat: Infinity }}
        >
          <Icon className="w-3 h-3" />
          {cfg.label}
        </motion.div>
      </div>

      {/* Semi-circular gauge */}
      <div className="flex flex-col items-center gap-2">
        <div className="relative w-36 h-[72px] overflow-hidden">
          <svg viewBox="0 0 144 80" className="w-full h-full">
            {/* Background arc */}
            <path
              d="M 12 72 A 60 60 0 0 1 132 72"
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="10"
              strokeLinecap="round"
            />
            {/* Colored progress arc */}
            <motion.path
              d="M 12 72 A 60 60 0 0 1 132 72"
              fill="none"
              stroke={cfg.color}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray="188.5"
              initial={{ strokeDashoffset: 188.5 }}
              animate={{ strokeDashoffset: 188.5 - (clampedNtu / MAX_NTU_DISPLAY) * 188.5 }}
              transition={{ duration: 1, ease: 'easeOut' }}
              style={{ filter: `drop-shadow(0 0 6px ${cfg.color})` }}
            />
            {/* Zone markers */}
            <text x="8" y="78" fill="rgba(255,255,255,0.2)" fontSize="7" fontFamily="monospace">0</text>
            <text x="128" y="78" fill="rgba(255,255,255,0.2)" fontSize="7" fontFamily="monospace">20</text>
          </svg>

          {/* Needle */}
          <motion.div
            className="absolute bottom-0 left-1/2 w-0.5 h-[58px] origin-bottom"
            style={{ transformOrigin: 'center bottom' }}
            animate={{ rotate: angle }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          >
            <div className="w-0.5 h-full bg-gradient-to-t from-white to-transparent rounded-full" />
            <div className="absolute bottom-[-3px] left-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full bg-white/90 border border-white/60" />
          </motion.div>
        </div>

        {/* NTU readout */}
        <div className="text-center">
          <motion.div
            key={Math.round(ntu * 10)}
            className={`text-3xl font-black font-mono ${cfg.text}`}
            style={{ textShadow: `0 0 15px ${cfg.color}60` }}
            initial={{ scale: 1.1 }}
            animate={{ scale: 1 }}
          >
            {ntu.toFixed(2)}
            <span className="text-sm font-normal text-slate-400 ml-1">NTU</span>
          </motion.div>
          <p className="text-[10px] font-mono text-slate-500">
            ADC Raw: {raw_ntu} · Rango {cfg.threshold}
          </p>
        </div>
      </div>

      {/* Mini area chart (12h history) */}
      {chartData.length > 0 && (
        <div className="h-24">
          <p className="text-[10px] font-mono text-slate-600 uppercase tracking-widest mb-1">Últimas 12h</p>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="turbGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={cfg.color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={cfg.color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#475569', fontFamily: 'monospace' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 9, fill: '#475569', fontFamily: 'monospace' }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="ntu" stroke={cfg.color} strokeWidth={1.5} fill="url(#turbGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.div>
  );
}
