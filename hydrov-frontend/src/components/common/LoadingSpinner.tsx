import { motion } from 'framer-motion';
import { Droplets } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
}

export function LoadingSpinner({ message = 'Conectando con tu dispositivo…' }: LoadingSpinnerProps) {
  return (
    <div
      className="flex flex-col items-center justify-center min-h-dvh bg-gradient-to-br from-brand-50 via-white to-blue-50 gap-6 px-6"
      role="status"
      aria-live="polite"
      aria-label={message}
    >
      {/* Animated logo */}
      <motion.div
        className="relative flex items-center justify-center w-24 h-24 rounded-3xl bg-brand-500 shadow-btn-lg"
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      >
        <Droplets className="w-12 h-12 text-white" aria-hidden="true" />

        {/* Ripple rings */}
        {[1, 2].map((i) => (
          <motion.span
            key={i}
            className="absolute inset-0 rounded-3xl border-2 border-brand-400"
            animate={{ scale: [1, 1.8], opacity: [0.5, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut', delay: i * 0.7 }}
          />
        ))}
      </motion.div>

      <div className="text-center space-y-2">
        <h2 className="text-3xl font-black text-neutral-900">Hydro-V</h2>
        <p className="text-lg text-neutral-500 font-medium">{message}</p>
      </div>

      {/* Friendly progress dots */}
      <div className="flex items-center gap-2" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="w-2.5 h-2.5 rounded-full bg-brand-400"
            animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
      </div>
    </div>
  );
}
