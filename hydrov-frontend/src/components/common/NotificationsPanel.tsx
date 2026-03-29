import { motion, AnimatePresence } from 'framer-motion';
import { Bell, X, CheckCircle2, AlertTriangle, Droplets, Info } from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────────
type NotifType = 'warning' | 'success' | 'info';

interface Notification {
  id: string;
  type: NotifType;
  title: string;
  body: string;
  time: string;
  read: boolean;
}

// ─── Mock notifications (replace with real WebSocket events or API) ────────────
const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: 'n1',
    type: 'warning',
    title: 'Nivel de cisterna bajo',
    body: 'Tu cisterna está al 15% de capacidad. Considera contactar a tu proveedor.',
    time: 'Hace 2 horas',
    read: false,
  },
  {
    id: 'n2',
    type: 'success',
    title: 'Dispositivo sincronizado',
    body: 'Tu sensor Hydro-V NEZA-001 se ha sincronizado correctamente con la nube.',
    time: 'Ayer, 3:45 p.m.',
    read: false,
  },
  {
    id: 'n3',
    type: 'info',
    title: 'Aviso de tu Municipio',
    body: 'Corte programado de agua en tu colonia el miércoles de 8 AM a 2 PM.',
    time: 'Hace 2 días',
    read: true,
  },
];

const TYPE_CONFIG: Record<NotifType, {
  Icon: React.ElementType;
  iconColor: string;
  bg: string;
  border: string;
  dot: string;
}> = {
  warning: {
    Icon: AlertTriangle,
    iconColor: '#f59e0b',
    bg: 'rgba(255,251,235,0.9)',
    border: 'rgba(253,230,138,0.7)',
    dot: '#f59e0b',
  },
  success: {
    Icon: CheckCircle2,
    iconColor: '#22c55e',
    bg: 'rgba(240,253,244,0.9)',
    border: 'rgba(187,247,208,0.7)',
    dot: '#22c55e',
  },
  info: {
    Icon: Info,
    iconColor: '#0e8de6',
    bg: 'rgba(239,248,255,0.9)',
    border: 'rgba(186,230,253,0.7)',
    dot: '#0e8de6',
  },
};

// ─── Component ─────────────────────────────────────────────────────────────────
interface NotificationsPanelProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationsPanel({ open, onClose }: NotificationsPanelProps) {
  const unread = MOCK_NOTIFICATIONS.filter((n) => !n.read).length;

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="notif-backdrop"
            className="fixed inset-0 z-50 bg-black/20 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Slide-over panel */}
          <motion.aside
            key="notif-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Panel de notificaciones"
            className="fixed top-0 right-0 z-50 h-full w-full max-w-sm flex flex-col"
            style={{
              background: 'linear-gradient(180deg, #f0f7ff 0%, #ffffff 100%)',
              borderLeft: '1px solid rgba(186,230,253,0.6)',
              boxShadow: '-8px 0 40px rgba(0,0,0,0.1)',
            }}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 340, damping: 36 }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-5 py-4 border-b"
              style={{ borderColor: 'rgba(186,230,253,0.5)' }}
            >
              <div className="flex items-center gap-2.5">
                <div
                  className="flex items-center justify-center w-9 h-9 rounded-xl"
                  style={{ background: 'rgba(239,248,255,0.9)', border: '1px solid rgba(186,230,253,0.6)' }}
                >
                  <Bell className="w-5 h-5" style={{ color: '#0e8de6' }} aria-hidden="true" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-neutral-900">Notificaciones</h2>
                  {unread > 0 && (
                    <p className="text-sm text-neutral-500">{unread} sin leer</p>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-xl text-neutral-400 hover:text-neutral-700 transition-colors"
                style={{ minHeight: 40, minWidth: 40, background: 'none', border: 'none' }}
                aria-label="Cerrar notificaciones"
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </button>
            </div>

            {/* Notification list */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {MOCK_NOTIFICATIONS.map((notif, i) => {
                const cfg = TYPE_CONFIG[notif.type];
                const Icon = cfg.Icon;
                return (
                  <motion.div
                    key={notif.id}
                    className="rounded-2xl p-4"
                    style={{
                      background: cfg.bg,
                      border: `1px solid ${cfg.border}`,
                    }}
                    initial={{ opacity: 0, x: 24 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.07, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                  >
                    <div className="flex items-start gap-3">
                      {/* Icon + unread dot */}
                      <div className="relative shrink-0 mt-0.5">
                        <Icon className="w-5 h-5" style={{ color: cfg.iconColor }} aria-hidden="true" />
                        {!notif.read && (
                          <span
                            className="absolute -top-1 -right-1 w-2 h-2 rounded-full"
                            style={{ background: cfg.dot }}
                            aria-label="Sin leer"
                          />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-base font-bold text-neutral-900 leading-snug">
                          {notif.title}
                        </p>
                        <p className="text-sm text-neutral-600 mt-1 leading-relaxed">
                          {notif.body}
                        </p>
                        <p className="text-xs font-semibold text-neutral-400 mt-2 uppercase tracking-wide">
                          {notif.time}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Footer */}
            <div
              className="px-5 py-4 border-t text-center"
              style={{ borderColor: 'rgba(226,232,240,0.8)' }}
            >
              <div className="flex items-center justify-center gap-2 text-sm text-neutral-400">
                <Droplets className="w-4 h-4" style={{ color: '#38aaf8' }} aria-hidden="true" />
                <span>Solo se muestran los últimos 7 días</span>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
