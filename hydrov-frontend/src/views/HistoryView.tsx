import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { BarChart3, Droplets, TrendingDown, TrendingUp, Calendar } from 'lucide-react';

// ─── Mock data: last 7 days ────────────────────────────────────────────────────
// Replace with API call to InfluxDB / backend
const DAILY_DATA = [
  { day: 'Lun', liters: 210, date: '24 Mar' },
  { day: 'Mar', liters: 185, date: '25 Mar' },
  { day: 'Mié', liters: 230, date: '26 Mar' },
  { day: 'Jue', liters: 195, date: '27 Mar' },
  { day: 'Vie', liters: 270, date: '28 Mar' },
  { day: 'Sáb', liters: 310, date: '29 Mar' },
  { day: 'Hoy', liters: 178, date: '30 Mar' },
];

const WEEKLY_TOTAL = DAILY_DATA.reduce((sum, d) => sum + d.liters, 0);
const WEEKLY_AVG   = Math.round(WEEKLY_TOTAL / DAILY_DATA.length);
const MAX_DAY      = DAILY_DATA.reduce((max, d) => d.liters > max.liters ? d : max, DAILY_DATA[0]);
const MIN_DAY      = DAILY_DATA.reduce((min, d) => d.liters < min.liters ? d : min, DAILY_DATA[0]);

// Custom tooltip
function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-xl px-4 py-3 text-sm font-semibold"
      style={{
        background: 'white',
        border: '1px solid rgba(186,230,253,0.7)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
        color: '#0f172a',
      }}
    >
      <p className="text-xs text-neutral-500 mb-0.5">{label}</p>
      <p className="text-xl font-black" style={{ color: '#0e8de6' }}>
        {payload[0].value} <span className="text-sm font-semibold text-neutral-400">L</span>
      </p>
    </div>
  );
}

const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
};

export function HistoryView() {
  return (
    <motion.div
      className="max-w-2xl mx-auto px-4 md:px-6 py-6 space-y-5"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* Page header */}
      <motion.div variants={itemVariants}>
        <div className="flex items-center gap-2.5 mb-1">
          <BarChart3 className="w-6 h-6" style={{ color: '#0e8de6' }} aria-hidden="true" />
          <h2 className="text-2xl font-bold text-neutral-900">Historial de Consumo</h2>
        </div>
        <p className="text-base text-neutral-500">Últimos 7 días · Cisterna HYDRO-V-NEZA-001</p>
      </motion.div>

      {/* Summary cards */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 gap-3">
        {[
          {
            Icon: Droplets,
            label: 'Total semanal',
            value: WEEKLY_TOTAL.toLocaleString('es-MX'),
            unit: 'L',
            color: '#0e8de6',
            bg: 'rgba(239,248,255,0.9)',
            border: 'rgba(186,230,253,0.6)',
          },
          {
            Icon: Calendar,
            label: 'Promedio diario',
            value: WEEKLY_AVG.toString(),
            unit: 'L/día',
            color: '#06b6d4',
            bg: 'rgba(236,254,255,0.9)',
            border: 'rgba(165,243,252,0.6)',
          },
          {
            Icon: TrendingUp,
            label: 'Día de mayor uso',
            value: `${MAX_DAY.liters} L`,
            unit: MAX_DAY.day,
            color: '#f59e0b',
            bg: 'rgba(255,251,235,0.9)',
            border: 'rgba(253,230,138,0.6)',
          },
          {
            Icon: TrendingDown,
            label: 'Día de menor uso',
            value: `${MIN_DAY.liters} L`,
            unit: MIN_DAY.day,
            color: '#22c55e',
            bg: 'rgba(240,253,244,0.9)',
            border: 'rgba(187,247,208,0.6)',
          },
        ].map(({ Icon, label, value, unit, color, bg, border }) => (
          <div
            key={label}
            className="rounded-2xl p-4"
            style={{ background: bg, border: `1px solid ${border}` }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <Icon className="w-4 h-4 shrink-0" style={{ color }} aria-hidden="true" />
              <p className="section-label">{label}</p>
            </div>
            <p className="text-2xl font-black text-neutral-900 tabular-nums leading-tight">{value}</p>
            <p className="text-sm text-neutral-500 mt-0.5">{unit}</p>
          </div>
        ))}
      </motion.div>

      {/* Bar chart card */}
      <motion.div
        variants={itemVariants}
        className="rounded-2xl overflow-hidden"
        style={{
          background: 'linear-gradient(160deg, rgba(239,248,255,1) 0%, rgba(255,255,255,0.95) 100%)',
          border: '1px solid rgba(186,230,253,0.6)',
          boxShadow: '0 4px 20px rgba(14,141,230,0.07)',
        }}
      >
        <div className="px-5 pt-5 pb-2">
          <h3 className="text-lg font-bold text-neutral-800">Consumo diario</h3>
          <p className="text-sm text-neutral-500">Litros utilizados por día</p>
        </div>

        <div className="px-3 pb-5" style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={DAILY_DATA} barSize={28} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(203,213,225,0.5)" vertical={false} />
              <XAxis
                dataKey="day"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#64748b', fontSize: 13, fontWeight: 600, fontFamily: 'Inter' }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#94a3b8', fontSize: 12, fontFamily: 'Inter' }}
                tickFormatter={(v) => `${v}L`}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(14,141,230,0.06)', radius: 8 }} />
              <Bar dataKey="liters" radius={[10, 10, 0, 0]}>
                {DAILY_DATA.map((entry, i) => {
                  const isMax   = entry.liters === MAX_DAY.liters;
                  const isToday = entry.day === 'Hoy';
                  const color   = isMax ? '#f59e0b' : isToday ? '#0e8de6' : '#38bdf8';
                  return (
                    <Cell
                      key={`bar-${i}`}
                      fill={color}
                      opacity={isToday || isMax ? 1 : 0.75}
                    />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className="px-5 pb-5 flex flex-wrap gap-4 text-sm text-neutral-500">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full" style={{ background: '#0e8de6' }} aria-hidden="true" />
            Hoy
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full" style={{ background: '#f59e0b' }} aria-hidden="true" />
            Mayor consumo
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full" style={{ background: '#38bdf8' }} aria-hidden="true" />
            Días normales
          </span>
        </div>
      </motion.div>

      {/* Daily breakdown list */}
      <motion.div
        variants={itemVariants}
        className="rounded-2xl overflow-hidden"
        style={{ background: 'white', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}
      >
        <div className="px-5 pt-4 pb-2">
          <h3 className="text-base font-bold text-neutral-800">Detalle por día</h3>
        </div>
        <ul>
          {[...DAILY_DATA].reverse().map((d, i) => {
            const pct = Math.round((d.liters / MAX_DAY.liters) * 100);
            return (
              <li
                key={d.day}
                className="flex items-center gap-4 px-5 py-3"
                style={{ borderTop: i > 0 ? '1px solid rgba(241,245,249,1)' : 'none' }}
              >
                <div className="w-10 text-center">
                  <p className="text-sm font-bold text-neutral-700">{d.day}</p>
                  <p className="text-xs text-neutral-400">{d.date}</p>
                </div>
                <div className="flex-1">
                  <div className="h-2.5 rounded-full overflow-hidden" style={{ background: '#f1f5f9' }}>
                    <motion.div
                      className="h-full rounded-full"
                      style={{ background: 'linear-gradient(90deg, #38bdf8, #0e8de6)' }}
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.8, delay: i * 0.05, ease: 'easeOut' }}
                    />
                  </div>
                </div>
                <p className="text-base font-bold text-neutral-900 tabular-nums w-16 text-right">
                  {d.liters} <span className="text-sm font-normal text-neutral-400">L</span>
                </p>
              </li>
            );
          })}
        </ul>
      </motion.div>

      <div className="h-4 pb-safe" />
    </motion.div>
  );
}
