import { Droplets, Wifi, WifiOff, Bell } from 'lucide-react';

interface NavbarProps {
  isConnected: boolean;
  deviceCode?: string;
  lastUpdate?: Date | null;
  pageTitle?: string;
  /** Number of unread notifications — shows red dot when > 0 */
  unreadCount?: number;
  onNotificationsClick?: () => void;
}

export function Navbar({
  isConnected,
  deviceCode = 'HYDRO-V-001',
  lastUpdate,
  pageTitle = 'Mi Panel de Agua',
  unreadCount = 0,
  onNotificationsClick,
}: NavbarProps) {
  const timeStr = lastUpdate
    ? lastUpdate.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <header className="sticky top-0 z-40 flex items-center justify-between px-4 md:px-6 py-3 bg-white/90 backdrop-blur-sm border-b border-neutral-200 shadow-sm">
      {/* Left: brand (mobile only — sidebar handles desktop) */}
      <div className="flex items-center gap-2.5 md:hidden">
        <div
          className="flex items-center justify-center w-9 h-9 rounded-xl shrink-0"
          style={{ background: '#0e8de6' }}
        >
          <Droplets className="w-5 h-5 text-white" aria-hidden="true" />
        </div>
        <span className="text-lg font-black text-neutral-900">Hydro-V</span>
      </div>

      {/* Desktop title — reflects current view */}
      <div className="hidden md:block">
        <h1 className="text-xl font-bold text-neutral-900">{pageTitle}</h1>
        <p className="text-sm text-neutral-500">
          {deviceCode}
          {timeStr && <> · Actualizado a las {timeStr}</>}
        </p>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-2">
        {/* Connection badge */}
        <div
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold border"
          style={isConnected
            ? { background: '#f0fdf4', borderColor: '#bbf7d0', color: '#166534' }
            : { background: '#fff1f2', borderColor: '#fecdd3', color: '#9f1239' }}
        >
          {isConnected
            ? <Wifi className="w-4 h-4" aria-hidden="true" />
            : <WifiOff className="w-4 h-4" aria-hidden="true" />}
          <span>{isConnected ? 'En línea' : 'Sin conexión'}</span>
        </div>

        {/* Mobile connection dot */}
        <div
          className="sm:hidden w-2.5 h-2.5 rounded-full"
          style={{ background: isConnected ? '#22c55e' : '#f43f5e' }}
          aria-label={isConnected ? 'Conectado' : 'Sin conexión'}
        />

        {/* Notifications bell — interactive */}
        <button
          onClick={onNotificationsClick}
          className="relative p-2 rounded-xl transition-colors"
          style={{
            background: 'none',
            border: 'none',
            color: '#64748b',
            minHeight: 44,
            minWidth: 44,
            cursor: 'pointer',
          }}
          aria-label={`Notificaciones${unreadCount > 0 ? ` (${unreadCount} sin leer)` : ''}`}
          aria-haspopup="dialog"
        >
          <Bell className="w-5 h-5" aria-hidden="true" />

          {/* Unread badge — pulse when notifications exist */}
          {unreadCount > 0 && (
            <span
              className="absolute top-1.5 right-1.5 flex items-center justify-center rounded-full text-white font-bold"
              style={{
                background: '#f59e0b',
                minWidth: '1rem',
                height: '1rem',
                fontSize: '0.6rem',
                lineHeight: 1,
                padding: '0 2px',
              }}
              aria-hidden="true"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}
