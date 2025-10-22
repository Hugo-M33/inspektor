mod db;

use db::credentials::CredentialStore;

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(CredentialStore::new())
        .invoke_handler(tauri::generate_handler![
            greet,
            // Credential management
            db::credentials::save_credentials,
            db::credentials::get_credentials,
            db::credentials::list_credentials,
            db::credentials::delete_credentials,
            db::credentials::update_credentials,
            // Connection testing
            db::connection::test_database_connection,
            // Query execution
            db::query::execute_sql_query,
            // Metadata extraction
            db::metadata::get_database_tables,
            db::metadata::get_database_table_schema,
            db::metadata::get_database_relationships,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
