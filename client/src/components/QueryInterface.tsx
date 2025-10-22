import { useState } from 'react';
import type {
  QueryResponse,
  ConversationMessage,
  QueryResult,
} from '../types/database';
import { processQuery, sendErrorFeedback } from '../services/llm';
import { executeSqlQuery } from '../services/tauri';
import { MetadataApproval } from './MetadataApproval';
import { ResultsViewer } from './ResultsViewer';

interface QueryInterfaceProps {
  databaseId: string;
  databaseName: string;
}

export function QueryInterface({ databaseId, databaseName }: QueryInterfaceProps) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [pendingMetadataRequest, setPendingMetadataRequest] = useState<QueryResponse | null>(
    null
  );
  const [generatedSQL, setGeneratedSQL] = useState<string | null>(null);
  const [sqlExplanation, setSqlExplanation] = useState<string | null>(null);
  const [queryResults, setQueryResults] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmitQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setQueryResults(null);
    setPendingMetadataRequest(null);
    setGeneratedSQL(null);

    const newConversation: ConversationMessage[] = [
      ...conversation,
      { role: 'user', content: query },
    ];
    setConversation(newConversation);

    try {
      const response = await processQuery(databaseId, query, newConversation);
      handleLLMResponse(response);
    } catch (err) {
      setError(`Failed to process query: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLLMResponse = (response: QueryResponse) => {
    if (response.status === 'needs_metadata') {
      setPendingMetadataRequest(response);
    } else if (response.status === 'ready' && response.sql_response) {
      setGeneratedSQL(response.sql_response.sql);
      setSqlExplanation(response.sql_response.explanation);
    } else if (response.status === 'error') {
      setError(response.error || 'Unknown error from LLM');
    }
  };

  const handleMetadataApproved = (response: QueryResponse) => {
    setPendingMetadataRequest(null);
    handleLLMResponse(response);
  };

  const handleExecuteSQL = async () => {
    if (!generatedSQL) return;

    setLoading(true);
    setError(null);

    try {
      const results = await executeSqlQuery(databaseId, generatedSQL);
      setQueryResults(results);
    } catch (err) {
      const errorMessage = String(err);
      setError(errorMessage);

      // Send error feedback to LLM for correction
      try {
        const response = await sendErrorFeedback(
          databaseId,
          generatedSQL,
          errorMessage,
          query
        );
        handleLLMResponse(response);
      } catch (feedbackErr) {
        console.error('Failed to send error feedback:', feedbackErr);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleNewQuery = () => {
    setQuery('');
    setGeneratedSQL(null);
    setSqlExplanation(null);
    setQueryResults(null);
    setError(null);
    setPendingMetadataRequest(null);
  };

  return (
    <div className="query-interface">
      <div className="header">
        <h2>Query: {databaseName}</h2>
      </div>

      <form onSubmit={handleSubmitQuery} className="query-form">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question in natural language (e.g., 'Show me all users who signed up last month')"
          rows={3}
          disabled={loading || !!pendingMetadataRequest || !!generatedSQL}
        />
        <button
          type="submit"
          disabled={loading || !!pendingMetadataRequest || !!generatedSQL}
        >
          {loading ? 'Processing...' : 'Ask'}
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
          metadataRequest={pendingMetadataRequest.metadata_request}
          onApproved={handleMetadataApproved}
          onRejected={() => {
            setPendingMetadataRequest(null);
            setError('Metadata request was rejected by user');
          }}
        />
      )}

      {generatedSQL && !queryResults && (
        <div className="sql-preview">
          <h3>Generated SQL</h3>
          {sqlExplanation && <p className="explanation">{sqlExplanation}</p>}
          <pre className="sql-code">{generatedSQL}</pre>
          <div className="actions">
            <button onClick={handleExecuteSQL} disabled={loading}>
              {loading ? 'Executing...' : 'Execute Query'}
            </button>
            <button onClick={handleNewQuery} className="secondary">
              Cancel
            </button>
          </div>
        </div>
      )}

      {queryResults && (
        <div className="results-section">
          <ResultsViewer results={queryResults} sql={generatedSQL!} />
          <button onClick={handleNewQuery} className="new-query-btn">
            New Query
          </button>
        </div>
      )}
    </div>
  );
}
