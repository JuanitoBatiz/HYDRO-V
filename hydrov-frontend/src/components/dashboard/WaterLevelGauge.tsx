import { useRef, useEffect, useId } from 'react';
import { motion, useMotionValue, useSpring, animate } from 'framer-motion';
import { Droplets, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import type { SensorLevel } from '@/types/telemetry.types';

interface WaterLevelGaugeProps {
  level: SensorLevel;
}

interface StatusConfig {
  label: string;
  description: string;
  badgeCls: string;
  icon: React.ElementType;
  waveColor1: string;
  waveColor2: string;
  trackColor: string;
  gradient: [string, string]; // [from, to]
}

function getStatus(pct: number): StatusConfig {
  if (pct >= 60) return {
    label: 'Nivel Bueno',
    description: 'Tu cisterna tiene suficiente agua.',
    badgeCls: 'badge-ok',
    icon: CheckCircle,
    waveColor1: 'rgba(14,141,230,0.85)',
    waveColor2: 'rgba(6,182,212,0.7)',
    trackColor: '#0e8de6',
    gradient: ['#38bdf8', '#06b6d4'],
  };
  if (pct >= 30) return {
    label: 'Nivel Medio',
    description: 'Considera usar el agua con más cuidado.',
    badgeCls: 'badge-warning',
    icon: AlertCircle,
    waveColor1: 'rgba(245,158,11,0.8)',
    waveColor2: 'rgba(251,146,60,0.65)',
    trackColor: '#f59e0b',
    gradient: ['#fbbf24', '#fb923c'],
  };
  return {
    label: '¡Nivel Bajo!',
    description: 'El agua de tu cisterna se está agotando.',
    badgeCls: 'badge-danger',
    icon: XCircle,
    waveColor1: 'rgba(244,63,94,0.8)',
    waveColor2: 'rgba(251,113,133,0.65)',
    trackColor: '#f43f5e',
    gradient: ['#fb7185', '#f43f5e'],
  };
}

function useAnimatedCount(target: number) {
  const ref = useRef<HTMLSpanElement>(null);
  const prev = useRef(target);
  useEffect(() => {
    const ctrl = animate(prev.current, target, {
      duration: 1.2,
      ease: 'easeOut',
      onUpdate(v) { if (ref.current) ref.current.textContent = Math.round(v).toString(); },
      onComplete() { prev.current = target; },
    });
    return () => ctrl.stop();
  }, [target]);
  return ref;
}

// ─── Liquid Wave SVG Component ────────────────────────────────────────────────
// Uses a clipPath circle + animated SVG wave path to create a liquid fill effect.
interface LiquidWaveProps {
  percentage: number;
  cfg: StatusConfig;
  uid: string;
}

function LiquidWave({ percentage, cfg, uid }: LiquidWaveProps) {
  const SIZE = 240;        // SVG canvas size
  const R = 100;           // Circle radius
  const CX = SIZE / 2;     // Center X
  const CY = SIZE / 2;     // Center Y

  // "fillY": top of water. 0% = full (top), 100% = empty (bottom of circle)
  // Water fills from bottom. At pct=0 water top is at circle bottom.
  // At pct=100 water top is at circle top.
  const fillY = CY + R - (percentage / 100) * (2 * R);

  // clamp so wave stays inside circle bounds visually
  const clampedFillY = Math.max(CY - R + 4, Math.min(CY + R - 4, fillY));

  // Spring-animate the water surface Y position
  const waveY = useMotionValue(CY + R); // start empty
  const springY = useSpring(waveY, { stiffness: 60, damping: 18 });

  useEffect(() => {
    waveY.set(clampedFillY);
  }, [clampedFillY, waveY]);

  // Wave path: wide sinusoidal curve drawn across full width + bottom rectangle
  // The wave oscillates on the X-axis using Framer Motion animate
  const waveWidth = SIZE * 2;

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="w-full h-full"
      aria-hidden="true"
    >
      <defs>
        {/* Circular clip region */}
        <clipPath id={`clip-${uid}`}>
          <circle cx={CX} cy={CY} r={R - 2} />
        </clipPath>

        {/* Gradient for water body */}
        <linearGradient id={`wg-${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={cfg.gradient[0]} stopOpacity="0.9" />
          <stop offset="100%" stopColor={cfg.gradient[1]} stopOpacity="1" />
        </linearGradient>

        {/* Gradient for the outer ring */}
        <linearGradient id={`ring-${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={cfg.gradient[0]} />
          <stop offset="100%" stopColor={cfg.gradient[1]} />
        </linearGradient>

        {/* Soft inner shadow using filter */}
        <filter id={`shadow-${uid}`} x="-10%" y="-10%" width="120%" height="120%">
          <feDropShadow dx="0" dy="4" stdDeviation="8" floodColor={cfg.gradient[1]} floodOpacity="0.3" />
        </filter>
      </defs>

      {/* Base circle background */}
      <circle cx={CX} cy={CY} r={R} fill="#f1f5f9" />

      {/* Colored ring (border) */}
      <circle
        cx={CX} cy={CY} r={R}
        fill="none"
        stroke={`url(#ring-${uid})`}
        strokeWidth="5"
        opacity="0.4"
      />

      {/* Clipped water body + animated wave */}
      <g clipPath={`url(#clip-${uid})`}>
        {/* Solid water fill underneath the wave */}
        <motion.rect
          x={0}
          y={0}
          width={SIZE}
          height={SIZE}
          fill={`url(#wg-${uid})`}
          style={{
            y: springY,
            height: SIZE,
          }}
        />

        {/* Wave layer 1 (front) — oscillates left-right */}
        <motion.g style={{ y: springY }}>
          <motion.path
            fill={cfg.waveColor1}
            animate={{
              d: [
                `M -${waveWidth} -16 
                 Q ${-waveWidth * 0.75} 16, ${-waveWidth * 0.5} 0 
                 T 0 -16 T ${waveWidth * 0.5} -16 T ${waveWidth} -16
                 L ${waveWidth} ${SIZE} L -${waveWidth} ${SIZE} Z`,

                `M -${waveWidth} 16 
                 Q ${-waveWidth * 0.75} -16, ${-waveWidth * 0.5} 0 
                 T 0 16 T ${waveWidth * 0.5} 16 T ${waveWidth} 16
                 L ${waveWidth} ${SIZE} L -${waveWidth} ${SIZE} Z`,

                `M -${waveWidth} -16 
                 Q ${-waveWidth * 0.75} 16, ${-waveWidth * 0.5} 0 
                 T 0 -16 T ${waveWidth * 0.5} -16 T ${waveWidth} -16
                 L ${waveWidth} ${SIZE} L -${waveWidth} ${SIZE} Z`,
              ],
            }}
            transition={{
              duration: 3.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        </motion.g>

        {/* Wave layer 2 (back, slower, offset phase) */}
        <motion.g style={{ y: springY }}>
          <motion.path
            fill={cfg.waveColor2}
            animate={{
              d: [
                `M -${waveWidth} 14 
                 Q ${-waveWidth * 0.75} -14, ${-waveWidth * 0.5} 0 
                 T 0 14 T ${waveWidth * 0.5} 14 T ${waveWidth} 14
                 L ${waveWidth} ${SIZE} L -${waveWidth} ${SIZE} Z`,

                `M -${waveWidth} -14 
                 Q ${-waveWidth * 0.75} 14, ${-waveWidth * 0.5} 0 
                 T 0 -14 T ${waveWidth * 0.5} -14 T ${waveWidth} -14
                 L ${waveWidth} ${SIZE} L -${waveWidth} ${SIZE} Z`,

                `M -${waveWidth} 14 
                 Q ${-waveWidth * 0.75} -14, ${-waveWidth * 0.5} 0 
                 T 0 14 T ${waveWidth * 0.5} 14 T ${waveWidth} 14
                 L ${waveWidth} ${SIZE} L -${waveWidth} ${SIZE} Z`,
              ],
            }}
            transition={{
              duration: 4.8,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: 0.6,
            }}
          />
        </motion.g>
      </g>

      {/* Outer progress ring — renders on top of water */}
      <circle cx={CX} cy={CY} r={R} fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="5" />
      {/* Glow ring around circle */}
      <circle
        cx={CX} cy={CY} r={R + 2}
        fill="none"
        stroke={cfg.gradient[0]}
        strokeWidth="2"
        opacity="0.25"
      />
    </svg>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────
export function WaterLevelGauge({ level }: WaterLevelGaugeProps) {
  const { percentage, liters, tank_capacity_liters } = level;
  const cfg = getStatus(percentage);
  const Icon = cfg.icon;
  const uid = useId().replace(/:/g, '');

  const litersRef = useAnimatedCount(Math.round(liters));
  const pctRef    = useAnimatedCount(Math.round(percentage));

  return (
    <motion.section
      aria-label="Nivel de agua de la cisterna"
      className="overflow-hidden rounded-2xl text-center"
      style={{
        background: `linear-gradient(160deg, 
          rgba(239,248,255,1) 0%, 
          rgba(224,242,254,0.9) 40%, 
          rgba(207,250,254,0.8) 100%)`,
        border: '1px solid rgba(186,230,253,0.7)',
        boxShadow: '0 4px 24px rgba(14,141,230,0.08), 0 1px 4px rgba(14,141,230,0.06)',
      }}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Card header — gradient top stripe */}
      <div
        className="px-6 pt-6 pb-2"
        style={{
          background: `linear-gradient(135deg, rgba(14,141,230,0.08) 0%, rgba(6,182,212,0.06) 100%)`,
        }}
      >
        <div className="flex items-center justify-center gap-2 mb-0.5">
          <Droplets className="w-5 h-5" style={{ color: cfg.trackColor }} aria-hidden="true" />
          <h2 className="text-lg font-bold text-neutral-800">Tu Cisterna</h2>
        </div>
        <p className="text-sm text-neutral-500">HYDRO-V-001 · Almacenamiento Principal</p>
      </div>

      {/* ── Liquid Wave Gauge ───────────────────────────────────── */}
      <div className="relative flex items-center justify-center py-4 px-6">
        {/* Circular wave container */}
        <div
          className="relative"
          style={{ width: 220, height: 220 }}
        >
          <LiquidWave percentage={percentage} cfg={cfg} uid={uid} />

          {/* Centered text overlay */}
          <div
            className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
            style={{ mixBlendMode: 'normal' }}
          >
            {/* Percentage */}
            <motion.div
              className="flex flex-col items-center"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5, ease: 'backOut' }}
            >
              <span
                className="text-6xl font-black leading-none tabular-nums"
                style={{
                  color: percentage > 45 ? 'white' : '#0f172a',
                  textShadow: percentage > 45 ? '0 2px 8px rgba(0,0,0,0.25)' : 'none',
                }}
              >
                <span ref={pctRef}>{Math.round(percentage)}</span>
                <span className="text-3xl font-semibold" style={{ opacity: 0.8 }}>%</span>
              </span>
              <span
                className="text-sm font-semibold mt-0.5"
                style={{
                  color: percentage > 45 ? 'rgba(255,255,255,0.85)' : '#64748b',
                }}
              >
                de capacidad
              </span>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Status badge */}
      <div className="flex justify-center pb-4">
        <motion.span
          className={cfg.badgeCls}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <Icon className="w-4 h-4" aria-hidden="true" />
          {cfg.label}
        </motion.span>
      </div>

      {/* Description */}
      <p className="text-base text-neutral-600 px-6 pb-5 leading-relaxed">{cfg.description}</p>

      {/* Key numbers */}
      <div
        className="grid grid-cols-2 gap-3 px-6 pb-5"
      >
        <div
          className="rounded-2xl p-4 text-left"
          style={{ background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(186,230,253,0.5)' }}
        >
          <p className="section-label mb-1">Tienes ahora</p>
          <p className="text-3xl font-black text-neutral-900 tabular-nums">
            <span ref={litersRef}>{Math.round(liters)}</span>
            <span className="text-base font-semibold text-neutral-400 ml-1">L</span>
          </p>
        </div>
        <div
          className="rounded-2xl p-4 text-left"
          style={{ background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(186,230,253,0.5)' }}
        >
          <p className="section-label mb-1">Capacidad total</p>
          <p className="text-3xl font-black text-neutral-900 tabular-nums">
            {tank_capacity_liters.toLocaleString('es-MX')}
            <span className="text-base font-semibold text-neutral-400 ml-1">L</span>
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div
        className="px-6 pb-6"
        aria-label={`Nivel: ${Math.round(percentage)} por ciento`}
      >
        <div className="flex justify-between text-sm text-neutral-500 mb-1.5">
          <span>0 L</span>
          <span>{tank_capacity_liters.toLocaleString('es-MX')} L</span>
        </div>
        <div
          className="h-3 rounded-full overflow-hidden"
          style={{ background: 'rgba(203,213,225,0.6)' }}
          role="progressbar"
          aria-valuenow={Math.round(percentage)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <motion.div
            className="h-full rounded-full"
            style={{
              background: `linear-gradient(90deg, ${cfg.gradient[0]}, ${cfg.gradient[1]})`,
            }}
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 1.4, ease: 'easeOut', delay: 0.2 }}
          />
        </div>
      </div>
    </motion.section>
  );
}
