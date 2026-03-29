import { useState } from 'react';
import { motion } from 'framer-motion';
import { Wifi, MapPin, ExternalLink, Zap } from 'lucide-react';

// Home Address in Nezahualcóyotl
const HOME_ADDRESS = "Calle 34 No.174, El Sol, Nezahualcóyotl, Estado de México";
const NEZA_LAT = 19.4017;
const NEZA_LON = -99.0153;

// Google Maps Embed — using the exact address for precision
const MAP_SRC =
  `https://maps.google.com/maps?q=${encodeURIComponent(HOME_ADDRESS)}&z=18&output=embed&hl=es`;

interface LocationWidgetProps {
  deviceCode?: string;
  isConnected?: boolean;
}

export function LocationWidget({
  deviceCode = 'HYDRO-V-NEZA-001',
  isConnected = true,
}: LocationWidgetProps) {
  const [mapLoaded, setMapLoaded] = useState(false);

  return (
    <motion.section
      aria-label="Ubicación del nodo Hydro-V"
      className="overflow-hidden rounded-2xl"
      style={{
        border: '1px solid rgba(186,230,253,0.6)',
        boxShadow: '0 4px 24px rgba(14,141,230,0.08), 0 1px 4px rgba(0,0,0,0.05)',
      }}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Card Header */}
      <div
        className="flex items-center justify-between px-5 py-4"
        style={{
          background: 'linear-gradient(135deg, rgba(239,248,255,1) 0%, rgba(224,242,254,0.9) 100%)',
          borderBottom: '1px solid rgba(186,230,253,0.5)',
        }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="flex items-center justify-center w-9 h-9 rounded-xl"
            style={{ background: '#0e8de6', boxShadow: '0 2px 8px rgba(14,141,230,0.3)' }}
          >
            <MapPin className="w-5 h-5 text-white" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-base font-bold text-neutral-900">Ubicación del Sensor</h3>
            <p className="text-sm text-neutral-500">Nezahualcóyotl, Estado de México</p>
          </div>
        </div>
        <a
          href={`https://maps.google.com/?q=${encodeURIComponent(HOME_ADDRESS)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 rounded-xl transition-colors"
          style={{ color: '#0e8de6', background: 'none', border: 'none', minHeight: 36 }}
          aria-label="Abrir en Google Maps"
          title="Ver en Google Maps"
        >
          <ExternalLink className="w-4 h-4" aria-hidden="true" />
        </a>
      </div>

      {/* Map container */}
      <div className="relative" style={{ height: 280 }}>
        {/* Loading shimmer */}
        {!mapLoaded && (
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%)' }}
          >
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.8, repeat: Infinity }}
              className="flex flex-col items-center gap-3"
            >
              <MapPin className="w-10 h-10" style={{ color: '#38bdf8' }} aria-hidden="true" />
              <p className="text-sm font-medium text-neutral-400">Cargando mapa…</p>
            </motion.div>
          </div>
        )}

        {/* Actual map iframe */}
        <iframe
          src={MAP_SRC}
          title="Mapa de ubicación del sensor Hydro-V en Nezahualcóyotl"
          className="w-full h-full border-0"
          loading="lazy"
          onLoad={() => setMapLoaded(true)}
          style={{ filter: 'saturate(0.85) brightness(1.02)' }}
          allowFullScreen
        />

        {/* ── Glassmorphism overlay card ─────────────────────────────── */}
        <div
          className="absolute bottom-3 left-3 right-3"
          style={{
            background: 'rgba(255,255,255,0.72)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            borderRadius: '1rem',
            border: '1px solid rgba(255,255,255,0.85)',
            boxShadow: '0 4px 24px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08)',
            padding: '0.875rem 1rem',
          }}
        >
          <div className="flex items-center justify-between gap-3">
            {/* Left: node info */}
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: 'rgba(14,141,230,0.1)', border: '1px solid rgba(14,141,230,0.2)' }}
              >
                <Zap className="w-4 h-4" style={{ color: '#0e8de6' }} aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-500">
                  Nodo Activo
                </p>
                <p className="text-sm font-black text-neutral-900 truncate">{deviceCode}</p>
              </div>
            </div>

            {/* Right: MQTT status */}
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-full shrink-0"
              style={{
                background: isConnected ? 'rgba(240,253,244,0.95)' : 'rgba(255,241,242,0.95)',
                border: `1px solid ${isConnected ? 'rgba(187,247,208,0.9)' : 'rgba(254,205,211,0.9)'}`,
              }}
            >
              {/* Pulsing green dot */}
              <span className="relative flex items-center justify-center w-2.5 h-2.5">
                {isConnected && (
                  <motion.span
                    className="absolute inline-flex rounded-full"
                    style={{ background: 'rgba(34,197,94,0.4)', width: '100%', height: '100%' }}
                    animate={{ scale: [1, 2.2, 1], opacity: [0.7, 0, 0.7] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                )}
                <span
                  className="relative inline-flex rounded-full w-2.5 h-2.5"
                  style={{ background: isConnected ? '#22c55e' : '#f43f5e' }}
                />
              </span>
              <div className="flex items-center gap-1">
                <Wifi className="w-3.5 h-3.5" style={{ color: isConnected ? '#166534' : '#9f1239' }} aria-hidden="true" />
                <span
                  className="text-xs font-bold"
                  style={{ color: isConnected ? '#166534' : '#9f1239' }}
                >
                  MQTT {isConnected ? 'OK' : 'OFF'}
                </span>
              </div>
            </div>
          </div>

          {/* Bottom metadata strip */}
          <div
            className="flex items-center gap-4 mt-2 pt-2"
            style={{ borderTop: '1px solid rgba(203,213,225,0.4)' }}
          >
            {[
              { label: 'Lat',  value: NEZA_LAT.toFixed(4) },
              { label: 'Lon',  value: NEZA_LON.toFixed(4) },
              { label: 'Zona', value: 'UTC-6 CDMX' },
            ].map(({ label, value }) => (
              <div key={label} className="flex items-center gap-1">
                <span className="text-[9px] font-bold uppercase tracking-wider text-neutral-400">{label}</span>
                <span className="text-[11px] font-semibold text-neutral-700">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.section>
  );
}
