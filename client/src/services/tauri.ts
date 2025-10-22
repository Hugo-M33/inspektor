import { invoke } from '@tauri-apps/api/core';
import type {
  DatabaseCredentials,
  ConnectionTestResult,
  QueryResult,
  TableInfo,
  TableSchema,
  Relationship,
} from '../types/database';

// Credential Management
export async function saveCredentials(credentials: DatabaseCredentials): Promise<string> {
  return invoke<string>('save_credentials', { credentials });
}

export async function getCredentials(id: string): Promise<DatabaseCredentials> {
  return invoke<DatabaseCredentials>('get_credentials', { id });
}

export async function listCredentials(): Promise<DatabaseCredentials[]> {
  return invoke<DatabaseCredentials[]>('list_credentials');
}

export async function deleteCredentials(id: string): Promise<void> {
  return invoke<void>('delete_credentials', { id });
}

export async function updateCredentials(credentials: DatabaseCredentials): Promise<void> {
  return invoke<void>('update_credentials', { credentials });
}

// Connection Testing
export async function testDatabaseConnection(
  credentials: DatabaseCredentials
): Promise<ConnectionTestResult> {
  return invoke<ConnectionTestResult>('test_database_connection', { credentials });
}

// Query Execution
export async function executeSqlQuery(
  databaseId: string,
  sql: string
): Promise<QueryResult> {
  return invoke<QueryResult>('execute_sql_query', {
    databaseId,
    sql,
  });
}

// Metadata Extraction
export async function getDatabaseTables(databaseId: string): Promise<TableInfo[]> {
  return invoke<TableInfo[]>('get_database_tables', { databaseId });
}

export async function getDatabaseTableSchema(
  databaseId: string,
  tableName: string,
  schema?: string
): Promise<TableSchema> {
  return invoke<TableSchema>('get_database_table_schema', {
    databaseId,
    tableName,
    schema,
  });
}

export async function getDatabaseRelationships(databaseId: string): Promise<Relationship[]> {
  return invoke<Relationship[]>('get_database_relationships', { databaseId });
}
