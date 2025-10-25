import { useState, useEffect } from 'react';
import { MessageSquare, Trash2, RefreshCw, Clock } from 'lucide-react';
import {
  listConversations,
  deleteConversation,
  type ConversationSummary,
} from '../services/conversations';
import { ConfirmModal } from './ConfirmModal';

interface ConversationHistoryProps {
  databaseId?: string;
  onSelectConversation?: (conversationId: string) => void;
}

export function ConversationHistory({
  databaseId,
  onSelectConversation,
}: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmModal, setConfirmModal] = useState<{
    message: string;
    onConfirm: () => void;
  } | null>(null);

  useEffect(() => {
    loadConversations();
  }, [databaseId]);

  const loadConversations = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listConversations(databaseId);
      setConversations(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (conversationId: string) => {
    setConfirmModal({
      message: 'Are you sure you want to delete this conversation?',
      onConfirm: async () => {
        try {
          await deleteConversation(conversationId);
          setConversations((prev) => prev.filter((c) => c.id !== conversationId));
          setConfirmModal(null);
        } catch (err) {
          setConfirmModal(null);
          setError(err instanceof Error ? err.message : 'Failed to delete conversation');
        }
      },
    });
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-text-secondary">Loading conversations...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 space-y-3">
        <p className="text-sm text-accent-red">{error}</p>
        <button onClick={loadConversations} className="btn btn-secondary text-sm px-4 py-2">
          Retry
        </button>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="text-center py-8">
        <MessageSquare className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
        <p className="text-sm text-text-secondary px-4">
          No conversations yet. Start asking questions to create your first conversation!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
          History
        </h3>
        <button
          onClick={loadConversations}
          className="p-1 hover:bg-dark-hover rounded transition-colors"
          title="Refresh conversations"
        >
          <RefreshCw className="w-4 h-4 text-text-tertiary hover:text-accent-blue" />
        </button>
      </div>

      {/* Conversation List */}
      <div className="space-y-1">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className="group relative bg-dark-card hover:bg-dark-hover rounded-lg p-3 cursor-pointer transition-colors border border-transparent hover:border-dark-border"
            onClick={() => onSelectConversation?.(conv.id)}
          >
            <div className="flex items-start gap-2 mb-2">
              <MessageSquare className="w-4 h-4 text-accent-blue flex-shrink-0 mt-0.5" />
              <h4 className="text-sm font-medium text-text-primary line-clamp-2 flex-1">
                {conv.title || <span className="italic text-text-tertiary">Untitled</span>}
              </h4>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(conv.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-accent-red/20 rounded transition-all"
                title="Delete conversation"
              >
                <Trash2 className="w-3 h-3 text-accent-red" />
              </button>
            </div>
            <div className="flex items-center gap-3 text-xs text-text-tertiary">
              <span className="flex items-center gap-1">
                <MessageSquare className="w-3 h-3" />
                {conv.message_count}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatDate(conv.updated_at)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Confirm Modal */}
      {confirmModal && (
        <ConfirmModal
          title="Confirm Deletion"
          message={confirmModal.message}
          confirmText="Delete"
          confirmVariant="danger"
          onConfirm={confirmModal.onConfirm}
          onCancel={() => setConfirmModal(null)}
        />
      )}
    </div>
  );
}
