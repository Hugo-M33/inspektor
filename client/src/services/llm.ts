import type { QueryResponse, ConversationMessage } from "../types/database";

const API_BASE_URL = "http://127.0.0.1:8000";

export async function processQuery(
  databaseId: string,
  query: string,
  conversationHistory: ConversationMessage[] = []
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      database_id: databaseId,
      query,
      conversation_history: conversationHistory,
    }),
  });

  if (!response.ok) {
    throw new Error(`LLM API error: ${response.statusText}`);
  }

  return response.json();
}

export async function submitMetadata(
  requestId: string,
  metadataType: string,
  data: any
): Promise<void> {
  console.log("submitMetadata", requestId, metadataType, data);
  const response = await fetch(`${API_BASE_URL}/metadata`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      request_id: requestId,
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
  sql: string,
  errorMessage: string,
  originalQuery: string
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/error-feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      database_id: databaseId,
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

export async function checkHealth(): Promise<{
  status: string;
  ollama_url: string;
}> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error("LLM server is not available");
  }

  return response.json();
}
