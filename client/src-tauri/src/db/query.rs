use super::connection::create_pool;
use super::credentials::CredentialStore;
use super::types::{DatabaseError, QueryResult};
use serde_json::Value;
use sqlx::{Column, Row, TypeInfo};
use std::collections::HashMap;
use std::time::Instant;
use tauri::State;

/// List of SQL keywords that indicate destructive operations
const DESTRUCTIVE_KEYWORDS: &[&str] = &[
    "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE", "GRANT", "REVOKE",
];

/// Validate SQL query for safety
fn validate_query(sql: &str) -> Result<(), DatabaseError> {
    let sql_upper = sql.trim().to_uppercase();

    // Check for destructive operations
    for keyword in DESTRUCTIVE_KEYWORDS {
        if sql_upper.starts_with(keyword) {
            return Err(DatabaseError::DestructiveOperation(format!(
                "{} operations are not allowed",
                keyword
            )));
        }
    }

    // Basic SQL injection checks
    // Note: This is a simple check. In production, use parameterized queries
    let suspicious_patterns = vec![
        "--",      // SQL comments
        "/*",      // Multi-line comments
        ";",       // Multiple statements (could be legitimate in some cases)
        "xp_",     // SQL Server extended procedures
        "sp_",     // SQL Server stored procedures
    ];

    for pattern in suspicious_patterns {
        if sql.contains(pattern) && pattern == ";" {
            // Allow semicolon at the end only
            if sql.trim().ends_with(';') && sql.matches(';').count() == 1 {
                continue;
            }
            return Err(DatabaseError::SQLInjection);
        } else if sql.contains(pattern) && pattern != ";" {
            return Err(DatabaseError::SQLInjection);
        }
    }

    Ok(())
}

pub async fn execute_query(
    database_id: &str,
    sql: &str,
    store: &CredentialStore,
) -> Result<QueryResult, DatabaseError> {
    // Validate the query first
    validate_query(sql)?;

    // Get credentials
    let creds = store.get(database_id)?;

    // Create connection pool
    let pool = create_pool(&creds).await?;

    // Execute query and measure time
    let start = Instant::now();

    let rows = sqlx::query(sql)
        .fetch_all(&pool)
        .await
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    let execution_time = start.elapsed();

    // Convert rows to our format
    let mut result_rows: Vec<HashMap<String, Value>> = Vec::new();
    let mut columns: Vec<String> = Vec::new();

    if !rows.is_empty() {
        // Get column names from first row
        columns = rows[0]
            .columns()
            .iter()
            .map(|col| col.name().to_string())
            .collect();

        // Convert each row
        for row in &rows {
            let mut row_map = HashMap::new();

            for (idx, column) in row.columns().iter().enumerate() {
                let col_name = column.name().to_string();

                // Try to get value as different types
                let value: Value = if let Ok(val) = row.try_get::<String, _>(idx) {
                    Value::String(val)
                } else if let Ok(val) = row.try_get::<i64, _>(idx) {
                    Value::Number(val.into())
                } else if let Ok(val) = row.try_get::<i32, _>(idx) {
                    Value::Number(val.into())
                } else if let Ok(val) = row.try_get::<f64, _>(idx) {
                    Value::Number(
                        serde_json::Number::from_f64(val)
                            .unwrap_or_else(|| serde_json::Number::from(0)),
                    )
                } else if let Ok(val) = row.try_get::<bool, _>(idx) {
                    Value::Bool(val)
                } else {
                    // Try to get as raw bytes and convert to string
                    Value::Null
                };

                row_map.insert(col_name, value);
            }

            result_rows.push(row_map);
        }
    }

    pool.close().await;

    Ok(QueryResult {
        columns,
        row_count: result_rows.len(),
        rows: result_rows,
        execution_time_ms: execution_time.as_millis() as u64,
    })
}

// Tauri command for executing queries
#[tauri::command]
pub async fn execute_sql_query(
    database_id: String,
    sql: String,
    store: State<'_, CredentialStore>,
) -> Result<QueryResult, String> {
    execute_query(&database_id, &sql, &store)
        .await
        .map_err(|e| e.to_string())
}
