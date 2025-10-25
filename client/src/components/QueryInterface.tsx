import { useState, useEffect } from 'react';
import { MessageSquare, X, Plus, Brain } from 'lucide-react';
import type {
  QueryResponse,
  QueryResult,
  DatabaseType,
} from '../types/database';
import { processQuery, sendErrorFeedback, sendMessage } from '../services/llm';
import { executeSqlQuery } from '../services/tauri';
import { MetadataApproval } from './MetadataApproval';
import { ResultsViewer } from './ResultsViewer';
import { MessageThread } from './MessageThread';
import { ConversationHistory } from './ConversationHistory';
import { SatisfactionPrompt } from './SatisfactionPrompt';
import { ContextViewer } from './ContextViewer';
import { getConversation, generateConversationTitle, type Message } from '../services/conversations';

interface QueryInterfaceProps {
  databaseId: string;
  databaseName: string;
  dbType: DatabaseType;
  workspaceId?: string;
}

export function QueryInterface({ databaseId, databaseName, dbType, workspaceId }: QueryInterfaceProps) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [pendingMetadataRequest, setPendingMetadataRequest] = useState<QueryResponse | null>(
    null
  );
  const [queryResults, setQueryResults] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [executingMessageId, setExecutingMessageId] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [conversationTitle, setConversationTitle] = useState<string | null>(null);
  const [showSatisfactionPrompt, setShowSatisfactionPrompt] = useState(false);
  const [showContextViewer, setShowContextViewer] = useState(false);

  // Auto mode state
  const [autoMode, setAutoMode] = useState(false);
  const [maxAutoApprovals, setMaxAutoApprovals] = useState(5);
  const [autoApprovalCount, setAutoApprovalCount] = useState(0);

  // Load conversation messages when conversation ID changes
  useEffect(() => {
    const loadMessages = async () => {
      if (!conversationId) {
        setMessages([]);
        setConversationTitle(null);
        setAutoApprovalCount(0); // Reset counter on new conversation
        return;
      }

      setLoadingMessages(true);
      setAutoApprovalCount(0); // Reset counter when switching conversations
      try {
        const conversation = await getConversation(conversationId);
        setMessages(conversation.messages);
        setConversationTitle(conversation.title);
      } catch (err) {
        console.error('Failed to load conversation messages:', err);
      } finally {
        setLoadingMessages(false);
      }
    };

    loadMessages();
  }, [conversationId]);

  // Reload messages after each query/response cycle
  const refreshMessages = async () => {
    if (!conversationId) return;

    try {
      const conversation = await getConversation(conversationId);
      setMessages(conversation.messages);
    } catch (err) {
      console.error('Failed to refresh messages:', err);
    }
  };

  const handleSubmitQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setQueryResults(null);
    setPendingMetadataRequest(null);

    try {
      let response: QueryResponse;

      // If there's an active conversation, send as a follow-up message
      if (conversationId) {
        response = await sendMessage(conversationId, query, databaseId);
      } else {
        // Otherwise, create a new conversation
        response = await processQuery(databaseId, query, conversationId || undefined, workspaceId);
      }

      handleLLMResponse(response);
      // Clear the input after successful submission
      setQuery('');
      // Refresh messages after query processing
      await refreshMessages();
    } catch (err) {
      setError(`Failed to process query: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLLMResponse = (response: QueryResponse) => {
    // Store conversation ID from response
    if (response.conversation_id) {
      setConversationId(response.conversation_id);
    }

    if (response.status === 'needs_metadata') {
      setPendingMetadataRequest(response);
    } else if (response.status === 'error') {
      setError(response.error || 'Unknown error from LLM');
    }
    // Note: SQL queries are now displayed in the conversation thread, not here
  };

  const handleMetadataApproved = async (response: QueryResponse, wasAutoApproved: boolean = false) => {
    setPendingMetadataRequest(null);
    if (wasAutoApproved) {
      setAutoApprovalCount(prev => prev + 1);
    }
    handleLLMResponse(response);
    // Refresh messages after metadata approval
    await refreshMessages();
  };

  const handleExecuteSQL = async (sql: string, messageId: string) => {
    setExecutingMessageId(messageId);
    setError(null);
    setQueryResults(null);
    setShowSatisfactionPrompt(false);

    try {
      const results = await executeSqlQuery(databaseId, sql);
      setQueryResults(results);
      // Show satisfaction prompt after successful query execution
      setShowSatisfactionPrompt(true);
    } catch (err) {
      const errorMessage = String(err);
      setError(errorMessage);

      // Send error feedback to LLM for correction
      if (conversationId) {
        try {
          // Find the original user query from messages
          const userMessage = messages.find(m => m.role === 'user');
          const originalQuery = userMessage?.content || '';

          await sendErrorFeedback(
            databaseId,
            conversationId,
            sql,
            errorMessage,
            originalQuery
          );

          // Refresh messages to show the corrected SQL
          await refreshMessages();
        } catch (feedbackErr) {
          console.error('Failed to send error feedback:', feedbackErr);
        }
      }
    } finally {
      setExecutingMessageId(null);
    }
  };

  const handleNewQuery = () => {
    setQuery('');
    setQueryResults(null);
    setError(null);
    setPendingMetadataRequest(null);
  };

  const handleSelectConversation = async (selectedConversationId: string) => {
    setConversationId(selectedConversationId);
    setShowHistory(false);
    setQueryResults(null);
    setError(null);
    setPendingMetadataRequest(null);
  };

  const handleNewConversation = () => {
    setConversationId(null);
    setMessages([]);
    setConversationTitle(null);
    setQuery('');
    setQueryResults(null);
    setError(null);
    setPendingMetadataRequest(null);
    setShowHistory(false);
    setAutoApprovalCount(0); // Reset auto approval counter
    setShowSatisfactionPrompt(false);
    setShowContextViewer(false);
  };

  const handleSatisfactionSubmitted = async (satisfied: boolean) => {
    if (satisfied && conversationId && !conversationTitle) {
      // Auto-generate title if satisfied and no title yet
      try {
        const title = await generateConversationTitle(conversationId);
        setConversationTitle(title);
      } catch (err) {
        console.error('Failed to generate title:', err);
      }
    }
    // Refresh messages to ensure we have the latest data including context
    await refreshMessages();
  };

  return (
    <div className="relative">
      {/* Conversation History Sidebar */}
      {showHistory && (
        <>
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            onClick={() => setShowHistory(false)}
          />
          <div className="fixed right-0 top-0 bottom-0 w-96 bg-dark-secondary border-l border-dark-border z-50 p-6 overflow-y-auto custom-scrollbar">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">Conversations</h3>
              <button
                onClick={() => setShowHistory(false)}
                className="p-1 hover:bg-dark-hover rounded transition-colors"
                title="Close sidebar"
              >
                <X className="w-5 h-5 text-text-secondary" />
              </button>
            </div>
            <ConversationHistory
              databaseId={databaseId}
              onSelectConversation={handleSelectConversation}
            />
          </div>
        </>
      )}

      {/* Main Content */}
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-dark-border">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-text-primary">{databaseName}</h2>
            {conversationId && (
              <div className="flex items-center gap-2">
                <span className="text-text-tertiary">•</span>
                <span className="text-sm text-text-secondary">
                  {conversationTitle || <span className="italic">Untitled</span>}
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            {/* Auto Mode Controls */}
            <div className="flex items-center gap-3 px-4 py-2 bg-dark-card rounded-lg border border-dark-border">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoMode}
                  onChange={(e) => setAutoMode(e.target.checked)}
                  className="w-4 h-4 rounded border-dark-border bg-dark-secondary text-accent-blue focus:ring-2 focus:ring-accent-blue"
                />
                <span className="text-sm font-medium text-text-primary">Auto Mode</span>
              </label>
              {autoMode && (
                <div className="flex items-center gap-2 pl-2 border-l border-dark-border">
                  <label className="flex items-center gap-1">
                    <span className="text-xs text-text-secondary">Max:</span>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={maxAutoApprovals}
                      onChange={(e) =>
                        setMaxAutoApprovals(Math.min(10, Math.max(1, parseInt(e.target.value) || 5)))
                      }
                      className="input w-14 px-2 py-1 text-sm text-center"
                    />
                  </label>
                  <span className="px-2 py-1 bg-accent-orange/20 text-accent-orange rounded text-sm font-semibold">
                    ({autoApprovalCount}/{maxAutoApprovals})
                  </span>
                </div>
              )}
            </div>

            {workspaceId && (
              <button
                onClick={() => setShowContextViewer(!showContextViewer)}
                className="btn btn-secondary flex items-center gap-2"
                title="View learned context"
              >
                <Brain className="w-4 h-4" />
                Context
              </button>
            )}
            {conversationId && (
              <>
                <button onClick={handleNewConversation} className="btn btn-primary flex items-center gap-2">
                  <Plus className="w-4 h-4" />
                  New Conversation
                </button>
              </>
            )}
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="btn btn-secondary flex items-center gap-2"
            >
              <MessageSquare className="w-4 h-4" />
              {showHistory ? 'Hide History' : 'Show History'}
            </button>
          </div>
        </div>

        {/* Message History with SQL execution */}
        {conversationId && messages.length > 0 && (
          <div>
            <MessageThread
              messages={messages}
              isLoading={loadingMessages || loading}
              onExecuteSQL={handleExecuteSQL}
              executingMessageId={executingMessageId}
              dbType={dbType}
            />
          </div>
        )}

        {/* Query Form */}
        <form onSubmit={handleSubmitQuery} className="space-y-3">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              conversationId
                ? "Send a follow-up message (e.g., 'use the products table instead', 'add a limit of 10')"
                : "Ask a question in natural language (e.g., 'Show me all users who signed up last month')"
            }
            rows={3}
            disabled={loading || !!pendingMetadataRequest}
            className="input resize-none"
          />
          <div className="flex justify-end">
            <button type="submit" disabled={loading || !!pendingMetadataRequest} className="btn btn-primary">
              {loading ? 'Processing...' : conversationId ? 'Send' : 'Ask'}
            </button>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-accent-red/10 border border-accent-red/30 rounded-lg">
            <h3 className="text-lg font-semibold text-accent-red mb-2">Error</h3>
            <pre className="text-sm text-accent-red whitespace-pre-wrap overflow-x-auto">{error}</pre>
          </div>
        )}

        {/* Metadata Approval */}
        {pendingMetadataRequest && pendingMetadataRequest.metadata_request && (
          <MetadataApproval
            databaseId={databaseId}
            conversationId={conversationId || ''}
            originalQuery={query}
            metadataRequest={pendingMetadataRequest.metadata_request}
            onApproved={handleMetadataApproved}
            onRejected={() => {
              setPendingMetadataRequest(null);
              setError('Metadata request was rejected by user');
            }}
            autoMode={autoMode}
            maxAutoApprovals={maxAutoApprovals}
            currentAutoApprovalCount={autoApprovalCount}
          />
        )}

        {/* Satisfaction Prompt */}
        {showSatisfactionPrompt && conversationId && queryResults && (
          <SatisfactionPrompt
            conversationId={conversationId}
            onClose={() => setShowSatisfactionPrompt(false)}
            onSubmitted={handleSatisfactionSubmitted}
          />
        )}

        {/* Query Results */}
        {queryResults && (
          <div className="space-y-4">
            <ResultsViewer results={queryResults} sql={''} dbType={dbType} />
            <div className="flex justify-center">
              <button onClick={handleNewQuery} className="btn btn-secondary">
                New Query
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Context Viewer Sidebar */}
      {showContextViewer && workspaceId != null && (
        <ContextViewer
          workspaceId={workspaceId}
          onClose={() => setShowContextViewer(false)}
        />
      )}
    </div>
  );
}
