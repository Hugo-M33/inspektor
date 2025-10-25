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
            "SELECT table_name::text, table_schema::text FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema') ORDER BY table_name".to_string()
        }
        DatabaseType::MySQL => {
            format!("SELECT table_name, table_schema FROM information_schema.tables WHERE table_schema = '{}' ORDER BY table_name", creds.database)
        }
        DatabaseType::SQLite => {
            "SELECT name as table_name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name".to_string()
        }
    };

    let rows = sqlx::query(&query)
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
    table_names: &str,
    schema: Option<&str>,
    store: &CredentialStore,
) -> Result<Vec<TableSchema>, DatabaseError> {
    let creds = store.get(database_id)?;
    let pool = create_pool(&creds).await?;

    let mut schemas = Vec::new();

    if matches!(creds.db_type, DatabaseType::SQLite) {
        // SQLite: PRAGMA only works for one table at a time
        // Parse table_names like "('users', 'files')" to extract individual tables
        let tables: Vec<&str> = table_names
            .trim_matches(|c| c == '(' || c == ')')
            .split(',')
            .map(|s| s.trim().trim_matches('\'').trim_matches('"'))
            .filter(|s| !s.is_empty())
            .collect();

        for table_name in tables {
            let query = format!("PRAGMA table_info('{}')", table_name);
            let rows = sqlx::query(&query)
                .fetch_all(&pool)
                .await
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

            let mut columns = Vec::new();
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

            schemas.push(TableSchema {
                table_name: table_name.to_string(),
                schema: None,
                columns,
            });
        }
    } else {
        // Postgres and MySQL can query multiple tables at once
        let query = match creds.db_type {
            DatabaseType::Postgres => {
                format!(
                    "SELECT
                        c.table_name::text,
                        c.column_name::text,
                        c.data_type::text,
                        c.is_nullable::text,
                        c.column_default::text,
                        CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT ku.table_name::text, ku.column_name::text
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku
                            ON tc.constraint_name = ku.constraint_name
                            AND tc.table_schema = ku.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                            AND tc.table_name IN {}
                            AND tc.table_schema = '{}'
                    ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
                    WHERE c.table_name IN {} AND c.table_schema = '{}'
                    ORDER BY c.table_name, c.ordinal_position",
                    table_names,
                    schema.unwrap_or("public"),
                    table_names,
                    schema.unwrap_or("public")
                )
            }
            DatabaseType::MySQL => {
                format!(
                    "SELECT
                        table_name,
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        CASE WHEN column_key = 'PRI' THEN 1 ELSE 0 END as is_primary_key
                    FROM information_schema.columns
                    WHERE table_name IN {} AND table_schema = '{}'
                    ORDER BY table_name, ordinal_position",
                    table_names,
                    creds.database
                )
            }
            DatabaseType::SQLite => unreachable!(),
        };

        let rows = sqlx::query(&query)
            .fetch_all(&pool)
            .await
            .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

        // Group columns by table name
        use std::collections::HashMap;
        let mut tables_map: HashMap<String, Vec<ColumnInfo>> = HashMap::new();

        for row in rows {
            let table_name: String = row
                .try_get("table_name")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
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

            let column_info = ColumnInfo {
                name: col_name,
                data_type,
                is_nullable,
                is_primary_key: is_pk,
                default_value: default_val,
            };

            tables_map
                .entry(table_name)
                .or_insert_with(Vec::new)
                .push(column_info);
        }

        // Convert HashMap to Vec<TableSchema>
        for (table_name, columns) in tables_map {
            schemas.push(TableSchema {
                table_name,
                schema: schema.map(|s| s.to_string()),
                columns,
            });
        }
    }

    pool.close().await;
    Ok(schemas)
}

pub async fn get_relationships(
    database_id: &str,
    store: &CredentialStore,
) -> Result<Vec<Relationship>, DatabaseError> {
    let creds = store.get(database_id)?;
    let pool = create_pool(&creds).await?;

    let mut relationships = Vec::new();

    // Step 1: Get explicit foreign key constraints
    let explicit_relationships = get_explicit_relationships(&creds, &pool).await?;
    relationships.extend(explicit_relationships);

    // Step 2: Infer relationships based on naming conventions and schema analysis
    let inferred_relationships = infer_relationships(&creds, &pool).await?;
    relationships.extend(inferred_relationships);

    pool.close().await;
    Ok(relationships)
}

/// Get explicit foreign key constraints from the database
async fn get_explicit_relationships(
    creds: &super::types::DatabaseCredentials,
    pool: &sqlx::AnyPool,
) -> Result<Vec<Relationship>, DatabaseError> {
    // Handle SQLite separately since it uses PRAGMA
    if matches!(creds.db_type, DatabaseType::SQLite) {
        return get_sqlite_foreign_keys(pool).await;
    }

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
            WHERE tc.constraint_type = 'FOREIGN KEY'".to_string()
        }
        DatabaseType::MySQL => {
            format!(
                "SELECT
                    table_name,
                    column_name,
                    referenced_table_name AS foreign_table,
                    referenced_column_name AS foreign_column,
                    constraint_name
                FROM information_schema.key_column_usage
                WHERE referenced_table_name IS NOT NULL
                    AND table_schema = '{}'",
                creds.database
            )
        }
        DatabaseType::SQLite => unreachable!(),
    };

    let rows = sqlx::query(&query)
        .fetch_all(pool)
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
            constraint_name: Some(
                row.try_get("constraint_name")
                    .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
            ),
            relationship_type: "foreign_key".to_string(),
            confidence: None,
        });
    }

    Ok(relationships)
}

/// Get foreign keys from SQLite using PRAGMA
async fn get_sqlite_foreign_keys(pool: &sqlx::AnyPool) -> Result<Vec<Relationship>, DatabaseError> {
    // First, get all table names
    let table_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'";
    let table_rows = sqlx::query(table_query)
        .fetch_all(pool)
        .await
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    let mut relationships = Vec::new();

    for table_row in table_rows {
        let table_name: String = table_row
            .try_get("name")
            .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

        // Use PRAGMA to get foreign keys for this table
        let pragma_query = format!("PRAGMA foreign_key_list('{}')", table_name);
        let fk_rows = sqlx::query(&pragma_query)
            .fetch_all(pool)
            .await
            .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

        for fk_row in fk_rows {
            let foreign_table: String = fk_row
                .try_get("table")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
            let column_name: String = fk_row
                .try_get("from")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
            let foreign_column: String = fk_row
                .try_get("to")
                .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

            relationships.push(Relationship {
                table_name: table_name.clone(),
                column_name,
                foreign_table,
                foreign_column,
                constraint_name: None, // SQLite PRAGMA doesn't return constraint names
                relationship_type: "foreign_key".to_string(),
                confidence: None,
            });
        }
    }

    Ok(relationships)
}

/// Infer relationships based on naming conventions and schema patterns
async fn infer_relationships(
    creds: &super::types::DatabaseCredentials,
    pool: &sqlx::AnyPool,
) -> Result<Vec<Relationship>, DatabaseError> {
    use std::collections::HashMap;

    // Get all tables and their columns with types
    let schemas = get_all_table_schemas(creds, pool).await?;

    // Build a map of potential primary keys: table_name -> [(column_name, data_type)]
    let mut primary_keys: HashMap<String, Vec<(String, String)>> = HashMap::new();
    let mut all_columns: HashMap<String, Vec<(String, String)>> = HashMap::new();

    for schema in &schemas {
        let table_name = &schema.table_name;

        for col in &schema.columns {
            all_columns
                .entry(table_name.clone())
                .or_insert_with(Vec::new)
                .push((col.name.clone(), col.data_type.clone()));

            if col.is_primary_key {
                primary_keys
                    .entry(table_name.clone())
                    .or_insert_with(Vec::new)
                    .push((col.name.clone(), col.data_type.clone()));
            }
        }
    }

    let mut inferred = Vec::new();

    // Pattern matching for common foreign key naming conventions
    for schema in &schemas {
        for col in &schema.columns {
            // Skip if it's a primary key (don't want self-references)
            if col.is_primary_key {
                continue;
            }

            let col_name = col.name.to_lowercase();
            let col_type = &col.data_type;

            // Pattern 1: column ends with "_id" (e.g., user_id, order_id, product_id)
            if col_name.ends_with("_id") {
                let potential_table = col_name.trim_end_matches("_id");

                // Try both singular and plural forms
                let potential_tables = vec![
                    potential_table.to_string(),
                    format!("{}s", potential_table),  // users, orders
                    format!("{}es", potential_table), // addresses
                ];

                for target_table in potential_tables {
                    if let Some(pk_columns) = primary_keys.get(&target_table) {
                        // Check if there's a matching primary key with compatible type
                        for (pk_col, pk_type) in pk_columns {
                            if are_types_compatible(col_type, pk_type) {
                                inferred.push(Relationship {
                                    table_name: schema.table_name.clone(),
                                    column_name: col.name.clone(),
                                    foreign_table: target_table.clone(),
                                    foreign_column: pk_col.clone(),
                                    constraint_name: None,
                                    relationship_type: "inferred".to_string(),
                                    confidence: Some("high".to_string()),
                                });
                                break;
                            }
                        }
                    }
                }
            }

            // Pattern 2: column name matches table_name + "id" or "id" (e.g., userid, orderid)
            // This handles cases without underscores
            if col_name.ends_with("id") && col_name != "id" {
                let potential_table = col_name.trim_end_matches("id");

                let potential_tables = vec![
                    potential_table.to_string(),
                    format!("{}s", potential_table),
                ];

                for target_table in potential_tables {
                    if let Some(pk_columns) = primary_keys.get(&target_table) {
                        for (pk_col, pk_type) in pk_columns {
                            if are_types_compatible(col_type, pk_type) {
                                inferred.push(Relationship {
                                    table_name: schema.table_name.clone(),
                                    column_name: col.name.clone(),
                                    foreign_table: target_table.clone(),
                                    foreign_column: pk_col.clone(),
                                    constraint_name: None,
                                    relationship_type: "inferred".to_string(),
                                    confidence: Some("medium".to_string()),
                                });
                                break;
                            }
                        }
                    }
                }
            }

            // Pattern 3: exact table name match (e.g., column "user" referencing table "users.id")
            for (target_table, pk_columns) in &primary_keys {
                let table_singular = target_table.trim_end_matches('s');

                if col_name == target_table.to_lowercase() || col_name == table_singular.to_lowercase() {
                    for (pk_col, pk_type) in pk_columns {
                        if are_types_compatible(col_type, pk_type) {
                            inferred.push(Relationship {
                                table_name: schema.table_name.clone(),
                                column_name: col.name.clone(),
                                foreign_table: target_table.clone(),
                                foreign_column: pk_col.clone(),
                                constraint_name: None,
                                relationship_type: "inferred".to_string(),
                                confidence: Some("low".to_string()),
                            });
                            break;
                        }
                    }
                }
            }
        }
    }

    Ok(inferred)
}

/// Get schemas for all tables in the database
async fn get_all_table_schemas(
    creds: &super::types::DatabaseCredentials,
    pool: &sqlx::AnyPool,
) -> Result<Vec<TableSchema>, DatabaseError> {
    // Get all table names first
    let tables_query = match creds.db_type {
        DatabaseType::Postgres => {
            "SELECT table_name::text FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')".to_string()
        }
        DatabaseType::MySQL => {
            format!("SELECT table_name FROM information_schema.tables WHERE table_schema = '{}'", creds.database)
        }
        DatabaseType::SQLite => {
            "SELECT name as table_name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'".to_string()
        }
    };

    let table_rows = sqlx::query(&tables_query)
        .fetch_all(pool)
        .await
        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

    let mut table_names: Vec<String> = Vec::new();
    for row in table_rows {
        let table_name: String = row
            .try_get("table_name")
            .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
        table_names.push(table_name);
    }

    // Now get schema for each table
    let mut schemas = Vec::new();

    for table_name in table_names {
        let schema = match creds.db_type {
            DatabaseType::SQLite => {
                // Use PRAGMA for SQLite
                let query = format!("PRAGMA table_info('{}')", table_name);
                let rows = sqlx::query(&query)
                    .fetch_all(pool)
                    .await
                    .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

                let mut columns = Vec::new();
                for row in rows {
                    columns.push(ColumnInfo {
                        name: row
                            .try_get("name")
                            .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
                        data_type: row
                            .try_get("type")
                            .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
                        is_nullable: row.try_get::<i32, _>("notnull").unwrap_or(0) == 0,
                        is_primary_key: row.try_get::<i32, _>("pk").unwrap_or(0) > 0,
                        default_value: row.try_get("dflt_value").ok(),
                    });
                }

                TableSchema {
                    table_name: table_name.clone(),
                    schema: None,
                    columns,
                }
            }
            DatabaseType::Postgres => {
                // Use information_schema for Postgres
                let query = format!(
                    "SELECT
                        c.column_name::text,
                        c.data_type::text,
                        c.is_nullable::text,
                        c.column_default::text,
                        CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT ku.column_name::text
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku
                            ON tc.constraint_name = ku.constraint_name
                            AND tc.table_schema = ku.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                            AND tc.table_name = '{}'
                    ) pk ON c.column_name = pk.column_name
                    WHERE c.table_name = '{}'
                    ORDER BY c.ordinal_position",
                    table_name, table_name
                );

                let rows = sqlx::query(&query)
                    .fetch_all(pool)
                    .await
                    .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

                let mut columns = Vec::new();
                for row in rows {
                    let is_nullable: String = row
                        .try_get("is_nullable")
                        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

                    columns.push(ColumnInfo {
                        name: row
                            .try_get("column_name")
                            .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
                        data_type: row
                            .try_get("data_type")
                            .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
                        is_nullable: is_nullable.to_uppercase() == "YES",
                        is_primary_key: row.try_get("is_primary_key").unwrap_or(false),
                        default_value: row.try_get("column_default").ok(),
                    });
                }

                TableSchema {
                    table_name: table_name.clone(),
                    schema: Some("public".to_string()),
                    columns,
                }
            }
            DatabaseType::MySQL => {
                // Use information_schema for MySQL
                let query = format!(
                    "SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        CASE WHEN column_key = 'PRI' THEN 1 ELSE 0 END as is_primary_key
                    FROM information_schema.columns
                    WHERE table_name = '{}' AND table_schema = '{}'
                    ORDER BY ordinal_position",
                    table_name,
                    creds.database
                );

                let rows = sqlx::query(&query)
                    .fetch_all(pool)
                    .await
                    .map_err(|e| DatabaseError::QueryError(e.to_string()))?;

                let mut columns = Vec::new();
                for row in rows {
                    let is_nullable: String = row
                        .try_get("is_nullable")
                        .map_err(|e| DatabaseError::QueryError(e.to_string()))?;
                    let is_pk: i32 = row.try_get("is_primary_key").unwrap_or(0);

                    columns.push(ColumnInfo {
                        name: row
                            .try_get("column_name")
                            .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
                        data_type: row
                            .try_get("data_type")
                            .map_err(|e| DatabaseError::QueryError(e.to_string()))?,
                        is_nullable: is_nullable.to_uppercase() == "YES",
                        is_primary_key: is_pk > 0,
                        default_value: row.try_get("column_default").ok(),
                    });
                }

                TableSchema {
                    table_name: table_name.clone(),
                    schema: None,
                    columns,
                }
            }
        };

        schemas.push(schema);
    }

    Ok(schemas)
}

/// Check if two data types are compatible for foreign key relationships
fn are_types_compatible(type1: &str, type2: &str) -> bool {
    let t1 = normalize_type(type1);
    let t2 = normalize_type(type2);

    // Exact match
    if t1 == t2 {
        return true;
    }

    // Integer types are compatible with each other
    let int_types = ["int", "integer", "bigint", "smallint", "tinyint", "serial", "bigserial"];
    if int_types.contains(&t1.as_str()) && int_types.contains(&t2.as_str()) {
        return true;
    }

    // String types are compatible
    let string_types = ["varchar", "char", "text", "string"];
    if string_types.contains(&t1.as_str()) && string_types.contains(&t2.as_str()) {
        return true;
    }

    // UUID types
    if t1 == "uuid" && t2 == "uuid" {
        return true;
    }

    false
}

/// Normalize type names for comparison
fn normalize_type(data_type: &str) -> String {
    let lower = data_type.to_lowercase();

    // Remove size specifications like VARCHAR(255) -> varchar
    if let Some(idx) = lower.find('(') {
        lower[..idx].to_string()
    } else {
        lower
    }
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
    table_names: String,
    schema: Option<String>,
    store: State<'_, CredentialStore>,
) -> Result<Vec<TableSchema>, String> {
    get_table_schema(&database_id, &table_names, schema.as_deref(), &store)
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
