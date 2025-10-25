import type {
  QueryResponse,
  DatabaseCredentials,
} from '../types/database';

const API_BASE_URL = 'http://127.0.0.1:8000';

/**
 * Convert DatabaseCredentials to connection object for the server
 */
function buildConnectionObject(credentials: DatabaseCredentials) {
  return {
    db_type: credentials.db_type,
    host: credentials.host,
    port: credentials.port,
    database: credentials.database,
    username: credentials.username,
    password: credentials.password,
    file_path: credentials.file_path,
    schema: credentials.schema,
  };
}

/**
 * Process a natural language query using the improved LangChain SQL agent.
 *
 * The server now uses LangChain's SQLDatabase wrapper which:
 * - Automatically caches database schemas
 * - Provides SQL tools to the agent
 * - Handles read-only query execution
 *
 * No manual metadata approval workflow needed!
 */
export async function processQueryImproved(
  _databaseId: string,
  query: string,
  _credentials: DatabaseCredentials
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
    }),
  });

  if (!response.ok) {
    throw new Error(`LLM API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send error feedback to the agent for query correction.
 */
export async function sendErrorFeedbackImproved(
  databaseId: string,
  sql: string,
  errorMessage: string,
  originalQuery: string,
  credentials: DatabaseCredentials
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/error-feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      database_id: databaseId,
      sql,
      error_message: errorMessage,
      original_query: originalQuery,
      connection: buildConnectionObject(credentials),
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to send error feedback: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get cached schema information for a database.
 */
export async function getSchemaInfo(
  databaseId: string,
  credentials: DatabaseCredentials
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/schema-info`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      database_id: databaseId,
      connection: buildConnectionObject(credentials),
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to get schema info: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Clear cached schema for a database.
 */
export async function clearDatabaseCache(databaseId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/cache/${databaseId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to clear cache: ${response.statusText}`);
  }
}

export async function checkHealth(): Promise<{ status: string; ollama_url: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error('LLM server is not available');
  }

  return response.json();
}
