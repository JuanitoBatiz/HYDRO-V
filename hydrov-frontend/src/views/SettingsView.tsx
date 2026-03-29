import { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, MessageSquare, Droplets, Bell, Smartphone, Shield, Info } from 'lucide-react';

// ─── Toggle switch component ───────────────────────────────────────────────────
interface ToggleProps {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  accentColor?: string;
}

function Toggle({ id, checked, onChange, disabled = false, accentColor = '#0e8de6' }: ToggleProps) {
  return (
    <button
      id={id}
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      type="button"
      style={{
        width: 52,
        height: 30,
        borderRadius: 9999,
        background: checked ? accentColor : '#cbd5e1',
        border: 'none',
        cursor: disabled ? 'not-allowed' : 'pointer',
        position: 'relative',
        transition: 'background 0.25s',
        flexShrink: 0,
        opacity: disabled ? 0.5 : 1,
        padding: 0,
      }}
      aria-label={`Toggle ${id}`}
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        style={{
          position: 'absolute',
          top: 3,
          left: checked ? 'calc(100% - 27px)' : 3,
          width: 24,
          height: 24,
          borderRadius: '50%',
          background: 'white',
          boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
        }}
      />
    </button>
  );
}

// ─── Settings sections ─────────────────────────────────────────────────────────
interface SettingItem {
  id: string;
  Icon: React.ElementType;
  label: string;
  description: string;
  defaultValue: boolean;
  accentColor?: string;
  disabled?: boolean;
  badge?: string;
}

const SETTINGS_GROUPS: Array<{ groupLabel: string; items: SettingItem[] }> = [
  {
    groupLabel: 'Alertas y Notificaciones',
    items: [
      {
        id: 'sms_leak',
        Icon: MessageSquare,
        label: 'Alertas de fuga por SMS',
        description: 'Recibe un mensaje de texto si se detecta una fuga en tu sistema.',
        defaultValue: true,
        accentColor: '#0e8de6',
      },
      {
        id: 'notify_low_level',
        Icon: Droplets,
        label: 'Aviso de cisterna baja',
        description: 'Notificarme cuando la cisterna baje del 20% de capacidad.',
        defaultValue: true,
        accentColor: '#f59e0b',
      },
      {
        id: 'municipal_alerts',
        Icon: Bell,
        label: 'Avisos municipales',
        description: 'Recibir notificaciones de cortes y alertas del municipio en tu zona.',
        defaultValue: false,
        accentColor: '#0e8de6',
      },
      {
        id: 'weekly_report',
        Icon: Info,
        label: 'Reporte semanal',
        description: 'Recibe cada lunes un resumen de tu consumo de agua de la semana.',
        defaultValue: false,
        accentColor: '#06b6d4',
      },
    ],
  },
  {
    groupLabel: 'Dispositivo',
    items: [
      {
        id: 'auto_sync',
        Icon: Smartphone,
        label: 'Sincronización automática',
        description: 'Tu sensor Hydro-V enviará lecturas cada 5 minutos.',
        defaultValue: true,
        accentColor: '#22c55e',
      },
      {
        id: 'power_saving',
        Icon: Settings,
        label: 'Modo ahorro de energía',
        description: 'Reduce la frecuencia de lecturas para extender la batería del sensor.',
        defaultValue: false,
        accentColor: '#10b981',
        disabled: false,
      },
    ],
  },
  {
    groupLabel: 'Privacidad',
    items: [
      {
        id: 'share_data',
        Icon: Shield,
        label: 'Compartir datos anónimos',
        description: 'Ayuda a mejorar Hydro-V compartiendo datos de uso de forma anónima.',
        defaultValue: true,
        accentColor: '#6366f1',
        badge: 'Opcional',
      },
    ],
  },
];

const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};
const itemVariants = {
  hidden: { opacity: 0, y: 18 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] } },
};

export function SettingsView() {
  // Initialize state from default values
  const [toggles, setToggles] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    SETTINGS_GROUPS.forEach((g) => g.items.forEach((item) => { init[item.id] = item.defaultValue; }));
    return init;
  });

  function handleToggle(id: string, value: boolean) {
    setToggles((prev) => ({ ...prev, [id]: value }));
  }

  return (
    <motion.div
      className="max-w-2xl mx-auto px-4 md:px-6 py-6 space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* Page header */}
      <motion.div variants={itemVariants}>
        <div className="flex items-center gap-2.5 mb-1">
          <Settings className="w-6 h-6" style={{ color: '#0e8de6' }} aria-hidden="true" />
          <h2 className="text-2xl font-bold text-neutral-900">Ajustes</h2>
        </div>
        <p className="text-base text-neutral-500">Personaliza tu experiencia Hydro-V</p>
      </motion.div>

      {/* Settings groups */}
      {SETTINGS_GROUPS.map((group) => (
        <motion.div key={group.groupLabel} variants={itemVariants} className="space-y-2">
          {/* Group label */}
          <p
            className="px-1 text-xs font-bold uppercase tracking-widest"
            style={{ color: '#64748b' }}
          >
            {group.groupLabel}
          </p>

          {/* Items card */}
          <div
            className="rounded-2xl overflow-hidden"
            style={{ background: 'white', border: '1px solid rgba(226,232,240,0.8)', boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}
          >
            {group.items.map((item, i) => {
              const Icon = item.Icon;
              const checked = toggles[item.id] ?? false;
              return (
                <div
                  key={item.id}
                  className="flex items-start gap-4 px-5 py-4"
                  style={{ borderTop: i > 0 ? '1px solid rgba(241,245,249,1)' : 'none' }}
                >
                  {/* Icon */}
                  <div
                    className="flex items-center justify-center w-10 h-10 rounded-xl shrink-0 mt-0.5"
                    style={{
                      background: checked ? `${item.accentColor ?? '#0e8de6'}14` : 'rgba(248,250,252,0.9)',
                      border: `1px solid ${checked ? `${item.accentColor ?? '#0e8de6'}30` : 'rgba(226,232,240,0.8)'}`,
                      transition: 'all 0.25s',
                    }}
                  >
                    <Icon
                      className="w-5 h-5"
                      style={{ color: checked ? item.accentColor ?? '#0e8de6' : '#94a3b8' }}
                      aria-hidden="true"
                    />
                  </div>

                  {/* Text */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <label
                        htmlFor={item.id}
                        className="text-base font-semibold text-neutral-900 cursor-pointer"
                      >
                        {item.label}
                      </label>
                      {item.badge && (
                        <span
                          className="text-xs font-bold px-2 py-0.5 rounded-full"
                          style={{ background: '#eff8ff', color: '#0558a0', border: '1px solid #bfdbfe' }}
                        >
                          {item.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-neutral-500 mt-0.5 leading-relaxed">
                      {item.description}
                    </p>
                  </div>

                  {/* Toggle */}
                  <Toggle
                    id={item.id}
                    checked={checked}
                    onChange={(v) => handleToggle(item.id, v)}
                    disabled={item.disabled}
                    accentColor={item.accentColor}
                  />
                </div>
              );
            })}
          </div>
        </motion.div>
      ))}

      {/* Device info card */}
      <motion.div
        variants={itemVariants}
        className="rounded-2xl p-5"
        style={{
          background: 'linear-gradient(160deg, rgba(239,248,255,0.9) 0%, rgba(224,242,254,0.7) 100%)',
          border: '1px solid rgba(186,230,253,0.6)',
        }}
      >
        <p className="text-xs font-bold uppercase tracking-widest text-neutral-400 mb-3">
          Información del dispositivo
        </p>
        {[
          { label: 'Dispositivo',   value: 'HYDRO-V-NEZA-001' },
          { label: 'Firmware',      value: 'v2.1.4 (actualizado)' },
          { label: 'Conectividad',  value: 'WiFi 2.4 GHz · MQTT' },
          { label: 'Última sincronía', value: 'Hace 3 minutos' },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="flex justify-between items-center py-2"
            style={{ borderTop: '1px solid rgba(186,230,253,0.3)' }}
          >
            <span className="text-sm text-neutral-500">{label}</span>
            <span className="text-sm font-semibold text-neutral-800">{value}</span>
          </div>
        ))}
      </motion.div>

      {/* Version footer */}
      <motion.p
        variants={itemVariants}
        className="text-center text-xs text-neutral-400 pb-2"
      >
        Hydro-V App · v1.0.0 · © 2026 Hydro-V Technologies
      </motion.p>

      <div className="h-4 pb-safe" />
    </motion.div>
  );
}
