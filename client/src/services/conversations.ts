import { authenticatedFetch } from "./auth";

const API_BASE_URL = "http://127.0.0.1:8000";

export interface ConversationSummary {
  id: string;
  database_id: string;
  title: string;
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
  title: string;
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
