import { useState, FormEvent } from 'react';
import { Shield } from 'lucide-react';
import { register, type User } from '../services/auth';

interface RegisterProps {
  onRegister: (user: User) => void;
  onSwitchToLogin: () => void;
}

export function Register({ onRegister, onSwitchToLogin }: RegisterProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate passwords match
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Validate password strength
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      const response = await register(email, password);
      onRegister(response.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
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
              <button
                onClick={onSwitchToLogin}
                disabled={loading}
                className="px-6 py-2 bg-transparent text-text-secondary hover:text-text-primary rounded-lg font-medium transition-colors"
              >
                Login
              </button>
              <button className="px-6 py-2 bg-accent-blue text-white rounded-lg font-medium">
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
                placeholder="your@email.com"
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
                autoComplete="new-password"
                placeholder="At least 8 characters"
                disabled={loading}
                minLength={8}
                className="input"
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-text-secondary mb-2">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Re-enter your password"
                disabled={loading}
                minLength={8}
                className="input"
              />
            </div>

            <div className="pt-2">
              <button type="submit" className="btn btn-primary w-full" disabled={loading}>
                {loading ? 'Creating account...' : 'Create Account'}
              </button>
            </div>
          </form>

          <p className="text-center text-sm text-text-tertiary mt-6">
            Secure by default. Your credentials are never shared.
          </p>
        </div>
      </div>
    </div>
  );
}
