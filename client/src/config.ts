/**
 * Application Configuration
 * Manages environment-specific settings like API URLs
 */

// Determine the environment
const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

// Backend API URL Configuration
// In development: use local backend
// In production: use production backend (can be overridden with VITE_API_URL)
const getApiUrl = (): string => {
  // Check for explicit environment variable override
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // Default based on environment
  if (isProduction) {
    // Production backend URL
    return 'https://inspektor.hmartin.dev';
  }

  // Development backend URL
  return 'http://localhost:8000';
};

// Export configuration
export const config = {
  // Backend API URL
  apiUrl: getApiUrl(),

  // Environment flags
  isDevelopment,
  isProduction,

  // App metadata
  appName: 'Inspektor',
  version: '0.1.0',

  // Feature flags
  features: {
    workspaceSharing: true,
    contextAnalysis: true,
    conversationHistory: true,
  },

  // API timeouts (in milliseconds)
  timeouts: {
    default: 30000,      // 30 seconds
    llmQuery: 300000,    // 5 minutes for LLM queries
    metadata: 60000,     // 1 minute for metadata fetching
  },

  // Logging
  logging: {
    enabled: isDevelopment,
    level: isDevelopment ? 'debug' : 'info',
  },
} as const;

// Type for config
export type AppConfig = typeof config;

// Helper to log configuration (useful for debugging)
export const logConfig = () => {
  if (config.logging.enabled) {
    console.log('🔧 Application Configuration:', {
      apiUrl: config.apiUrl,
      environment: config.isProduction ? 'production' : 'development',
      version: config.version,
    });
  }
};
