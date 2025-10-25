export type DatabaseType = 'postgres' | 'mysql' | 'sqlite';

export interface DatabaseCredentials {
  id: string;
  name: string;
  db_type: DatabaseType;
  host?: string;
  port?: number;
  database: string;
  username?: string;
  password?: string;
  file_path?: string;
  schema?: string;  // Optional PostgreSQL schema (e.g., 'public')
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  server_version?: string;
}

export interface QueryResult {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  execution_time_ms: number;
}

export interface TableInfo {
  name: string;
  schema?: string;
  row_count?: number;
}

export interface ColumnInfo {
  name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  default_value?: string;
}

export interface TableSchema {
  table_name: string;
  schema?: string;
  columns: ColumnInfo[];
}

export interface Relationship {
  table_name: string;
  column_name: string;
  foreign_table: string;
  foreign_column: string;
  constraint_name: string;
}

export interface MetadataRequest {
  metadata_type: 'tables' | 'schema' | 'relationships';
  params?: Record<string, any>;
  reason: string;
}

export interface SQLResponse {
  sql: string;
  explanation: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface QueryResponse {
  status: 'needs_metadata' | 'ready' | 'error' | 'clarification';
  conversation_id: string;
  metadata_request?: MetadataRequest;
  sql_response?: SQLResponse;
  message?: string;
  error?: string;
  failed_sql?: string;  // SQL that caused an error, if any
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}
