import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ShieldAlert, Radar, MapPin, Clock, ActivitySquare } from 'lucide-react';
import type { LeakStatus } from '@/types/telemetry.types';

interface LeakRadarProps {
  leak: LeakStatus;
}

export function LeakRadar({ leak }: LeakRadarProps) {
  const { status, confidence, location_hint, last_checked } = leak;
  const isStable = status === 'stable';
  const isLeaking = status === 'leak_detected';

  const timeStr = new Date(last_checked).toLocaleTimeString('es-MX', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  return (
    <motion.div
      className={`glass-card p-5 flex flex-col gap-4 relative overflow-hidden transition-all duration-700 ${
        isLeaking ? 'border-neon-red/30' : 'border-neon-blue/10'
      }`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      {/* Leak alert pulsing background overlay */}
      <AnimatePresence>
        {isLeaking && (
          <motion.div
            className="absolute inset-0 bg-neon-red/5 pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0.3, 0.08, 0.3] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="flex items-center justify-between relative z-10">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg border transition-colors duration-500 ${
            isLeaking ? 'bg-neon-red/10 border-neon-red/30' : 'bg-neon-green/10 border-neon-green/20'
          }`}>
            {isLeaking ? (
              <ShieldAlert className="w-4 h-4 text-neon-red" />
            ) : (
              <Shield className="w-4 h-4 text-neon-green" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Radar de Fugas · GNN</h3>
            <p className="text-[10px] font-mono text-slate-500">Graph Neural Network Detection</p>
          </div>
        </div>

        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-mono font-bold transition-colors duration-500 ${
          isLeaking
            ? 'bg-neon-red/10 border-neon-red/30 text-neon-red'
            : 'bg-neon-green/10 border-neon-green/20 text-neon-green'
        }`}>
          <motion.div
            className={`w-1.5 h-1.5 rounded-full ${isLeaking ? 'bg-neon-red' : 'bg-neon-green'}`}
            animate={{ opacity: isLeaking ? [1, 0.2, 1] : 1, scale: isLeaking ? [1, 1.3, 1] : 1 }}
            transition={{ duration: 1, repeat: Infinity }}
          />
          {isLeaking ? 'FUGA DETECTADA' : 'RED ESTABLE'}
        </div>
      </div>

      {/* Radar animation */}
      <div className="flex items-center justify-center py-2">
        <div className="relative w-40 h-40">
          {/* Radar rings */}
          {[40, 60, 80].map((size, i) => (
            <motion.div
              key={size}
              className={`absolute rounded-full border ${
                isLeaking ? 'border-neon-red/20' : 'border-neon-blue/15'
              }`}
              style={{
                width: size,
                height: size,
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
              }}
              animate={isLeaking ? {
                scale: [1, 1.08, 1],
                opacity: [0.5, 1, 0.5],
              } : {}}
              transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}

          {/* Radar sweep */}
          <motion.div
            className="absolute inset-0 rounded-full overflow-hidden"
          >
            <motion.div
              className={`absolute inset-0 origin-center ${
                isLeaking ? 'opacity-60' : 'opacity-30'
              }`}
              style={{
                background: `conic-gradient(${
                  isLeaking ? 'rgba(255,0,64,0.3)' : 'rgba(0,212,255,0.3)'
                } 0deg, transparent 90deg, transparent 360deg)`,
              }}
              animate={{ rotate: 360 }}
              transition={{
                duration: isLeaking ? 1.5 : 3,
                repeat: Infinity,
                ease: 'linear',
              }}
            />
          </motion.div>

          {/* Center dot */}
          <motion.div
            className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 rounded-full border-2 ${
              isLeaking ? 'bg-neon-red/30 border-neon-red' : 'bg-neon-blue/30 border-neon-blue'
            }`}
            animate={isLeaking ? {
              boxShadow: [
                '0 0 5px rgba(255,0,64,0.3)',
                '0 0 25px rgba(255,0,64,0.8)',
                '0 0 5px rgba(255,0,64,0.3)',
              ],
            } : {
              boxShadow: [
                '0 0 5px rgba(0,212,255,0.2)',
                '0 0 15px rgba(0,212,255,0.5)',
                '0 0 5px rgba(0,212,255,0.2)',
              ],
            }}
            transition={{ duration: isLeaking ? 1 : 2.5, repeat: Infinity }}
          />

          {/* Leak blip when detected */}
          <AnimatePresence>
            {isLeaking && (
              <motion.div
                className="absolute w-3 h-3 rounded-full bg-neon-red border border-neon-red/60"
                style={{ top: '30%', left: '65%' }}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: [0, 1.5, 1], opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                transition={{ duration: 0.5 }}
              >
                <motion.div
                  className="absolute inset-[-4px] rounded-full border border-neon-red/50"
                  animate={{ scale: [1, 2], opacity: [0.8, 0] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Stable shield icon */}
          <AnimatePresence>
            {isStable && (
              <motion.div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 0.12, scale: 1 }}
                exit={{ opacity: 0 }}
              >
                <Radar className="w-20 h-20 text-neon-blue" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-2 gap-3 relative z-10">
        {/* GNN Confidence */}
        <div className="p-3 rounded-xl bg-dark-600/40 border border-dark-500/30 space-y-2">
          <div className="flex items-center gap-1.5">
            <ActivitySquare className="w-3 h-3 text-slate-500" />
            <span className="text-[10px] font-mono text-slate-500 uppercase">Confianza GNN</span>
          </div>
          <p className={`text-lg font-bold font-mono ${isLeaking ? 'text-neon-red' : 'text-neon-green'}`}>
            {(confidence * 100).toFixed(1)}
            <span className="text-xs text-slate-400 ml-0.5">%</span>
          </p>
          <div className="h-1 bg-dark-700 rounded-full overflow-hidden">
            <motion.div
              className={`h-full rounded-full ${isLeaking ? 'bg-neon-red' : 'bg-neon-green'}`}
              animate={{ width: `${confidence * 100}%` }}
              transition={{ duration: 0.8 }}
            />
          </div>
        </div>

        {/* Last check time */}
        <div className="p-3 rounded-xl bg-dark-600/40 border border-dark-500/30 space-y-2">
          <div className="flex items-center gap-1.5">
            <Clock className="w-3 h-3 text-slate-500" />
            <span className="text-[10px] font-mono text-slate-500 uppercase">Último Scan</span>
          </div>
          <p className="text-xs font-bold font-mono text-white">{timeStr}</p>
          <p className="text-[9px] font-mono text-slate-600">Análisis continuo activo</p>
        </div>

        {/* Location hint (when leaking) */}
        <AnimatePresence>
          {isLeaking && location_hint && (
            <motion.div
              className="col-span-2 p-3 rounded-xl bg-neon-red/10 border border-neon-red/30 space-y-1"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <div className="flex items-center gap-1.5">
                <MapPin className="w-3 h-3 text-neon-red" />
                <span className="text-[10px] font-mono text-neon-red uppercase font-bold">Ubicación Probable</span>
              </div>
              <p className="text-xs font-mono text-white">{location_hint}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
