import { invoke } from "@tauri-apps/api/core";
import { config } from "../config";

const API_BASE_URL = config.apiUrl;

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  expires_in: number;
  user: User;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

// Local storage keys
const TOKEN_KEY = "inspektor_token";
const USER_KEY = "inspektor_user";

/**
 * Register a new user account
 */
export async function register(
  email: string,
  password: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Registration failed");
  }

  const data: LoginResponse = await response.json();

  // Store token and user data using Tauri secure storage
  await saveAuthData(data.access_token, data.user);

  return data;
}

/**
 * Login with email and password
 */
export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Login failed");
  }

  const data: LoginResponse = await response.json();

  // Store token and user data
  await saveAuthData(data.access_token, data.user);

  return data;
}

/**
 * Logout current user
 */
export async function logout(): Promise<void> {
  const token = await getToken();

  if (token) {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error("Logout API call failed:", error);
      // Continue with local logout even if API call fails
    }
  }

  // Clear local auth data
  await clearAuthData();
}

/**
 * Get current user info from server
 */
export async function getCurrentUser(): Promise<User> {
  const token = await getToken();

  if (!token) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired or invalid
      await clearAuthData();
      throw new Error("Session expired. Please login again.");
    }
    throw new Error("Failed to get user info");
  }

  return response.json();
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  const token = await getToken();
  return token !== null;
}

/**
 * Get current auth state
 */
export async function getAuthState(): Promise<AuthState> {
  const token = await getToken();
  const user = await getStoredUser();

  return {
    token,
    user,
    isAuthenticated: token !== null && user !== null,
  };
}

/**
 * Get stored authentication token
 */
export async function getToken(): Promise<string | null> {
  try {
    // Try to get from Tauri secure storage first
    const token = await invoke<string>("get_secure_storage", { key: TOKEN_KEY });
    return token || null;
  } catch (error) {
    // Silently fallback to localStorage
    // Note: "Command get_secure_storage not found" is expected in development
    // until Tauri secure storage commands are implemented
    return localStorage.getItem(TOKEN_KEY);
  }
}

/**
 * Get stored user data
 */
export async function getStoredUser(): Promise<User | null> {
  try {
    const userJson = await invoke<string>("get_secure_storage", { key: USER_KEY });
    return userJson ? JSON.parse(userJson) : null;
  } catch {
    // Fallback to localStorage
    const userJson = localStorage.getItem(USER_KEY);
    return userJson ? JSON.parse(userJson) : null;
  }
}

/**
 * Save authentication data securely
 */
async function saveAuthData(token: string, user: User): Promise<void> {
  try {
    // Try to use Tauri secure storage
    await invoke("set_secure_storage", { key: TOKEN_KEY, value: token });
    await invoke("set_secure_storage", {
      key: USER_KEY,
      value: JSON.stringify(user),
    });
  } catch {
    // Fallback to localStorage for development
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
}

/**
 * Clear all authentication data
 */
async function clearAuthData(): Promise<void> {
  try {
    await invoke("remove_secure_storage", { key: TOKEN_KEY });
    await invoke("remove_secure_storage", { key: USER_KEY });
  } catch {
    // Fallback to localStorage
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

/**
 * Make an authenticated API request
 */
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getToken();

  if (!token) {
    throw new Error("Not authenticated");
  }

  const headers = {
    ...options.headers,
    Authorization: `Bearer ${token}`,
  };

  const response = await fetch(url, { ...options, headers });

  // Handle token expiration
  if (response.status === 401) {
    await clearAuthData();
    throw new Error("Session expired. Please login again.");
  }

  return response;
}
