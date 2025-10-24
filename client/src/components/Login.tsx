import { useState, FormEvent } from 'react';
import { Shield } from 'lucide-react';
import { login, type User } from '../services/auth';

interface LoginProps {
  onLogin: (user: User) => void;
  onSwitchToRegister: () => void;
}

export function Login({ onLogin, onSwitchToRegister }: LoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await login(email, password);
      onLogin(response.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-primary p-4">
      <div className="w-full max-w-md">
        <div className="bg-dark-card rounded-2xl shadow-2xl p-8 border border-dark-border">
          {/* Logo and Title */}
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <div className="bg-accent-blue/10 p-4 rounded-full">
                <Shield className="w-12 h-12 text-accent-blue" strokeWidth={1.5} />
              </div>
            </div>
            <h1 className="text-3xl font-bold text-text-primary mb-2">Inspektor</h1>
            <div className="flex justify-center gap-2 mb-6">
              <button className="px-6 py-2 bg-accent-blue text-white rounded-lg font-medium">
                Login
              </button>
              <button
                onClick={onSwitchToRegister}
                disabled={loading}
                className="px-6 py-2 bg-transparent text-text-secondary hover:text-text-primary rounded-lg font-medium transition-colors"
              >
                Register
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-accent-red/10 border border-accent-red/30 rounded-lg">
              <p className="text-sm text-accent-red">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="admin@inspektor.io"
                disabled={loading}
                className="input"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                disabled={loading}
                className="input"
              />
            </div>

            <div className="pt-2">
              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </div>

            <button
              type="button"
              className="btn-secondary w-full"
              disabled={loading}
            >
              Use SSO
            </button>
          </form>

          <p className="text-center text-sm text-text-tertiary mt-6">
            Secure by default. Your credentials are never shared.
          </p>
        </div>
      </div>
    </div>
  );
}
