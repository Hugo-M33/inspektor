import { useState } from 'react';
import type {
  QueryResult,
  DatabaseCredentials,
} from '../types/database';
import { processQueryImproved, sendErrorFeedbackImproved } from '../services/llm-improved';
import { executeSqlQuery, getCredentials } from '../services/tauri';
import { ResultsViewer } from './ResultsViewer';

interface QueryInterfaceImprovedProps {
  databaseId: string;
  databaseName: string;
}

export function QueryInterfaceImproved({
  databaseId,
  databaseName,
}: QueryInterfaceImprovedProps) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [credentials, setCredentials] = useState<DatabaseCredentials | null>(null);
  const [generatedSQL, setGeneratedSQL] = useState<string | null>(null);
  const [sqlExplanation, setSqlExplanation] = useState<string | null>(null);
  const [queryResults, setQueryResults] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failedSQL, setFailedSQL] = useState<string | null>(null);

  // Load credentials on mount
  useState(() => {
    getCredentials(databaseId)
      .then(setCredentials)
      .catch((err) => setError(`Failed to load credentials: ${err}`));
  });

  const handleSubmitQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !credentials) return;

    setLoading(true);
    setError(null);
    setQueryResults(null);
    setGeneratedSQL(null);

    try {
      // Send query to LLM agent
      // The agent will automatically use LangChain's SQLDatabase to:
      // 1. Cache the database schema
      // 2. Use SQL tools to explore the schema as needed
      // 3. Generate the final SQL query
      // All without manual metadata approval!
      const response = await processQueryImproved(databaseId, query, credentials);

      if (response.status === 'ready' && response.sql_response) {
        setGeneratedSQL(response.sql_response.sql);
        setSqlExplanation(response.sql_response.explanation);
      } else if (response.status === 'error') {
        setError(response.error || 'Unknown error from LLM');
        // If there's a failed SQL in the error response, show it
        if (response.failed_sql) {
          setFailedSQL(response.failed_sql);
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(`Failed to process query: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteSQL = async () => {
    if (!generatedSQL) return;

    setLoading(true);
    setError(null);
    setFailedSQL(null);

    try {
      const results = await executeSqlQuery(databaseId, generatedSQL);
      setQueryResults(results);
    } catch (err) {
      const errorMessage = String(err);
      setError(errorMessage);
      setFailedSQL(generatedSQL); // Store the SQL that failed

      // Send error feedback to LLM for correction
      if (credentials) {
        try {
          const response = await sendErrorFeedbackImproved(
            databaseId,
            generatedSQL,
            errorMessage,
            query,
            credentials
          );

          if (response.status === 'ready' && response.sql_response) {
            setGeneratedSQL(response.sql_response.sql);
            setSqlExplanation(response.sql_response.explanation);
            setError(
              `Previous query failed. Here's a corrected version:\n${errorMessage}`
            );
          } else if (response.status === 'error') {
            // Error correction failed - show the error to user
            const correctionError = response.error || 'Could not generate corrected query';
            setError(`${errorMessage}\n\nError correction failed: ${correctionError}`);
            if (response.failed_sql) {
              setFailedSQL(response.failed_sql);
            }
          }
        } catch (feedbackErr) {
          const feedbackErrorMsg = feedbackErr instanceof Error ? feedbackErr.message : String(feedbackErr);
          setError(`${errorMessage}\n\nFailed to send error feedback: ${feedbackErrorMsg}`);
        }
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
    setFailedSQL(null);
  };

  return (
    <div className="query-interface">
      <div className="header">
        <h2>Query: {databaseName}</h2>
        <p className="info-text">
          Powered by LangChain SQL Agent with automatic schema caching
        </p>
      </div>

      <form onSubmit={handleSubmitQuery} className="query-form">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question in natural language (e.g., 'Show me all users who signed up last month')"
          rows={3}
          disabled={loading || !!generatedSQL}
        />
        <button type="submit" disabled={loading || !!generatedSQL || !credentials}>
          {loading ? 'Processing...' : 'Ask'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <h3>⚠️ Query Execution Failed</h3>
          <div className="error-details">
            <div className="error-section">
              <h4>Error Message:</h4>
              <pre className="error-text">{error}</pre>
            </div>
            {failedSQL && (
              <div className="error-section">
                <h4>Failed SQL Query:</h4>
                <pre className="sql-code error-sql">{failedSQL}</pre>
              </div>
            )}
            <div className="error-meta">
              <span className="error-timestamp">
                Failed at: {new Date().toLocaleString()}
              </span>
              <span className="error-db">
                Database: {databaseName}
              </span>
            </div>
          </div>
        </div>
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
          <ResultsViewer results={queryResults} sql={generatedSQL!} dbType={credentials?.db_type || 'postgres'} />
          <button onClick={handleNewQuery} className="new-query-btn">
            New Query
          </button>
        </div>
      )}

      <div className="info-panel">
        <h4>How it works:</h4>
        <ul>
          <li>The LLM agent automatically explores your database schema</li>
          <li>Schema is cached for faster subsequent queries</li>
          <li>No manual metadata approval needed</li>
          <li>Agent uses LangChain's SQL toolkit for intelligent querying</li>
        </ul>
      </div>
    </div>
  );
}
