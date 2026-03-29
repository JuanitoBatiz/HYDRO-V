import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Activity, TrendingUp, TrendingDown, AlertTriangle,
  BarChart3, Minus, Brain,
} from 'lucide-react';

import { LocationWidget }   from '@/components/dashboard/LocationWidget';
import { ClimatologyChart } from '@/components/dashboard/ClimatologyChart';

// ─── Weekly dataset (same as HistoryView — in production, share via context) ──
const WEEKLY_DATA = [
  { day: 'Lun', liters: 210 },
  { day: 'Mar', liters: 185 },
  { day: 'Mié', liters: 230 },
  { day: 'Jue', liters: 195 },
  { day: 'Vie', liters: 270 },
  { day: 'Sáb', liters: 310 },
  { day: 'Hoy', liters: 178 },
];

// ─── Statistical helpers ───────────────────────────────────────────────────────
function mean(arr: number[]) {
  return arr.reduce((s, v) => s + v, 0) / arr.length;
}

function stdDev(arr: number[]) {
  const mu = mean(arr);
  return Math.sqrt(arr.reduce((s, v) => s + (v - mu) ** 2, 0) / arr.length);
}

/** Ordinary Least Squares slope — consumption trend (litres/day) */
function olsSlope(arr: number[]) {
  const n  = arr.length;
  const xs = arr.map((_, i) => i);
  const mu = mean(arr);
  const mx = mean(xs);
  const num = xs.reduce((s, x, i) => s + (x - mx) * (arr[i] - mu), 0);
  const den = xs.reduce((s, x)    => s + (x - mx) ** 2, 0);
  return den === 0 ? 0 : num / den;
}

// ─── Stagger variants ─────────────────────────────────────────────────────────
const containerVariants = {
  hidden: {},
  show:   { transition: { staggerChildren: 0.1, delayChildren: 0.04 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 22 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

// ─── Smart Card ───────────────────────────────────────────────────────────────
interface SmartCardProps {
  symbol: string;
  symbolLabel: string;
  title: string;
  value: string;
  unit: string;
  subtitle: string;
  Icon: React.ElementType;
  accentColor: string;
  gradBg: string;
  borderColor: string;
  alert?: { message: string; color: string; bg: string; border: string };
}

function SmartCard({
  symbol, symbolLabel, title, value, unit, subtitle,
  Icon, accentColor, gradBg, borderColor, alert,
}: SmartCardProps) {
  return (
    <motion.div
      variants={itemVariants}
      className="overflow-hidden rounded-2xl"
      style={{
        background: gradBg,
        border: `1px solid ${borderColor}`,
        boxShadow: '0 4px 16px rgba(0,0,0,0.05)',
      }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between px-5 pt-5 pb-3">
        <div className="flex items-center gap-2.5">
          <div
            className="flex items-center justify-center w-10 h-10 rounded-xl shrink-0"
            style={{ background: `${accentColor}18`, border: `1px solid ${accentColor}30` }}
          >
            <Icon className="w-5 h-5" style={{ color: accentColor }} aria-hidden="true" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-widest" style={{ color: accentColor }}>
              {title}
            </p>
            <p className="text-[10px] text-neutral-400 font-medium">{subtitle}</p>
          </div>
        </div>

        {/* Math symbol badge */}
        <div
          className="flex flex-col items-center justify-center w-11 h-11 rounded-xl shrink-0"
          style={{
            background: `${accentColor}12`,
            border: `1px solid ${accentColor}25`,
          }}
          title={symbolLabel}
        >
          <span
            className="text-lg font-black leading-none"
            style={{ color: accentColor, fontFamily: 'Georgia, serif' }}
          >
            {symbol}
          </span>
          <span className="text-[9px] text-neutral-400 font-semibold">{symbolLabel}</span>
        </div>
      </div>

      {/* Value */}
      <div className="px-5 pb-4">
        <motion.p
          className="text-5xl font-black tabular-nums leading-none"
          style={{ color: '#0f172a' }}
          initial={{ opacity: 0, scale: 0.88 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, type: 'spring', stiffness: 240, damping: 22 }}
        >
          {value}
          <span className="text-xl font-semibold text-neutral-400 ml-1.5">{unit}</span>
        </motion.p>
      </div>

      {/* Alert strip */}
      {alert && (
        <motion.div
          className="mx-4 mb-4 rounded-xl px-3.5 py-2.5"
          style={{ background: alert.bg, border: `1px solid ${alert.border}` }}
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          transition={{ delay: 0.35 }}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" style={{ color: alert.color }} aria-hidden="true" />
            <p className="text-sm font-semibold" style={{ color: alert.color }}>
              {alert.message}
            </p>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}

// ─── Main View ────────────────────────────────────────────────────────────────
export function AnalyticsView() {
  const litersArr = WEEKLY_DATA.map((d) => d.liters);

  const mu    = useMemo(() => mean(litersArr),    []);   // Mean
  const sigma = useMemo(() => stdDev(litersArr),  []);   // Std deviation
  const slope = useMemo(() => olsSlope(litersArr), []);  // OLS trend slope

  const todayLiters = WEEKLY_DATA[WEEKLY_DATA.length - 1].liters;
  const isAbnormal  = todayLiters > mu + 1.5 * sigma;

  const trendDirection = slope > 2 ? 'up' : slope < -2 ? 'down' : 'flat';
  const TrendIcon      = trendDirection === 'up'   ? TrendingUp
                       : trendDirection === 'down' ? TrendingDown
                       : Minus;
  const trendColor     = trendDirection === 'up'   ? '#f59e0b'
                       : trendDirection === 'down' ? '#22c55e'
                       : '#64748b';

  const smartCards: SmartCardProps[] = [
    {
      symbol:      'μ',
      symbolLabel: 'Media',
      title:       'Promedio Diario',
      subtitle:    'Consumo medio · últimos 7 días',
      value:       mu.toFixed(0),
      unit:        'L/día',
      Icon:        Activity,
      accentColor: '#0e8de6',
      gradBg:      'linear-gradient(160deg, rgba(239,248,255,1) 0%, rgba(224,242,254,0.8) 100%)',
      borderColor: 'rgba(186,230,253,0.7)',
    },
    {
      symbol:      'σ',
      symbolLabel: 'Desv. Std.',
      title:       'Volatilidad de Consumo',
      subtitle:    'Desviación estándar poblacional',
      value:       sigma.toFixed(1),
      unit:        'L',
      Icon:        BarChart3,
      accentColor: '#6366f1',
      gradBg:      'linear-gradient(160deg, rgba(245,243,255,1) 0%, rgba(237,233,254,0.8) 100%)',
      borderColor: 'rgba(196,181,253,0.6)',
      ...(isAbnormal ? {
        alert: {
          message: `Consumo hoy (${todayLiters}L) supera μ+1.5σ — patrón anormal`,
          color:   '#c2410c',
          bg:      'rgba(255,237,213,0.9)',
          border:  'rgba(254,215,170,0.8)',
        },
      } : {}),
    },
    {
      symbol:      'm',
      symbolLabel: 'Tendencia',
      title:       'Tendencia Semanal',
      subtitle:    'Pendiente OLS · L/día por día',
      value:       `${slope > 0 ? '+' : ''}${slope.toFixed(1)}`,
      unit:        'L/d²',
      Icon:        TrendIcon,
      accentColor: trendColor,
      gradBg:      trendDirection === 'up'
        ? 'linear-gradient(160deg, rgba(255,251,235,1) 0%, rgba(254,243,199,0.8) 100%)'
        : trendDirection === 'down'
          ? 'linear-gradient(160deg, rgba(240,253,244,1) 0%, rgba(220,252,231,0.8) 100%)'
          : 'linear-gradient(160deg, rgba(248,250,252,1) 0%, rgba(241,245,249,0.8) 100%)',
      borderColor: trendDirection === 'up'
        ? 'rgba(253,230,138,0.7)'
        : trendDirection === 'down'
          ? 'rgba(187,247,208,0.7)'
          : 'rgba(203,213,225,0.7)',
    },
  ];

  return (
    <motion.div
      className="max-w-3xl mx-auto px-4 md:px-6 py-6 space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* ── Page header ─────────────────────────────────────────────────── */}
      <motion.div variants={itemVariants}>
        <div className="flex items-center gap-3 mb-1">
          <div
            className="flex items-center justify-center w-10 h-10 rounded-xl shrink-0"
            style={{ background: 'linear-gradient(135deg, #0e8de6, #6366f1)', boxShadow: '0 2px 8px rgba(14,141,230,0.3)' }}
          >
            <Brain className="w-5 h-5 text-white" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-neutral-900">Inteligencia Hídrica</h2>
            <p className="text-sm text-neutral-500">Análisis estadístico · Correlación climática · Geolocalización</p>
          </div>
        </div>
      </motion.div>

      {/* ── Smart Cards (μ σ m) ──────────────────────────────────────────── */}
      <motion.div
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
        variants={containerVariants}
      >
        {smartCards.map((card) => (
          <SmartCard key={card.symbol} {...card} />
        ))}
      </motion.div>

      {/* ── Climatology chart ───────────────────────────────────────────── */}
      <motion.div variants={itemVariants}>
        <ClimatologyChart delay={0.1} />
      </motion.div>

      {/* ── Location widget ─────────────────────────────────────────────── */}
      <motion.div variants={itemVariants}>
        <LocationWidget isConnected={true} />
      </motion.div>

      {/* ── Stats methodology note ─────────────────────────────────────── */}
      <motion.div
        variants={itemVariants}
        className="rounded-2xl px-5 py-4"
        style={{
          background: 'rgba(255,255,255,0.7)',
          border: '1px solid rgba(226,232,240,0.7)',
        }}
      >
        <p className="text-xs font-bold uppercase tracking-widest text-neutral-400 mb-2">
          📐 Metodología estadística
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm text-neutral-600">
          <div>
            <span className="font-black" style={{ fontFamily: 'Georgia, serif', marginRight: 4 }}>μ</span>
            Media aritmética de consumo de los últimos 7 días
          </div>
          <div>
            <span className="font-black" style={{ fontFamily: 'Georgia, serif', marginRight: 4 }}>σ</span>
            Desviación estándar poblacional · umbral de anomalía: μ + 1.5σ
          </div>
          <div>
            <span className="font-black" style={{ fontFamily: 'Georgia, serif', marginRight: 4 }}>m</span>
            Pendiente OLS (mínimos cuadrados ordinarios) de la serie temporal
          </div>
        </div>
      </motion.div>

      <div className="h-4 pb-safe" />
    </motion.div>
  );
}
