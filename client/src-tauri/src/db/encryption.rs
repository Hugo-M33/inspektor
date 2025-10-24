use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use argon2::{
    password_hash::{rand_core::RngCore, SaltString},
    Argon2, PasswordHasher,
};
use base64::{engine::general_purpose, Engine as _};
use serde::{Deserialize, Serialize};

use super::types::DatabaseError;

/// Encrypted connection data that can be safely stored on the server
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedConnection {
    /// Base64-encoded encrypted credentials
    pub encrypted_data: String,
    /// Base64-encoded nonce used for encryption
    pub nonce: String,
    /// Base64-encoded salt used for key derivation
    pub salt: String,
    /// Connection name (not encrypted)
    pub name: String,
}

/// Service for encrypting and decrypting database credentials
pub struct EncryptionService;

impl EncryptionService {
    /// Encrypt database credentials with a user password
    ///
    /// # Arguments
    /// * `credentials_json` - JSON string of the credentials to encrypt
    /// * `password` - User's password for encryption
    ///
    /// # Returns
    /// * `EncryptedConnection` - Encrypted data with salt and nonce
    pub fn encrypt(
        credentials_json: &str,
        password: &str,
        connection_name: &str,
    ) -> Result<EncryptedConnection, DatabaseError> {
        // Generate a random salt for key derivation
        let salt = SaltString::generate(&mut OsRng);

        // Derive encryption key from password using Argon2
        let key = Self::derive_key(password, salt.as_str())?;

        // Generate a random nonce for AES-GCM
        let cipher = Aes256Gcm::new(&key.into());
        let mut nonce_bytes = [0u8; 12];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        // Encrypt the credentials
        let ciphertext = cipher
            .encrypt(nonce, credentials_json.as_bytes())
            .map_err(|e| DatabaseError::EncryptionError(format!("Encryption failed: {}", e)))?;

        Ok(EncryptedConnection {
            encrypted_data: general_purpose::STANDARD.encode(&ciphertext),
            nonce: general_purpose::STANDARD.encode(nonce),
            salt: salt.as_str().to_string(),
            name: connection_name.to_string(),
        })
    }

    /// Decrypt database credentials with a user password
    ///
    /// # Arguments
    /// * `encrypted_conn` - Encrypted connection data
    /// * `password` - User's password for decryption
    ///
    /// # Returns
    /// * `String` - Decrypted JSON string of credentials
    pub fn decrypt(
        encrypted_conn: &EncryptedConnection,
        password: &str,
    ) -> Result<String, DatabaseError> {
        // Derive the same key from password and salt
        let key = Self::derive_key(password, &encrypted_conn.salt)?;

        // Decode base64 data
        let ciphertext = general_purpose::STANDARD
            .decode(&encrypted_conn.encrypted_data)
            .map_err(|e| DatabaseError::EncryptionError(format!("Invalid encrypted data: {}", e)))?;

        let nonce_bytes = general_purpose::STANDARD
            .decode(&encrypted_conn.nonce)
            .map_err(|e| DatabaseError::EncryptionError(format!("Invalid nonce: {}", e)))?;

        let nonce = Nonce::from_slice(&nonce_bytes);

        // Decrypt
        let cipher = Aes256Gcm::new(&key.into());
        let plaintext = cipher
            .decrypt(nonce, ciphertext.as_ref())
            .map_err(|e| DatabaseError::EncryptionError(format!("Decryption failed (wrong password?): {}", e)))?;

        String::from_utf8(plaintext)
            .map_err(|e| DatabaseError::EncryptionError(format!("Invalid UTF-8: {}", e)))
    }

    /// Derive a 256-bit encryption key from password and salt using Argon2
    fn derive_key(password: &str, salt_str: &str) -> Result<[u8; 32], DatabaseError> {
        use argon2::password_hash::SaltString;

        let argon2 = Argon2::default();

        // Create SaltString from the string representation
        let salt = SaltString::new(salt_str)
            .map_err(|e| DatabaseError::EncryptionError(format!("Invalid salt: {}", e)))?;

        let password_hash = argon2
            .hash_password(password.as_bytes(), &salt)
            .map_err(|e| DatabaseError::EncryptionError(format!("Key derivation failed: {}", e)))?;

        // Extract the hash bytes (first 32 bytes)
        let hash_string = password_hash
            .hash
            .ok_or_else(|| DatabaseError::EncryptionError("No hash generated".to_string()))?;

        let hash_bytes = hash_string.as_bytes();

        if hash_bytes.len() < 32 {
            return Err(DatabaseError::EncryptionError(
                "Hash too short".to_string(),
            ));
        }

        let mut key = [0u8; 32];
        key.copy_from_slice(&hash_bytes[0..32]);

        Ok(key)
    }

    /// Test if a password can decrypt the data (password verification)
    pub fn verify_password(
        encrypted_conn: &EncryptedConnection,
        password: &str,
    ) -> bool {
        Self::decrypt(encrypted_conn, password).is_ok()
    }
}

// Tauri commands for encryption/decryption

#[tauri::command]
pub async fn encrypt_connection(
    credentials_json: String,
    password: String,
    connection_name: String,
) -> Result<EncryptedConnection, String> {
    EncryptionService::encrypt(&credentials_json, &password, &connection_name)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn decrypt_connection(
    encrypted_conn: EncryptedConnection,
    password: String,
) -> Result<String, String> {
    EncryptionService::decrypt(&encrypted_conn, &password).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn verify_connection_password(
    encrypted_conn: EncryptedConnection,
    password: String,
) -> Result<bool, String> {
    Ok(EncryptionService::verify_password(&encrypted_conn, &password))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encryption_decryption() {
        let credentials = r#"{"host":"localhost","port":5432,"database":"test"}"#;
        let password = "my_secure_password";
        let name = "Test Connection";

        // Encrypt
        let encrypted = EncryptionService::encrypt(credentials, password, name).unwrap();

        // Decrypt
        let decrypted = EncryptionService::decrypt(&encrypted, password).unwrap();

        assert_eq!(credentials, decrypted);
    }

    #[test]
    fn test_wrong_password() {
        let credentials = r#"{"host":"localhost","port":5432,"database":"test"}"#;
        let password = "my_secure_password";
        let wrong_password = "wrong_password";
        let name = "Test Connection";

        // Encrypt
        let encrypted = EncryptionService::encrypt(credentials, password, name).unwrap();

        // Try to decrypt with wrong password
        let result = EncryptionService::decrypt(&encrypted, wrong_password);

        assert!(result.is_err());
    }

    #[test]
    fn test_verify_password() {
        let credentials = r#"{"host":"localhost","port":5432,"database":"test"}"#;
        let password = "my_secure_password";
        let name = "Test Connection";

        let encrypted = EncryptionService::encrypt(credentials, password, name).unwrap();

        assert!(EncryptionService::verify_password(&encrypted, password));
        assert!(!EncryptionService::verify_password(&encrypted, "wrong"));
    }
}
