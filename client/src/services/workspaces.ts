import { authenticatedFetch } from "./auth";
import { config } from "../config";

const API_BASE_URL = config.apiUrl;

export interface Workspace {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  connection_count: number;
}

export interface WorkspaceConnection {
  id: string;
  workspace_id: string;
  name: string;
  encrypted_data: string;
  nonce: string;
  salt: string;
  created_at: string;
  updated_at: string;
}

export interface CreateWorkspaceRequest {
  name: string;
}

export interface AddConnectionRequest {
  name: string;
  encrypted_data: string;
  nonce: string;
  salt: string;
}

/**
 * Create a new workspace
 */
export async function createWorkspace(name: string): Promise<Workspace> {
  const response = await authenticatedFetch(`${API_BASE_URL}/workspaces`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  });

  if (!response.ok) {
    throw new Error("Failed to create workspace");
  }

  return response.json();
}

/**
 * List all workspaces for the current user
 */
export async function listWorkspaces(): Promise<Workspace[]> {
  const response = await authenticatedFetch(`${API_BASE_URL}/workspaces`);

  if (!response.ok) {
    throw new Error("Failed to fetch workspaces");
  }

  return response.json();
}

/**
 * Delete a workspace
 */
export async function deleteWorkspace(workspaceId: string): Promise<void> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/workspaces/${workspaceId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to delete workspace");
  }
}

/**
 * Add an encrypted connection to a workspace
 */
export async function addWorkspaceConnection(
  workspaceId: string,
  connection: AddConnectionRequest
): Promise<WorkspaceConnection> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/workspaces/${workspaceId}/connections`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(connection),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to add connection");
  }

  return response.json();
}

/**
 * List all connections in a workspace
 */
export async function listWorkspaceConnections(
  workspaceId: string
): Promise<WorkspaceConnection[]> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/workspaces/${workspaceId}/connections`
  );

  if (!response.ok) {
    throw new Error("Failed to fetch connections");
  }

  return response.json();
}

/**
 * Delete a connection from a workspace
 */
export async function deleteWorkspaceConnection(
  workspaceId: string,
  connectionId: string
): Promise<void> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/workspaces/${workspaceId}/connections/${connectionId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error("Failed to delete connection");
  }
}
