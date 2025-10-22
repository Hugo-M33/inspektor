use super::connection::create_pool;
use super::credentials::CredentialStore;
use super::types::{ColumnInfo, DatabaseError, DatabaseType, Relationship, TableInfo, TableSchema};
use sqlx::{Column, Row, TypeInfo};
use tauri::State;

pub async fn get_tables(
    database_id: &str,
    store: &CredentialStore,
) -> Result<Vec<TableInfo>, DatabaseError> {
    let creds = store.get(database_id)?;
    let pool = create_pool(&creds).await?;

    let query = match creds.db_type {
        DatabaseType::Postgres => {
            "SELECT table_name::text, table_schema::text FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema') ORDER BY table_name"
        }
        DatabaseType::MySQL => {
            "SELECT table_name, table_schema FROM information_schema.tables WHERE table_schema = DATABASE() ORDER BY table_name"
        }
        DatabaseType::SQLite => {
            "SELECT name as table_name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        }
    };

    let rows = sqlx::query(query)
        .fetch_all(&pool)
        .await
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    let mut tables = Vec::new();
    for row in rows {
        let table_name: String = row
            .try_get("table_name")
            .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

        let schema: Option<String> = if matches!(creds.db_type, DatabaseType::SQLite) {
            None
        } else {
            row.try_get("table_schema").ok()
        };

        tables.push(TableInfo {
            name: table_name,
            schema,
            row_count: None, // We could optionally count rows here
        });
    }

    pool.close().await;
    Ok(tables)
}

pub async fn get_table_schema(
    database_id: &str,
    table_name: &str,
    schema: Option<&str>,
    store: &CredentialStore,
) -> Result<TableSchema, DatabaseError> {
    let creds = store.get(database_id)?;
    let pool = create_pool(&creds).await?;

    let query = match creds.db_type {
        DatabaseType::Postgres => {
            format!(
                "SELECT
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
                FROM information_schema.columns c
                LEFT JOIN (
                    SELECT ku.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage ku
                        ON tc.constraint_name = ku.constraint_name
                        AND tc.table_schema = ku.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND tc.table_name = '{}'
                        AND tc.table_schema = '{}'
                ) pk ON c.column_name = pk.column_name
                WHERE c.table_name = '{}' AND c.table_schema = '{}'
                ORDER BY c.ordinal_position",
                table_name,
                schema.unwrap_or("public"),
                table_name,
                schema.unwrap_or("public")
            )
        }
        DatabaseType::MySQL => {
            format!(
                "SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    CASE WHEN column_key = 'PRI' THEN 1 ELSE 0 END as is_primary_key
                FROM information_schema.columns
                WHERE table_name = '{}' AND table_schema = DATABASE()
                ORDER BY ordinal_position",
                table_name
            )
        }
        DatabaseType::SQLite => {
            format!("PRAGMA table_info('{}')", table_name)
        }
    };

    let rows = sqlx::query(&query)
        .fetch_all(&pool)
        .await
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    let mut columns = Vec::new();

    if matches!(creds.db_type, DatabaseType::SQLite) {
        // SQLite PRAGMA returns different column names
        for row in rows {
            let col_name: String = row
                .try_get("name")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
            let data_type: String = row
                .try_get("type")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
            let not_null: i32 = row
                .try_get("notnull")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
            let pk: i32 = row
                .try_get("pk")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
            let default_val: Option<String> = row.try_get("dflt_value").ok();

            columns.push(ColumnInfo {
                name: col_name,
                data_type,
                is_nullable: not_null == 0,
                is_primary_key: pk > 0,
                default_value: default_val,
            });
        }
    } else {
        for row in rows {
            let col_name: String = row
                .try_get("column_name")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
            let data_type: String = row
                .try_get("data_type")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

            let is_nullable_str: String = row
                .try_get("is_nullable")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
            let is_nullable = is_nullable_str.to_uppercase() == "YES";

            let default_val: Option<String> = row.try_get("column_default").ok();

            let is_pk = if matches!(creds.db_type, DatabaseType::MySQL) {
                let pk_val: i32 = row.try_get("is_primary_key").unwrap_or(0);
                pk_val > 0
            } else {
                let pk_val: bool = row.try_get("is_primary_key").unwrap_or(false);
                pk_val
            };

            columns.push(ColumnInfo {
                name: col_name,
                data_type,
                is_nullable,
                is_primary_key: is_pk,
                default_value: default_val,
            });
        }
    }

    pool.close().await;

    Ok(TableSchema {
        table_name: table_name.to_string(),
        schema: schema.map(|s| s.to_string()),
        columns,
    })
}

pub async fn get_relationships(
    database_id: &str,
    store: &CredentialStore,
) -> Result<Vec<Relationship>, DatabaseError> {
    let creds = store.get(database_id)?;
    let pool = create_pool(&creds).await?;

    let query = match creds.db_type {
        DatabaseType::Postgres => {
            "SELECT
                tc.table_name::text,
                kcu.column_name::text,
                ccu.table_name::text AS foreign_table,
                ccu.column_name::text AS foreign_column,
                tc.constraint_name::text
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'"
        }
        DatabaseType::MySQL => {
            "SELECT
                table_name,
                column_name,
                referenced_table_name AS foreign_table,
                referenced_column_name AS foreign_column,
                constraint_name
            FROM information_schema.key_column_usage
            WHERE referenced_table_name IS NOT NULL
                AND table_schema = DATABASE()"
        }
        DatabaseType::SQLite => {
            // SQLite doesn't have a simple way to get all foreign keys
            // We would need to run PRAGMA foreign_key_list for each table
            return Ok(Vec::new());
        }
    };

    let rows = sqlx::query(query)
        .fetch_all(&pool)
        .await
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    let mut relationships = Vec::new();
    for row in rows {
        relationships.push(Relationship {
            table_name: row
                .try_get("table_name")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
            column_name: row
                .try_get("column_name")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
            foreign_table: row
                .try_get("foreign_table")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
            foreign_column: row
                .try_get("foreign_column")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
            constraint_name: row
                .try_get("constraint_name")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
        });
    }

    pool.close().await;
    Ok(relationships)
}

// Tauri commands for metadata
#[tauri::command]
pub async fn get_database_tables(
    database_id: String,
    store: State<'_, CredentialStore>,
) -> Result<Vec<TableInfo>, String> {
    get_tables(&database_id, &store)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn get_database_table_schema(
    database_id: String,
    table_name: String,
    schema: Option<String>,
    store: State<'_, CredentialStore>,
) -> Result<TableSchema, String> {
    get_table_schema(&database_id, &table_name, schema.as_deref(), &store)
        .await
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn get_database_relationships(
    database_id: String,
    store: State<'_, CredentialStore>,
) -> Result<Vec<Relationship>, String> {
    get_relationships(&database_id, &store)
        .await
        .map_err(|e| e.to_string())
}
