import type { QueryResponse, ConversationMessage } from "../types/database";
import { authenticatedFetch } from "./auth";

const API_BASE_URL = "http://127.0.0.1:8000";

export async function processQuery(
  databaseId: string,
  query: string,
  conversationId?: string
): Promise<QueryResponse> {
  const response = await authenticatedFetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      database_id: databaseId,
      query,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    throw new Error(`LLM API error: ${response.statusText}`);
  }

  return response.json();
}

export async function submitMetadata(
  databaseId: string,
  metadataType: string,
  data: any
): Promise<void> {
  const response = await authenticatedFetch(`${API_BASE_URL}/metadata`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      database_id: databaseId,
      metadata_type: metadataType,
      data,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to submit metadata: ${response.statusText}`);
  }
}

export async function sendErrorFeedback(
  databaseId: string,
  conversationId: string,
  sql: string,
  errorMessage: string,
  originalQuery: string
): Promise<QueryResponse> {
  const response = await authenticatedFetch(`${API_BASE_URL}/error-feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      database_id: databaseId,
      conversation_id: conversationId,
      sql,
      error_message: errorMessage,
      original_query: originalQuery,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to send error feedback: ${response.statusText}`);
  }

  return response.json();
}

export async function sendMessage(
  conversationId: string,
  message: string,
  databaseId: string
): Promise<QueryResponse> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/conversations/${conversationId}/message`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        database_id: databaseId,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`);
  }

  return response.json();
}

export async function checkHealth(): Promise<{
  status: string;
  version: string;
  llm_model: string;
}> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error("LLM server is not available");
  }

  return response.json();
}
