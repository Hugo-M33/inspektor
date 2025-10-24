import { useState } from 'react';
import './PasswordPrompt.css';

interface PasswordPromptProps {
  title: string;
  message: string;
  onSubmit: (password: string) => void | Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export function PasswordPrompt({
  title,
  message,
  onSubmit,
  onCancel,
  isLoading = false,
}: PasswordPromptProps) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!password) {
      setError('Password is required');
      return;
    }

    setError(null);
    try {
      await onSubmit(password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid password');
    }
  };

  return (
    <div className="password-prompt-overlay">
      <div className="password-prompt-modal">
        <h2>{title}</h2>
        <p className="password-prompt-message">{message}</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoFocus
              disabled={isLoading}
            />
          </div>

          {error && <div className="error-text">{error}</div>}

          <div className="password-prompt-actions">
            <button type="submit" disabled={isLoading || !password}>
              {isLoading ? 'Processing...' : 'Submit'}
            </button>
            <button type="button" onClick={onCancel} className="secondary" disabled={isLoading}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
