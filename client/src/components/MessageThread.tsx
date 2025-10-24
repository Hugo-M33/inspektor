import { useState } from 'react';
import { User, Bot, Settings, Play, Eye, EyeOff } from 'lucide-react';
import type { Message } from '../services/conversations';

interface MessageThreadProps {
  messages: Message[];
  isLoading?: boolean;
  onExecuteSQL?: (sql: string, messageId: string) => void;
  executingMessageId?: string | null;
}

export function MessageThread({ messages, isLoading, onExecuteSQL, executingMessageId }: MessageThreadProps) {
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());

  const toggleExpanded = (messageId: string) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;

    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const renderMessageContent = (message: Message) => {
    const isExpanded = expandedMessages.has(message.id);
    const hasMetadata = message.metadata && Object.keys(message.metadata).length > 0;

    const roleConfig = {
      user: { icon: User, label: 'You', color: 'text-accent-blue', bg: 'bg-accent-blue/10', border: 'border-accent-blue/30' },
      assistant: { icon: Bot, label: 'Assistant', color: 'text-accent-purple', bg: 'bg-accent-purple/10', border: 'border-accent-purple/30' },
      system: { icon: Settings, label: 'System', color: 'text-accent-orange', bg: 'bg-accent-orange/10', border: 'border-accent-orange/30' },
    };

    const config = roleConfig[message.role as keyof typeof roleConfig] || roleConfig.system;
    const Icon = config.icon;

    return (
      <div className={`${config.bg} border ${config.border} rounded-lg p-4 transition-all`} key={message.id}>
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <Icon className={`w-4 h-4 ${config.color}`} />
            <span className={`text-sm font-semibold ${config.color}`}>{config.label}</span>
          </div>
          <span className="text-xs text-text-tertiary">{formatTimestamp(message.timestamp)}</span>
        </div>

        <div className="text-text-primary leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>

        {hasMetadata && (
          <div className="mt-3 pt-3 border-t border-dark-border/50 space-y-3">
            {message.metadata.sql && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <strong className="text-sm text-text-secondary">
                      SQL Query{message.metadata.is_retry ? ' (Corrected)' : ''}
                    </strong>
                    {message.metadata.is_retry && (
                      <span className="px-2 py-0.5 bg-accent-orange/20 text-accent-orange text-xs rounded">
                        Retry
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleExpanded(message.id)}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-dark-card hover:bg-dark-hover border border-dark-border rounded transition-colors"
                    >
                      {isExpanded ? <><EyeOff className="w-3 h-3" /> Hide</> : <><Eye className="w-3 h-3" /> Show</>}
                    </button>
                    {onExecuteSQL && (
                      <button
                        onClick={() => onExecuteSQL(message.metadata.sql, message.id)}
                        disabled={executingMessageId === message.id}
                        className="btn-success flex items-center gap-1 px-3 py-1 text-xs"
                      >
                        <Play className="w-3 h-3" />
                        {executingMessageId === message.id ? 'Executing...' : 'Execute'}
                      </button>
                    )}
                  </div>
                </div>
                {isExpanded && (
                  <pre className="bg-dark-primary text-text-primary p-3 rounded border border-dark-border overflow-x-auto text-xs font-mono">
                    {message.metadata.sql}
                  </pre>
                )}
              </div>
            )}

            {message.metadata.metadata_request && (
              <div className="text-sm">
                <strong className="text-text-secondary">Metadata Request:</strong>{' '}
                <span className="text-text-tertiary">{message.metadata.metadata_request.metadata_type}</span>
                {message.metadata.metadata_request.reason && (
                  <p className="text-text-tertiary italic mt-1">{message.metadata.metadata_request.reason}</p>
                )}
              </div>
            )}

            {message.metadata.failed_sql && (
              <div>
                <strong className="text-sm text-accent-red">Failed SQL:</strong>
                <pre className="bg-accent-red/10 border border-accent-red/30 text-accent-red p-3 rounded overflow-x-auto text-xs font-mono mt-2">
                  {message.metadata.failed_sql}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="text-center py-8">
        <Bot className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
        <p className="text-text-secondary">No messages yet. Start a conversation!</p>
      </div>
    );
  }

  return (
    <div className="bg-dark-secondary/30 rounded-lg p-4 max-h-[500px] overflow-y-auto custom-scrollbar space-y-3">
      {messages.map((message) => renderMessageContent(message))}
      {isLoading && (
        <div className="bg-dark-card/50 border border-dark-border rounded-lg p-4 animate-pulse">
          <div className="flex items-center gap-2 mb-2">
            <Bot className="w-4 h-4 text-accent-purple" />
            <span className="text-sm font-semibold text-accent-purple">Assistant</span>
          </div>
          <div className="text-text-secondary">
            Thinking...
          </div>
        </div>
      )}
    </div>
  );
}
