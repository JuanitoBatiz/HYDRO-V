import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X, Info } from 'lucide-react';

interface LeakAlertBannerProps {
  /** Controls whether the banner is visible */
  visible: boolean;
  /** Callback to dismiss the banner */
  onDismiss: () => void;
  /** 'warning' = yellow (municipal advisory), 'danger' = red (confirmed leak) */
  severity?: 'warning' | 'danger';
  /** Custom message override */
  message?: string;
}

const SEVERITY_CONFIG = {
  warning: {
    wrapper: 'bg-warning-bg border-warning-border',
    icon:    'text-warning-icon',
    title:   'text-warning-text',
    body:    'text-amber-800',
    dismiss: 'text-amber-600 hover:bg-amber-100',
    label:   'Aviso de tu Municipio',
    defaultMsg:
      'Hemos detectado una posible fuga en tu zona. Te sugerimos revisar tu nivel de agua y evitar desperdicios en los próximos días.',
  },
  danger: {
    wrapper: 'bg-danger-bg border-danger-border',
    icon:    'text-danger-icon',
    title:   'text-danger-text',
    body:    'text-rose-800',
    dismiss: 'text-rose-600 hover:bg-rose-100',
    label:   'Alerta de Fuga Detectada',
    defaultMsg:
      'Tu sistema detectó una posible fuga. Por favor revisa tus tuberías y válvulas. Si el nivel sigue bajando, contacta a un técnico.',
  },
};

export function LeakAlertBanner({
  visible,
  onDismiss,
  severity = 'warning',
  message,
}: LeakAlertBannerProps) {
  const cfg = SEVERITY_CONFIG[severity];

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          role="alert"
          aria-live="assertive"
          aria-label={cfg.label}
          className={`relative w-full rounded-2xl border-2 p-4 md:p-5 ${cfg.wrapper}`}
          initial={{ opacity: 0, y: -20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -12, scale: 0.98 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
        >
          <div className="flex gap-4">
            {/* Icon */}
            <div className="shrink-0 mt-0.5">
              <AlertTriangle className={`w-6 h-6 ${cfg.icon}`} aria-hidden="true" />
            </div>

            {/* Text content */}
            <div className="flex-1 min-w-0">
              <h3 className={`text-base font-bold leading-snug ${cfg.title}`}>
                ⚠️ {cfg.label}
              </h3>
              <p className={`mt-1.5 text-base leading-relaxed ${cfg.body}`}>
                {message ?? cfg.defaultMsg}
              </p>

              {severity === 'warning' && (
                <div className="mt-3 flex items-start gap-2 text-sm text-amber-700 bg-amber-50/60 rounded-xl p-3 border border-amber-200">
                  <Info className="w-4 h-4 shrink-0 mt-0.5 text-amber-500" aria-hidden="true" />
                  <span>
                    <strong>Consejo:</strong> Cierra las llaves que no uses y revisa que no
                    haya goteos visibles en tu cocina o baño.
                  </span>
                </div>
              )}
            </div>

            {/* Dismiss button */}
            <button
              onClick={onDismiss}
              className={`shrink-0 self-start p-2 rounded-xl transition-colors ${cfg.dismiss}`}
              aria-label="Cerrar aviso"
              title="Cerrar"
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
