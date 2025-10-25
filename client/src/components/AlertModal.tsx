import { createPortal } from 'react-dom';
import { AlertCircle, CheckCircle, XCircle, X } from 'lucide-react';

interface AlertModalProps {
  title?: string;
  message: string;
  type?: 'info' | 'success' | 'error';
  onClose: () => void;
}

export function AlertModal({ title, message, type = 'info', onClose }: AlertModalProps) {
  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-6 h-6 text-accent-green" />;
      case 'error':
        return <XCircle className="w-6 h-6 text-accent-red" />;
      default:
        return <AlertCircle className="w-6 h-6 text-accent-blue" />;
    }
  };

  const getColors = () => {
    switch (type) {
      case 'success':
        return 'bg-accent-green/10 border-accent-green/30';
      case 'error':
        return 'bg-accent-red/10 border-accent-red/30';
      default:
        return 'bg-accent-blue/10 border-accent-blue/30';
    }
  };

  const modalContent = (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-dark-secondary border border-dark-border rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-start gap-4">
            <div className={`p-2 rounded-lg ${getColors()}`}>
              {getIcon()}
            </div>
            <div className="flex-1 min-w-0">
              {title && (
                <h3 className="text-lg font-semibold text-text-primary mb-2">
                  {title}
                </h3>
              )}
              <p className="text-sm text-text-secondary whitespace-pre-wrap">
                {message}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-dark-hover rounded transition-colors"
            >
              <X className="w-5 h-5 text-text-tertiary" />
            </button>
          </div>
        </div>
        <div className="border-t border-dark-border p-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-accent-blue text-white rounded-lg hover:bg-blue-500 transition-colors"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
