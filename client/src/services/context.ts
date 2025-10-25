import { authenticatedFetch } from "./auth";
import { config } from "../config";

const API_BASE_URL = config.apiUrl;

export interface ContextData {
  tables_used: string[];
  relationships: Array<{
    from_table: string;
    from_column: string;
    to_table: string;
    to_column: string;
    type: string;
  }>;
  column_typecast_hints: Array<{
    table: string;
    column: string;
    hint: string;
    example?: string;
  }>;
  business_context: string[];
  sql_patterns: Array<{
    pattern: string;
    example?: string;
  }>;
}

export interface WorkspaceContext {
  workspace_id: string;
  context_data: ContextData;
  created_at: string;
  updated_at: string;
}

/**
 * Submit satisfaction feedback for a conversation
 */
export async function submitSatisfactionFeedback(
  conversationId: string,
  satisfied: boolean,
  userNotes?: string
): Promise<void> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/conversations/${conversationId}/satisfaction`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        satisfied,
        user_notes: userNotes,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to submit satisfaction feedback");
  }
}

/**
 * Get workspace context
 */
export async function getWorkspaceContext(
  workspaceId: string
): Promise<WorkspaceContext> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/workspaces/${workspaceId}/context`
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("No context found for this workspace");
    }
    throw new Error("Failed to fetch workspace context");
  }

  return response.json();
}

/**
 * Update workspace context
 */
export async function updateWorkspaceContext(
  workspaceId: string,
  contextData: ContextData
): Promise<void> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/workspaces/${workspaceId}/context`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        context_data: contextData,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to update workspace context");
  }
}
