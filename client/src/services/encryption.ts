import { invoke } from "@tauri-apps/api/core";
import type { DatabaseCredentials } from "../types/database";

export interface EncryptedConnection {
  encrypted_data: string;
  nonce: string;
  salt: string;
  name: string;
}

/**
 * Encrypt database credentials with a password
 */
export async function encryptConnection(
  credentials: DatabaseCredentials,
  password: string
): Promise<EncryptedConnection> {
  // Convert credentials to JSON string
  const credentialsJson = JSON.stringify(credentials);

  const result = await invoke<EncryptedConnection>("encrypt_connection", {
    credentialsJson,
    password,
    connectionName: credentials.name,
  });

  return result;
}

/**
 * Decrypt connection data with a password
 */
export async function decryptConnection(
  encrypted: EncryptedConnection,
  password: string
): Promise<DatabaseCredentials> {
  const decryptedJson = await invoke<string>("decrypt_connection", {
    encryptedConn: encrypted,
    password,
  });

  return JSON.parse(decryptedJson) as DatabaseCredentials;
}

/**
 * Verify if a password can decrypt the connection
 */
export async function verifyPassword(
  encrypted: EncryptedConnection,
  password: string
): Promise<boolean> {
  try {
    return await invoke<boolean>("verify_connection_password", {
      encryptedConn: encrypted,
      password,
    });
  } catch {
    return false;
  }
}
