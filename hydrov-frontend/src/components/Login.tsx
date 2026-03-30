import { useState } from 'react';
import { motion } from 'framer-motion';
import { Droplets, Lock, Mail, ArrowRight, ShieldCheck, AlertCircle } from 'lucide-react';

interface LoginProps {
  onLogin: (email: string, deviceCode: string) => void;
}

export function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    // Validar correo
    if (!email.includes('@') || !email.includes('.')) {
      setError('Por favor escribe un correo electrónico válido.');
      return;
    }

    // Validar contraseña vacía
    if (!password) {
      setError('Por favor ingresa tu contraseña.');
      return;
    }

    setLoading(true);
    
    try {
      // El backend de Hydro-V espera un JSON con 'email' y 'password' 
      // basado en el UserLoginSchema, en lugar de un OAuth2PasswordRequestForm.
      const payload = {
        email: email,
        password: password,
      };

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        // Manejo seguro de errores para evitar que React explote con objetos (Ej. Error 422 Pydantic)
        let errorMsg = 'Credenciales inválidas. Verifica tu correo y contraseña.';
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMsg = data.detail;
          } else if (Array.isArray(data.detail) && data.detail.length > 0) {
            errorMsg = data.detail[0].msg || errorMsg;
          }
        }
        setError(errorMsg);
        setLoading(false);
        return;
      }

      // Guardar token JWT en memoria del navegador
      localStorage.setItem('hydrov_access_token', data.access_token);
      
      setLoading(false);
      // Hardcodeamos el device ID para el Dashboard temporalmente
      onLogin(email, 'HYDRO-V-NEZA-001');

    } catch (err) {
      console.error(err);
      setError('Error de conexión con el servidor. Intenta de nuevo más tarde.');
      setLoading(false);
    }
  }

  return (
    <div className="min-h-dvh flex flex-col bg-gradient-to-br from-brand-50 via-white to-blue-50">

      {/* Top branding bar */}
      <header className="flex items-center justify-center pt-10 pb-4">
        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-500 shadow-btn">
            <Droplets className="w-7 h-7 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-neutral-900 leading-none">Hydro-V</h1>
            <p className="text-sm text-brand-600 font-medium">Tu agua, bajo control</p>
          </div>
        </motion.div>
      </header>

      {/* Main card */}
      <main className="flex-1 flex items-start justify-center px-5 pt-6 pb-10">
        <motion.div
          className="w-full max-w-md"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <div className="card p-7 md:p-9">

            {/* Card header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-50 border-2 border-brand-100 mb-4">
                <ShieldCheck className="w-8 h-8 text-brand-500" />
              </div>
              <h2 className="text-2xl font-bold text-neutral-900">Bienvenido de vuelta</h2>
              <p className="text-base text-neutral-500 mt-2 leading-relaxed">
                Ingresa tus credenciales para acceder a tu panel de control Hydro-V.
              </p>
            </div>

            {/* Error message */}
            {error && (
              <motion.div
                className="flex items-start gap-3 p-4 rounded-xl bg-danger-bg border border-danger-border mb-6"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                role="alert"
                aria-live="polite"
              >
                <AlertCircle className="w-5 h-5 text-danger-icon mt-0.5 shrink-0" />
                <p className="text-sm font-medium text-danger-text">{error}</p>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-5">

              {/* Email */}
              <div className="space-y-2">
                <label htmlFor="login-email" className="block text-base font-semibold text-neutral-800">
                  Correo electrónico
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 pointer-events-none" />
                  <input
                    id="login-email"
                    type="email"
                    inputMode="email"
                    autoComplete="email"
                    required
                    placeholder="tucorreo@ejemplo.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input-field pl-12"
                    aria-describedby="email-hint"
                  />
                </div>
                <p id="email-hint" className="text-sm text-neutral-500">
                  El correo que usaste para registrar tu cuenta.
                </p>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label htmlFor="login-password" className="block text-base font-semibold text-neutral-800">
                  Contraseña
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 pointer-events-none" />
                  <input
                    id="login-password"
                    type="password"
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-field pl-12 tracking-wide"
                  />
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full mt-2"
                aria-busy={loading}
              >
                {loading ? (
                  <>
                    <PairingSpinner />
                    Vinculando dispositivo…
                  </>
                ) : (
                  <>
                    Entrar al panel
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>
            </form>

            {/* Help text */}
            <div className="mt-6 pt-6 border-t border-neutral-200 text-center">
              <p className="text-sm text-neutral-500">
                ¿Olvidaste tu contraseña?{' '}
                <button className="text-brand-600 font-semibold underline underline-offset-2 hover:text-brand-700">
                  Recuperar acceso
                </button>
              </p>
            </div>
          </div>

          {/* Trust badges */}
          <div className="flex items-center justify-center gap-6 mt-6 text-sm text-neutral-500">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-success-icon" />
              Conexión segura
            </span>
            <span className="text-neutral-300">·</span>
            <span className="flex items-center gap-1.5">
              <Droplets className="w-4 h-4 text-brand-400" />
              Datos cifrados
            </span>
          </div>
        </motion.div>
      </main>
    </div>
  );
}

// Small inline spinner for the button loading state
function PairingSpinner() {
  return (
    <svg
      className="animate-spin w-5 h-5 text-white shrink-0"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}
