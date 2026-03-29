import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { animate } from 'framer-motion';
import { CalendarDays, TrendingDown, ThumbsUp, AlertTriangle, Clock } from 'lucide-react';
import type { AutonomyPrediction } from '@/types/telemetry.types';

interface AutonomyCardProps {
  autonomy: AutonomyPrediction;
}

function useCountUp(target: number) {
  const ref = useRef<HTMLSpanElement>(null);
  const prev = useRef(target);
  useEffect(() => {
    const ctrl = animate(prev.current, target, {
      duration: 0.9,
      ease: 'easeOut',
      onUpdate(v) { if (ref.current) ref.current.textContent = Math.round(v).toString(); },
      onComplete() { prev.current = target; },
    });
    return () => ctrl.stop();
  }, [target]);
  return ref;
}

interface DaysConfig {
  headline: string;
  sublabel: string;
  advice: string;
  numberColor: string;
  badgeCls: string;
  badgeIcon: React.ElementType;
  cardGrad: string;
  accentColor: string;
}

function getDaysConfig(days: number): DaysConfig {
  if (days >= 21) return {
    headline: 'días de agua',
    sublabel: '¡Vas muy bien! Tu cisterna está garantizada.',
    advice:   'Sigue con tus hábitos actuales y tu cisterna durará mucho tiempo.',
    numberColor: '#166534',
    badgeCls: 'badge-ok',
    badgeIcon: ThumbsUp,
    cardGrad: 'linear-gradient(160deg, rgba(240,253,244,1) 0%, rgba(220,252,231,0.8) 100%)',
    accentColor: '#22c55e',
  };
  if (days >= 10) return {
    headline: 'días de agua',
    sublabel: 'Tienes suficiente por ahora.',
    advice:   'Te recomendamos agendar la revisión de tu cisterna pronto.',
    numberColor: '#92400e',
    badgeCls: 'badge-warning',
    badgeIcon: AlertTriangle,
    cardGrad: 'linear-gradient(160deg, rgba(255,251,235,1) 0%, rgba(254,243,199,0.8) 100%)',
    accentColor: '#f59e0b',
  };
  return {
    headline: 'días — ¡Cuidado!',
    sublabel: 'El agua de tu cisterna se está agotando.',
    advice:   'Evita usos innecesarios y llama a tu proveedor de agua lo antes posible.',
    numberColor: '#9f1239',
    badgeCls: 'badge-danger',
    badgeIcon: AlertTriangle,
    cardGrad: 'linear-gradient(160deg, rgba(255,241,242,1) 0%, rgba(254,205,211,0.7) 100%)',
    accentColor: '#f43f5e',
  };
}

export function AutonomyCard({ autonomy }: AutonomyCardProps) {
  const { days_remaining, consumption_rate_lpd, predicted_empty_date, confidence } = autonomy;
  const cfg = getDaysConfig(days_remaining);
  const BadgeIcon = cfg.badgeIcon;
  const daysRef = useCountUp(days_remaining);

  const formattedDate = new Date(predicted_empty_date + 'T00:00:00').toLocaleDateString('es-MX', {
    weekday: 'long', day: 'numeric', month: 'long',
  });

  const confidenceLabel = { high: 'Alta', medium: 'Media', low: 'Baja' }[confidence];

  return (
    <motion.section
      aria-label="Días de agua de la cisterna restantes"
      className="overflow-hidden rounded-2xl text-center"
      style={{
        background: cfg.cardGrad,
        border: `1px solid ${cfg.accentColor}22`,
        boxShadow: `0 4px 24px ${cfg.accentColor}14, 0 1px 4px rgba(0,0,0,0.05)`,
      }}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
    >
      {/* Header */}
      <div className="px-6 pt-6 pb-2">
        <div className="flex items-center justify-center gap-2 mb-0.5">
          <CalendarDays className="w-5 h-5" style={{ color: cfg.accentColor }} aria-hidden="true" />
          <h2 className="text-lg font-bold text-neutral-800">¿Cuánto te dura el agua?</h2>
        </div>
        <p className="text-sm text-neutral-500">Calculado con tu consumo diario de cisterna</p>
      </div>

      {/* Big day counter */}
      <div className="px-6 py-4">
        <motion.span
          key={days_remaining}
          className="text-8xl font-black leading-none tabular-nums block"
          style={{ color: cfg.numberColor }}
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
        >
          <span ref={daysRef}>{days_remaining}</span>
        </motion.span>
        <p className="text-2xl font-bold text-neutral-600 mt-2">{cfg.headline}</p>
        <p className="text-base text-neutral-500 mt-1">{cfg.sublabel}</p>
      </div>

      {/* Badge */}
      <div className="flex justify-center pb-4">
        <span className={cfg.badgeCls}>
          <BadgeIcon className="w-4 h-4" aria-hidden="true" />
          {confidenceLabel === 'Alta' ? 'Estimación confiable' : `Confianza ${confidenceLabel}`}
        </span>
      </div>

      {/* Advice box */}
      <div
        className="mx-6 mb-5 rounded-2xl p-4 text-left"
        style={{
          background: 'rgba(239,246,255,0.8)',
          border: '1px solid rgba(191,219,254,0.7)',
        }}
      >
        <p className="text-base text-blue-900 leading-relaxed font-medium">
          💡 {cfg.advice}
        </p>
      </div>

      {/* Detail grid */}
      <div className="grid grid-cols-2 gap-3 px-6 pb-6 text-left">
        <div
          className="rounded-2xl p-4"
          style={{ background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.9)' }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingDown className="w-4 h-4 text-neutral-400" aria-hidden="true" />
            <p className="section-label">Usas al día</p>
          </div>
          <p className="text-2xl font-black text-neutral-900">
            {consumption_rate_lpd.toFixed(0)}
            <span className="text-sm font-semibold text-neutral-400 ml-1">L</span>
          </p>
        </div>

        <div
          className="rounded-2xl p-4"
          style={{ background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.9)' }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <Clock className="w-4 h-4 text-neutral-400" aria-hidden="true" />
            <p className="section-label">Se acaba el</p>
          </div>
          <p className="text-sm font-bold text-neutral-800 leading-snug capitalize">
            {formattedDate}
          </p>
        </div>
      </div>
    </motion.section>
  );
}
