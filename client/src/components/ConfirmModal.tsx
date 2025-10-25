import { createPortal } from 'react-dom';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmModalProps {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  confirmVariant?: 'primary' | 'danger';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  title = 'Confirm',
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'primary',
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const getConfirmButtonClasses = () => {
    if (confirmVariant === 'danger') {
      return 'px-4 py-2 bg-accent-red text-white rounded-lg hover:bg-red-600 transition-colors';
    }
    return 'px-4 py-2 bg-accent-blue text-white rounded-lg hover:bg-blue-500 transition-colors';
  };

  const modalContent = (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-dark-secondary border border-dark-border rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-start gap-4">
            <div className={`p-2 rounded-lg ${
              confirmVariant === 'danger'
                ? 'bg-accent-red/10 border-accent-red/30'
                : 'bg-accent-orange/10 border-accent-orange/30'
            }`}>
              <AlertTriangle className={`w-6 h-6 ${
                confirmVariant === 'danger' ? 'text-accent-red' : 'text-accent-orange'
              }`} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                {title}
              </h3>
              <p className="text-sm text-text-secondary whitespace-pre-wrap">
                {message}
              </p>
            </div>
            <button
              onClick={onCancel}
              className="p-1 hover:bg-dark-hover rounded transition-colors"
            >
              <X className="w-5 h-5 text-text-tertiary" />
            </button>
          </div>
        </div>
        <div className="border-t border-dark-border p-4 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-dark-card text-text-secondary border border-dark-border rounded-lg hover:bg-dark-hover transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={getConfirmButtonClasses()}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
