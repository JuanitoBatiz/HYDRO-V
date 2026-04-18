import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Layout
import { Sidebar, type SectionId } from '@/components/common/Sidebar';
import { Navbar }                  from '@/components/common/Navbar';
import { LoadingSpinner }          from '@/components/common/LoadingSpinner';
import { NotificationsPanel }      from '@/components/common/NotificationsPanel';

// Auth
import { Login } from '@/components/Login';

// Dashboard widgets
import { WaterLevelGauge }     from '@/components/dashboard/WaterLevelGauge';
import { AutonomyCard }        from '@/components/dashboard/AutonomyCard';
import { LeakAlertBanner }     from '@/components/dashboard/LeakAlertBanner';
import { RainPredictorWidget } from '@/components/dashboard/RainPredictorWidget';

// Views
import { HistoryView }   from '@/views/HistoryView';
import { SettingsView }  from '@/views/SettingsView';
import { AnalyticsView } from '@/views/AnalyticsView';

// Data hook
import { useHydroData } from '@/hooks/useTelemetry';

// Icons
import {
  Droplets, Waves, CheckCircle2, AlertTriangle,
  ToggleLeft, ToggleRight, LogOut, Phone,
} from 'lucide-react';

import '@/styles/global.css';

// ─── Page title map ───────────────────────────────────────────────────────────
const PAGE_TITLES: Record<SectionId, string> = {
  dashboard: 'Mi Panel de Agua',
  history:   'Historial de Consumo',
  analytics: 'Inteligencia Hídrica',
  settings:  'Ajustes',
};

// ─── Stagger animation ────────────────────────────────────────────────────────
const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

// ─── Quick stat pill ──────────────────────────────────────────────────────────
interface QuickStatProps {
  icon: React.ElementType;
  label: string;
  value: string;
  accent?: 'ok' | 'warn' | 'danger' | 'neutral';
}

function QuickStat({ icon: Icon, label, value, accent = 'neutral' }: QuickStatProps) {
  const styles: Record<string, React.CSSProperties> = {
    ok:      { background: 'rgba(240,253,244,0.9)', border: '1px solid #bbf7d0', color: '#166534' },
    warn:    { background: 'rgba(255,251,235,0.9)', border: '1px solid #fde68a', color: '#92400e' },
    danger:  { background: 'rgba(255,241,242,0.9)', border: '1px solid #fecdd3', color: '#9f1239' },
    neutral: { background: 'rgba(248,250,252,0.9)', border: '1px solid #e2e8f0', color: '#334155' },
  };
  return (
    <div className="flex items-center gap-3 rounded-2xl p-4" style={styles[accent]}>
      <Icon className="w-6 h-6 shrink-0" aria-hidden="true" />
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{label}</p>
        <p className="text-base font-bold leading-tight">{value}</p>
      </div>
    </div>
  );
}

// ─── Dashboard view ───────────────────────────────────────────────────────────
interface DashboardViewProps {
  onShowLeakBanner: () => void;
  leakBannerVisible: boolean;
  leakSeverity: 'warning' | 'danger';
  setLeakBannerVisible: React.Dispatch<React.SetStateAction<boolean>>;
  setLeakSeverity: React.Dispatch<React.SetStateAction<'warning' | 'danger'>>;
  onLogout: () => void;
}

function DashboardView({
  leakBannerVisible,
  leakSeverity,
  setLeakBannerVisible,
  setLeakSeverity,
  onLogout,
}: DashboardViewProps) {
  const { telemetry } = useHydroData();

  if (!telemetry) return <LoadingSpinner />;

  const { level, autonomy, turbidity, flow } = telemetry;
  const turbidityAccent: QuickStatProps['accent'] =
    turbidity.status === 'clear' ? 'ok' :
    turbidity.status === 'critical' ? 'danger' : 'warn';
  const flowAccent: QuickStatProps['accent'] = flow.rate_lpm > 2.5 ? 'warn' : 'ok';

  return (
    <motion.div
      className="max-w-2xl mx-auto px-4 md:px-6 py-6 space-y-5"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* Leak alert banner (outside stagger — conditionally managed) */}
      <LeakAlertBanner
        visible={leakBannerVisible}
        onDismiss={() => setLeakBannerVisible(false)}
        severity={leakSeverity}
      />

      {/* Greeting */}
      <motion.div variants={itemVariants}>
        <h2 className="text-2xl font-bold text-neutral-900">¡Hola! 👋</h2>
        <p className="text-base text-neutral-500 mt-0.5">El agua de tu cisterna, en un vistazo.</p>
      </motion.div>

      {/* Water level gauge */}
      <motion.div variants={itemVariants}>
        <WaterLevelGauge level={level} />
      </motion.div>

      {/* Autonomy */}
      <motion.div variants={itemVariants}>
        <AutonomyCard autonomy={autonomy} />
      </motion.div>

      {/* Weather */}
      <motion.div variants={itemVariants}>
        <RainPredictorWidget />
      </motion.div>

      {/* Quick stats */}
      <motion.section
        aria-label="Estado rápido del sistema"
        className="grid grid-cols-2 gap-3"
        variants={itemVariants}
      >
        <QuickStat icon={Waves} label="Calidad del agua"
          value={turbidity.status === 'clear' ? 'Clara ✓' : turbidity.status === 'moderate' ? 'Normal' : 'Revisar'}
          accent={turbidityAccent}
        />
        <QuickStat icon={Droplets} label="Flujo actual"
          value={`${flow.rate_lpm.toFixed(1)} L/min`}
          accent={flowAccent}
        />
        <QuickStat icon={CheckCircle2} label="Estado de la red"
          value={telemetry.leak.status === 'stable' ? 'Sin fugas' : '¡Revisar!'}
          accent={telemetry.leak.status === 'stable' ? 'ok' : 'danger'}
        />
        <QuickStat icon={AlertTriangle} label="Alertas activas"
          value={leakBannerVisible ? '1 activa' : 'Ninguna'}
          accent={leakBannerVisible ? 'warn' : 'ok'}
        />
      </motion.section>

      {/* Demo controls */}
      <motion.div
        variants={itemVariants}
        className="rounded-2xl p-5"
        style={{
          background: 'rgba(255,255,255,0.8)',
          border: '1px solid rgba(226,232,240,0.8)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        }}
      >
        <p className="text-xs font-bold text-neutral-400 uppercase tracking-widest mb-4">
          🛠 Controles de demostración
        </p>
        <div className="space-y-3">
          {[
            {
              label: 'Aviso municipal (amarillo)',
              desc: 'Simula alerta de la delegación',
              sev: 'warning' as const,
            },
            {
              label: 'Alerta de fuga (rojo)',
              desc: 'Simula fuga detectada por el sensor',
              sev: 'danger' as const,
            },
          ].map(({ label, desc, sev }) => {
            const isOn = leakBannerVisible && leakSeverity === sev;
            return (
              <div key={sev} className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-base font-semibold text-neutral-800">{label}</p>
                  <p className="text-sm text-neutral-500">{desc}</p>
                </div>
                <button
                  onClick={() => {
                    setLeakSeverity(sev);
                    setLeakBannerVisible((v) => leakSeverity === sev ? !v : true);
                  }}
                  style={{ color: isOn ? (sev === 'danger' ? '#f43f5e' : '#0e8de6') : '#cbd5e1', background: 'none', border: 'none' }}
                  className="shrink-0 transition-colors"
                  aria-label={isOn ? `Ocultar ${label}` : `Mostrar ${label}`}
                >
                  {isOn
                    ? <ToggleRight className="w-9 h-9" />
                    : <ToggleLeft  className="w-9 h-9" />}
                </button>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Help footer */}
      <motion.div
        variants={itemVariants}
        className="rounded-2xl p-5 flex items-center gap-4"
        style={{ background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}
      >
        <div
          className="flex items-center justify-center w-12 h-12 rounded-2xl shrink-0"
          style={{ background: 'rgba(239,248,255,0.9)', border: '1px solid rgba(186,230,253,0.6)' }}
        >
          <Phone className="w-6 h-6" style={{ color: '#0e8de6' }} aria-hidden="true" />
        </div>
        <div>
          <p className="text-base font-bold text-neutral-900">¿Necesitas ayuda?</p>
          <p className="text-sm text-neutral-500">
            Llama a soporte Hydro-V:{' '}
            <a href="tel:8001234567" className="font-semibold underline underline-offset-2" style={{ color: '#026fc2' }}>
              800 123 4567
            </a>
          </p>
        </div>
      </motion.div>

      {/* Mobile logout */}
      <motion.div variants={itemVariants} className="md:hidden">
        <button
          onClick={onLogout}
          className="flex items-center justify-center gap-2 w-full py-4 font-semibold text-base rounded-2xl transition-colors"
          style={{ color: '#9f1239', border: '2px solid #fecdd3', background: '#fff1f2' }}
        >
          <LogOut className="w-5 h-5" aria-hidden="true" />
          Cerrar sesión
        </button>
      </motion.div>

      <div className="h-4 pb-safe" />
    </motion.div>
  );
}

// ─── Authenticated app shell (handles routing + notifications) ────────────────
interface AppShellProps {
  email: string;
  deviceCode: string;
  onLogout: () => void;
}

// Count of unread mock notifications (matches NotificationsPanel mock data)
const UNREAD_COUNT = 2;

function AppShell({ email: _email, deviceCode, onLogout }: AppShellProps) {
  const { isConnected, isLoading, lastUpdate } = useHydroData();
  const [section, setSection]                   = useState<SectionId>('dashboard');
  const [notifOpen, setNotifOpen]               = useState(false);
  const [leakBannerVisible, setLeakBannerVisible] = useState(false);
  const [leakSeverity, setLeakSeverity]           = useState<'warning' | 'danger'>('warning');
  const [isSidebarOpen, setIsSidebarOpen]         = useState(false);

  if (isLoading) return <LoadingSpinner />;

  return (
    <div
      className="min-h-dvh flex"
      style={{ background: 'linear-gradient(160deg, #f0f7ff 0%, #f8fafc 60%, #fefefe 100%)' }}
    >
      {/* Desktop & Mobile Slide-over sidebar */}
      <Sidebar
        activeSection={section}
        onSectionChange={setSection}
        deviceCode={deviceCode}
        onLogout={onLogout}
        onNotificationsClick={() => setNotifOpen(true)}
        unreadCount={UNREAD_COUNT}
        isOpen={isSidebarOpen}
        onMenuClose={() => setIsSidebarOpen(false)}
      />

      {/* Main content column */}
      <div className="flex-1 flex flex-col min-h-dvh overflow-hidden w-full relative">
        <Navbar
          isConnected={isConnected}
          deviceCode={deviceCode}
          lastUpdate={lastUpdate}
          pageTitle={PAGE_TITLES[section]}
          unreadCount={UNREAD_COUNT}
          onNotificationsClick={() => setNotifOpen(true)}
          onMenuClick={() => setIsSidebarOpen(!isSidebarOpen)}
        />

        {/* Animated view switcher */}
        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            {section === 'dashboard' && (
              <motion.div
                key="dashboard"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.3 }}
              >
                <DashboardView
                  onShowLeakBanner={() => setLeakBannerVisible(true)}
                  leakBannerVisible={leakBannerVisible}
                  leakSeverity={leakSeverity}
                  setLeakBannerVisible={setLeakBannerVisible}
                  setLeakSeverity={setLeakSeverity}
                  onLogout={onLogout}
                />
              </motion.div>
            )}

            {section === 'history' && (
              <motion.div
                key="history"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.3 }}
              >
                <HistoryView />
              </motion.div>
            )}

            {section === 'analytics' && (
              <motion.div
                key="analytics"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.3 }}
              >
                <AnalyticsView />
              </motion.div>
            )}

            {section === 'settings' && (
              <motion.div
                key="settings"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.3 }}
              >
                <SettingsView />
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>

      {/* Notifications slide-over (portal over everything) */}
      <NotificationsPanel
        open={notifOpen}
        onClose={() => setNotifOpen(false)}
      />
    </div>
  );
}

// ─── App root: Login → Dashboard routing ─────────────────────────────────────
export default function App() {
  const [session, setSession] = useState<{ email: string; deviceCode: string } | null>(null);

  return (
    <>
      <AnimatePresence mode="wait">
        {!session ? (
          <motion.div
            key="login"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.2 } }}
          >
            <Login onLogin={(email, deviceCode) => setSession({ email, deviceCode })} />
          </motion.div>
        ) : (
          <motion.div
            key="app"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
          >
            <AppShell
              email={session.email}
              deviceCode={session.deviceCode}
              onLogout={() => setSession(null)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
