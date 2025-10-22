use super::types::{DatabaseCredentials, DatabaseError};
use serde_json;
use std::collections::HashMap;
use std::sync::Mutex;
use tauri::State;

/// In-memory credential store (encrypted storage would be better for production)
/// For now, we'll use Tauri's built-in store plugin
pub struct CredentialStore {
    credentials: Mutex<HashMap<String, DatabaseCredentials>>,
}

impl CredentialStore {
    pub fn new() -> Self {
        Self {
            credentials: Mutex::new(HashMap::new()),
        }
    }

    pub fn add(&self, creds: DatabaseCredentials) -> Result<(), DatabaseError> {
        let mut store = self.credentials.lock().unwrap();
        store.insert(creds.id.clone(), creds);
        Ok(())
    }

    pub fn get(&self, id: &str) -> Result<DatabaseCredentials, DatabaseError> {
        let store = self.credentials.lock().unwrap();
        store
            .get(id)
            .cloned()
            .ok_or_else(|| DatabaseError::CredentialsError(format!("Credentials not found: {}", id)))
    }

    pub fn list(&self) -> Result<Vec<DatabaseCredentials>, DatabaseError> {
        let store = self.credentials.lock().unwrap();
        Ok(store.values().cloned().collect())
    }

    pub fn remove(&self, id: &str) -> Result<(), DatabaseError> {
        let mut store = self.credentials.lock().unwrap();
        store
            .remove(id)
            .ok_or_else(|| DatabaseError::CredentialsError(format!("Credentials not found: {}", id)))?;
        Ok(())
    }

    pub fn update(&self, creds: DatabaseCredentials) -> Result<(), DatabaseError> {
        let mut store = self.credentials.lock().unwrap();
        if !store.contains_key(&creds.id) {
            return Err(DatabaseError::CredentialsError(format!(
                "Credentials not found: {}",
                creds.id
            )));
        }
        store.insert(creds.id.clone(), creds);
        Ok(())
    }
}

// Tauri commands for credential management
#[tauri::command]
pub async fn save_credentials(
    credentials: DatabaseCredentials,
    store: State<'_, CredentialStore>,
) -> Result<String, String> {
    store
        .add(credentials.clone())
        .map_err(|e| e.to_string())?;
    Ok(credentials.id)
}

#[tauri::command]
pub async fn get_credentials(
    id: String,
    store: State<'_, CredentialStore>,
) -> Result<DatabaseCredentials, String> {
    store.get(&id).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn list_credentials(
    store: State<'_, CredentialStore>,
) -> Result<Vec<DatabaseCredentials>, String> {
    store.list().map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn delete_credentials(
    id: String,
    store: State<'_, CredentialStore>,
) -> Result<(), String> {
    store.remove(&id).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn update_credentials(
    credentials: DatabaseCredentials,
    store: State<'_, CredentialStore>,
) -> Result<(), String> {
    store.update(credentials).map_err(|e| e.to_string())
}
