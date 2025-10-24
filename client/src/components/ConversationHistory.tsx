import { useState, useEffect } from 'react';
import {
  listConversations,
  deleteConversation,
  type ConversationSummary,
} from '../services/conversations';

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

  const handleDelete = async (conversationId: string) => {
    if (!confirm('Are you sure you want to delete this conversation?')) {
      return;
    }

    try {
      await deleteConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete conversation');
    }
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
    return <div className="conversation-history loading">Loading conversations...</div>;
  }

  if (error) {
    return (
      <div className="conversation-history error">
        <p>{error}</p>
        <button onClick={loadConversations}>Retry</button>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="conversation-history empty">
        <p>No conversations yet. Start asking questions to create your first conversation!</p>
      </div>
    );
  }

  return (
    <div className="conversation-history">
      <div className="history-header">
        <h3>Conversation History</h3>
        <button onClick={loadConversations} className="refresh-button">
          Refresh
        </button>
      </div>

      <div className="conversation-list">
        {conversations.map((conv) => (
          <div key={conv.id} className="conversation-item">
            <div
              className="conversation-info"
              onClick={() => onSelectConversation?.(conv.id)}
            >
              <h4 className="conversation-title">{conv.title}</h4>
              <div className="conversation-meta">
                <span className="message-count">{conv.message_count} messages</span>
                <span className="conversation-date">{formatDate(conv.updated_at)}</span>
              </div>
            </div>

            <button
              className="delete-button"
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(conv.id);
              }}
              title="Delete conversation"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
