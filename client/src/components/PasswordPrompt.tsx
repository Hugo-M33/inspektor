import { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Lock, Key } from 'lucide-react';

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
    <Transition appear show={true} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={() => !isLoading && onCancel()}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-dark-card border border-dark-border shadow-2xl transition-all">
                <div className="p-6">
                  {/* Header */}
                  <div className="flex items-start gap-4 mb-4">
                    <div className="p-3 rounded-full bg-accent-blue/20">
                      <Lock className="w-6 h-6 text-accent-blue" />
                    </div>
                    <div className="flex-1">
                      <Dialog.Title className="text-lg font-semibold text-text-primary">
                        {title}
                      </Dialog.Title>
                      <p className="text-sm text-text-secondary mt-1">{message}</p>
                    </div>
                  </div>

                  {/* Form */}
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-2">
                        Password
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <Key className="w-4 h-4 text-text-tertiary" />
                        </div>
                        <input
                          id="password"
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="Enter your password"
                          autoFocus
                          disabled={isLoading}
                          className="input pl-10"
                        />
                      </div>
                    </div>

                    {error && (
                      <div className="p-3 bg-accent-red/10 border border-accent-red/30 rounded-lg">
                        <p className="text-sm text-accent-red">{error}</p>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-3 pt-2">
                      <button
                        type="submit"
                        disabled={isLoading || !password}
                        className="btn btn-primary flex-1"
                      >
                        {isLoading ? 'Processing...' : 'Submit'}
                      </button>
                      <button
                        type="button"
                        onClick={onCancel}
                        disabled={isLoading}
                        className="btn btn-secondary px-6"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
