import { authenticatedFetch } from "./auth";
import { config } from "../config";

const API_BASE_URL = config.apiUrl;

export interface ConversationSummary {
  id: string;
  database_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  metadata?: any;
  timestamp: string;
}

export interface ConversationDetail {
  id: string;
  database_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

/**
 * List user's conversations
 */
export async function listConversations(
  databaseId?: string,
  limit: number = 50,
  offset: number = 0
): Promise<ConversationSummary[]> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  if (databaseId) {
    params.append("database_id", databaseId);
  }

  const response = await authenticatedFetch(
    `${API_BASE_URL}/conversations?${params}`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch conversations");
  }

  return response.json();
}

/**
 * Get detailed conversation with all messages
 */
export async function getConversation(
  conversationId: string
): Promise<ConversationDetail> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/conversations/${conversationId}`
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Conversation not found");
    }
    throw new Error("Failed to fetch conversation");
  }

  return response.json();
}

/**
 * Delete a conversation
 */
export async function deleteConversation(
  conversationId: string
): Promise<void> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/conversations/${conversationId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to delete conversation");
  }
}

/**
 * Update conversation title
 */
export async function updateConversationTitle(
  conversationId: string,
  title: string
): Promise<void> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/conversations/${conversationId}/title`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to update conversation title");
  }
}

/**
 * Auto-generate a conversation title using LLM
 */
export async function generateConversationTitle(
  conversationId: string
): Promise<string> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/conversations/${conversationId}/generate-title`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to generate conversation title");
  }

  const data = await response.json();
  return data.title;
}
