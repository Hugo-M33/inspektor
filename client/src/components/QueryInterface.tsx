import { useState, useEffect } from 'react';
import type {
  QueryResponse,
  QueryResult,
} from '../types/database';
import { processQuery, sendErrorFeedback, sendMessage } from '../services/llm';
import { executeSqlQuery } from '../services/tauri';
import { MetadataApproval } from './MetadataApproval';
import { ResultsViewer } from './ResultsViewer';
import { MessageThread } from './MessageThread';
import { ConversationHistory } from './ConversationHistory';
import { getConversation, type Message, type ConversationDetail } from '../services/conversations';

interface QueryInterfaceProps {
  databaseId: string;
  databaseName: string;
}

export function QueryInterface({ databaseId, databaseName }: QueryInterfaceProps) {
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
        response = await processQuery(databaseId, query, conversationId || undefined);
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

    try {
      const results = await executeSqlQuery(databaseId, sql);
      setQueryResults(results);
    } catch (err) {
      const errorMessage = String(err);
      setError(errorMessage);

      // Send error feedback to LLM for correction
      if (conversationId) {
        try {
          // Find the original user query from messages
          const userMessage = messages.find(m => m.role === 'user');
          const originalQuery = userMessage?.content || '';

          const response = await sendErrorFeedback(
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
  };

  return (
    <div className="query-interface">
      <div className="query-interface-container">
        {/* Conversation History Sidebar */}
        {showHistory && (
          <div className="conversation-history-sidebar">
            <div className="sidebar-header">
              <h3>Conversations</h3>
              <button
                onClick={() => setShowHistory(false)}
                className="close-sidebar-btn"
                title="Close sidebar"
              >
                ✕
              </button>
            </div>
            <ConversationHistory
              databaseId={databaseId}
              onSelectConversation={handleSelectConversation}
            />
          </div>
        )}

        {/* Main Content */}
        <div className="query-interface-main">
          <div className="header">
            <div className="header-left">
              <h2>{databaseName}</h2>
              {conversationTitle && (
                <span className="conversation-title-badge">
                  {conversationTitle}
                </span>
              )}
            </div>
            <div className="header-actions">
              {/* Auto Mode Controls */}
              <div className="auto-mode-controls">
                <label className="auto-mode-toggle">
                  <input
                    type="checkbox"
                    checked={autoMode}
                    onChange={(e) => setAutoMode(e.target.checked)}
                  />
                  <span>Auto Mode</span>
                </label>
                {autoMode && (
                  <div className="auto-mode-settings">
                    <label>
                      Max:
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={maxAutoApprovals}
                        onChange={(e) => setMaxAutoApprovals(Math.min(10, Math.max(1, parseInt(e.target.value) || 5)))}
                        style={{ width: '50px', marginLeft: '5px' }}
                      />
                    </label>
                    <span className="auto-approval-counter">
                      ({autoApprovalCount}/{maxAutoApprovals})
                    </span>
                  </div>
                )}
              </div>

              {conversationId && (
                <button onClick={handleNewConversation} className="new-conversation-btn">
                  + New Conversation
                </button>
              )}
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="history-toggle-btn"
              >
                {showHistory ? 'Hide History' : 'Show History'}
              </button>
            </div>
          </div>

          {/* Message History with SQL execution */}
          {conversationId && messages.length > 0 && (
            <div className="conversation-section">
              <MessageThread
                messages={messages}
                isLoading={loadingMessages || loading}
                onExecuteSQL={handleExecuteSQL}
                executingMessageId={executingMessageId}
              />
            </div>
          )}

          <form onSubmit={handleSubmitQuery} className="query-form">
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
            />
            <button
              type="submit"
              disabled={loading || !!pendingMetadataRequest}
            >
              {loading ? 'Processing...' : conversationId ? 'Send' : 'Ask'}
            </button>
          </form>

          {error && (
            <div className="error-message">
              <h3>Error:</h3>
              <pre>{error}</pre>
            </div>
          )}

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

          {queryResults && (
            <div className="results-section">
              <ResultsViewer results={queryResults} sql={''} />
              <button onClick={handleNewQuery} className="new-query-btn">
                New Query
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
