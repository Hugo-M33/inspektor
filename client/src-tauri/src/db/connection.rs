use super::types::{ConnectionTestResult, DatabaseCredentials, DatabaseError, DatabaseType};
use sqlx::{Any, AnyPool, Column, Pool, Row, TypeInfo};

pub async fn build_connection_string(creds: &DatabaseCredentials) -> Result<String, DatabaseError> {
    match creds.db_type {
        DatabaseType::Postgres => {
            let host = creds.host.as_ref().ok_or_else(|| {
                DatabaseError::CredentialsError("Host is required for PostgreSQL".to_string())
            })?;
            let port = creds.port.unwrap_or(5432);
            let username = creds.username.as_ref().ok_or_else(|| {
                DatabaseError::CredentialsError("Username is required for PostgreSQL".to_string())
            })?;
            let password = creds.password.as_ref().ok_or_else(|| {
                DatabaseError::CredentialsError("Password is required for PostgreSQL".to_string())
            })?;

            Ok(format!(
                "postgres://{}:{}@{}:{}/{}",
                username, password, host, port, creds.database
            ))
        }
        DatabaseType::MySQL => {
            let host = creds.host.as_ref().ok_or_else(|| {
                DatabaseError::CredentialsError("Host is required for MySQL".to_string())
            })?;
            let port = creds.port.unwrap_or(3306);
            let username = creds.username.as_ref().ok_or_else(|| {
                DatabaseError::CredentialsError("Username is required for MySQL".to_string())
            })?;
            let password = creds.password.as_ref().ok_or_else(|| {
                DatabaseError::CredentialsError("Password is required for MySQL".to_string())
            })?;

            Ok(format!(
                "mysql://{}:{}@{}:{}/{}",
                username, password, host, port, creds.database
            ))
        }
        DatabaseType::SQLite => {
            let file_path = creds.file_path.as_ref().ok_or_else(|| {
                DatabaseError::CredentialsError("File path is required for SQLite".to_string())
            })?;

            Ok(format!("sqlite://{}", file_path))
        }
    }
}

pub async fn create_pool(creds: &DatabaseCredentials) -> Result<Pool<Any>, DatabaseError> {
    let conn_str = build_connection_string(creds).await?;
    sqlx::any::install_default_drivers();
    
    let pool = AnyPool::connect(&conn_str)
        .await
        .map_err(|e| DatabaseError::ConnectionError(e.to_string()))?;

    Ok(pool)
}

pub async fn test_connection(creds: &DatabaseCredentials) -> Result<ConnectionTestResult, DatabaseError> {
    let pool = create_pool(creds).await?;

    // Test the connection with a simple query
    let version_query = match creds.db_type {
        DatabaseType::Postgres => "SELECT version()",
        DatabaseType::MySQL => "SELECT VERSION()",
        DatabaseType::SQLite => "SELECT sqlite_version()",
    };

    let row = sqlx::query(version_query)
        .fetch_one(&pool)
        .await
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    let version: String = row
        .try_get(0)
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    pool.close().await;

    Ok(ConnectionTestResult {
        success: true,
        message: "Connection successful".to_string(),
        server_version: Some(version),
    })
}

// Tauri command for testing connections
#[tauri::command]
pub async fn test_database_connection(
    credentials: DatabaseCredentials,
) -> Result<ConnectionTestResult, String> {
    test_connection(&credentials)
        .await
        .map_err(|e| e.to_string())
}
