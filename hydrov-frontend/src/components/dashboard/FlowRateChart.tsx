import { motion } from 'framer-motion';
import { Activity, TrendingUp, Zap } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { SensorFlow, HistoricalDataPoint } from '@/types/telemetry.types';

interface FlowRateChartProps {
  flow: SensorFlow;
  history?: HistoricalDataPoint[];
}

interface TooltipProps {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}

function ChartTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="px-3 py-2 rounded-lg bg-dark-700 border border-neon-cyan/20 text-xs font-mono">
      <p className="text-slate-400">{label}</p>
      <p className="text-neon-cyan font-bold">{payload[0].value.toFixed(2)} L/min</p>
    </div>
  );
}

export function FlowRateChart({ flow, history = [] }: FlowRateChartProps) {
  const { rate_lpm, total_liters } = flow;

  const chartData = history.slice(-16).map((p) => ({
    time: new Date(p.timestamp).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' }),
    flow: p.value,
  }));

  const avgFlow = chartData.length
    ? +(chartData.reduce((s, d) => s + d.flow, 0) / chartData.length).toFixed(2)
    : rate_lpm;

  const isHighFlow = rate_lpm > 2.5;

  return (
    <motion.div
      className="glass-card p-5 flex flex-col gap-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.15 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Flujo de Agua</h3>
            <p className="text-[10px] font-mono text-slate-500">Sensor de Pulsos · YF-S201</p>
          </div>
        </div>
        <div className={`flex items-center gap-1 px-2 py-1 rounded-lg border text-[10px] font-mono ${
          isHighFlow ? 'text-amber-400 bg-amber-400/10 border-amber-400/20' : 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/20'
        }`}>
          <Zap className="w-3 h-3" />
          {isHighFlow ? 'Flujo Alto' : 'Flujo Normal'}
        </div>
      </div>

      {/* Current rate + total */}
      <div className="flex items-center gap-6">
        <div className="text-center">
          <motion.div
            key={Math.round(rate_lpm * 10)}
            className="text-4xl font-black font-mono text-neon-cyan text-glow-cyan"
            initial={{ scale: 1.08 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            {rate_lpm.toFixed(2)}
          </motion.div>
          <p className="text-xs font-mono text-slate-400 mt-0.5">L / minuto</p>
        </div>

        <div className="flex-1 grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-xl bg-dark-600/40 border border-dark-500/30">
            <p className="text-[9px] font-mono text-slate-500 uppercase">Promedio 16h</p>
            <p className="text-sm font-bold font-mono text-white mt-0.5">{avgFlow} <span className="text-xs text-slate-400">L/min</span></p>
          </div>
          <div className="p-2.5 rounded-xl bg-dark-600/40 border border-dark-500/30">
            <p className="text-[9px] font-mono text-slate-500 uppercase">Total Acumulado</p>
            <p className="text-sm font-bold font-mono text-white mt-0.5">{total_liters.toLocaleString()} <span className="text-xs text-slate-400">L</span></p>
          </div>
        </div>
      </div>

      {/* Flow chart */}
      {chartData.length > 0 && (
        <div className="h-28">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
              <defs>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="2" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#475569', fontFamily: 'monospace' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 9, fill: '#475569', fontFamily: 'monospace' }} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine y={avgFlow} stroke="rgba(0,255,245,0.2)" strokeDasharray="4 4" />
              <Line
                type="monotone"
                dataKey="flow"
                stroke="#00fff5"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#00fff5', strokeWidth: 0 }}
                filter="url(#glow)"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.div>
  );
}
