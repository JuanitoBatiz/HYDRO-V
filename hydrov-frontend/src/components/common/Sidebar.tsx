import { motion } from 'framer-motion';
import { Droplets, LayoutDashboard, BarChart3, Settings, Bell, LogOut, ChevronRight, BrainCircuit } from 'lucide-react';

export type SectionId = 'dashboard' | 'history' | 'analytics' | 'settings';

interface NavItemConfig {
  id: SectionId;
  icon: React.ElementType;
  label: string;
}

const NAV_ITEMS: NavItemConfig[] = [
  { id: 'dashboard',  icon: LayoutDashboard, label: 'Inicio' },
  { id: 'history',    icon: BarChart3,       label: 'Historial' },
  { id: 'analytics',  icon: BrainCircuit,    label: 'Inteligencia Hídrica' },
  { id: 'settings',   icon: Settings,        label: 'Ajustes' },
];

interface SidebarProps {
  activeSection?: SectionId;
  onSectionChange?: (id: SectionId) => void;
  deviceCode?: string;
  onLogout?: () => void;
  onNotificationsClick?: () => void;
  unreadCount?: number;
}

export function Sidebar({
  activeSection = 'dashboard',
  onSectionChange,
  deviceCode = 'HYDRO-V-001',
  onLogout,
  onNotificationsClick,
  unreadCount = 0,
}: SidebarProps) {
  return (
    <aside
      className="hidden md:flex flex-col w-72 min-h-screen shrink-0 bg-white/70 dark:bg-ocean-900/50 backdrop-blur-md border-r border-neutral-200 dark:border-white/10 shadow-sm transition-colors duration-500"
      aria-label="Menú de navegación"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-neutral-200 dark:border-white/10">
        <div
          className="flex items-center justify-center w-12 h-12 rounded-2xl shrink-0 transition-transform hover:scale-105"
          style={{ background: '#0e8de6', boxShadow: '0 0 12px rgba(14,141,230,0.6)' }}
        >
          <Droplets className="w-6 h-6 text-white" aria-hidden="true" />
        </div>
        <div>
          <span className="text-xl font-black text-neutral-900 dark:text-f1f5f9">Hydro-V</span>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">Tu agua, bajo control</p>
        </div>
      </div>

      {/* Device info pill */}
      <div
        className="mx-4 mt-5 px-4 py-3 rounded-2xl shadow-sm dark:shadow-none"
        style={{ background: 'rgba(14, 141, 230, 0.05)', border: '1px solid rgba(14, 141, 230, 0.2)' }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wide mb-0.5"
          style={{ color: '#0e8de6' }}
        >
          Dispositivo vinculado
        </p>
        <p className="text-base font-bold text-neutral-900 dark:text-f1f5f9">{deviceCode}</p>
        <div className="flex items-center gap-1.5 mt-1">
          <span
            className="w-2 h-2 rounded-full animate-pulse shrink-0"
            style={{ background: '#22c55e', boxShadow: '0 0 8px #22c55e' }}
            aria-hidden="true"
          />
          <span className="text-sm font-medium text-success-text dark:text-success-icon">Conectado</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1" aria-label="Secciones">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          return (
            <motion.button
              key={item.id}
              onClick={() => onSectionChange?.(item.id)}
              className={`nav-item w-full text-left ${isActive ? 'active dark-active' : ''} dark:text-neutral-300 dark:hover:bg-white/5 dark:hover:text-f1f5f9`}
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.98 }}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon
                className="w-5 h-5 shrink-0 transition-colors"
                style={{ color: isActive ? '#38aaf8' : 'currentColor' }}
                aria-hidden="true"
              />
              <span className="text-base font-semibold">{item.label}</span>
              {isActive && (
                <ChevronRight
                  className="ml-auto w-4 h-4"
                  style={{ color: '#38aaf8' }}
                  aria-hidden="true"
                />
              )}
            </motion.button>
          );
        })}
      </nav>

      {/* Bottom: notifications + logout */}
      <div className="px-3 py-4 border-t border-neutral-200 dark:border-white/10 space-y-1">
        {/* Notifications button with badge */}
        <button
          onClick={onNotificationsClick}
          className="nav-item w-full relative dark:text-neutral-300 dark:hover:bg-white/5 dark:hover:text-f1f5f9"
          aria-label={`Notificaciones${unreadCount > 0 ? ` (${unreadCount} sin leer)` : ''}`}
        >
          <Bell className="w-5 h-5" aria-hidden="true" />
          <span className="text-base font-semibold">Notificaciones</span>
          {unreadCount > 0 && (
            <span
              className="ml-auto text-xs font-bold rounded-full px-2 py-0.5"
              style={{ background: '#f59e0b', color: 'white', boxShadow: '0 0 8px rgba(245, 158, 11, 0.6)' }}
              aria-hidden="true"
            >
              {unreadCount}
            </span>
          )}
        </button>

        {/* Logout — calls onLogout to return to Login */}
        <button
          onClick={onLogout}
          className="nav-item w-full dark:hover:bg-danger-bg/20"
          style={{ color: '#f43f5e' }}
          aria-label="Cerrar sesión"
        >
          <LogOut className="w-5 h-5" aria-hidden="true" />
          <span className="text-base font-semibold">Cerrar sesión</span>
        </button>
      </div>
    </aside>
  );
}
