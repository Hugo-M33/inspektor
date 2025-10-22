import { useState, useEffect } from 'react';
import type { DatabaseCredentials, DatabaseType } from '../types/database';
import {
  saveCredentials,
  listCredentials,
  deleteCredentials,
  testDatabaseConnection,
} from '../services/tauri';

interface ConnectionManagerProps {
  onSelectConnection: (id: string) => void;
}

export function ConnectionManager({ onSelectConnection }: ConnectionManagerProps) {
  const [connections, setConnections] = useState<DatabaseCredentials[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [testingConnection, setTestingConnection] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<DatabaseCredentials>>({
    name: '',
    db_type: 'postgres',
    database: '',
    host: 'localhost',
    port: 5432,
  });

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    try {
      const conns = await listCredentials();
      setConnections(conns);
    } catch (error) {
      console.error('Failed to load connections:', error);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    const credentials: DatabaseCredentials = {
      id: crypto.randomUUID(),
      name: formData.name!,
      db_type: formData.db_type!,
      database: formData.database!,
      host: formData.host,
      port: formData.port,
      username: formData.username,
      password: formData.password,
      file_path: formData.file_path,
    };

    try {
      await saveCredentials(credentials);
      setShowForm(false);
      setFormData({
        name: '',
        db_type: 'postgres',
        database: '',
        host: 'localhost',
        port: 5432,
      });
      loadConnections();
    } catch (error) {
      alert(`Failed to save connection: ${error}`);
    }
  };

  const handleTest = async (cred: DatabaseCredentials) => {
    setTestingConnection(cred.id);
    try {
      const result = await testDatabaseConnection(cred);
      alert(
        `${result.success ? 'Success' : 'Failed'}: ${result.message}\n${
          result.server_version ? `Version: ${result.server_version}` : ''
        }`
      );
    } catch (error) {
      alert(`Connection test failed: ${error}`);
    } finally {
      setTestingConnection(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this connection?')) {
      try {
        await deleteCredentials(id);
        loadConnections();
      } catch (error) {
        alert(`Failed to delete connection: ${error}`);
      }
    }
  };

  const handleTypeChange = (type: DatabaseType) => {
    setFormData({
      ...formData,
      db_type: type,
      port: type === 'postgres' ? 5432 : type === 'mysql' ? 3306 : undefined,
    });
  };

  return (
    <div className="connection-manager">
      <div className="header">
        <h2>Database Connections</h2>
        <button onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ New Connection'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSave} className="connection-form">
          <h3>New Connection</h3>

          <label>
            Name:
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </label>

          <label>
            Database Type:
            <select
              value={formData.db_type}
              onChange={(e) => handleTypeChange(e.target.value as DatabaseType)}
            >
              <option value="postgres">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
            </select>
          </label>

          {formData.db_type === 'sqlite' ? (
            <label>
              Database File Path:
              <input
                type="text"
                value={formData.file_path || ''}
                onChange={(e) => setFormData({ ...formData, file_path: e.target.value })}
                placeholder="/path/to/database.db"
                required
              />
            </label>
          ) : (
            <>
              <label>
                Host:
                <input
                  type="text"
                  value={formData.host}
                  onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                  required
                />
              </label>

              <label>
                Port:
                <input
                  type="number"
                  value={formData.port}
                  onChange={(e) =>
                    setFormData({ ...formData, port: parseInt(e.target.value) })
                  }
                  required
                />
              </label>

              <label>
                Database Name:
                <input
                  type="text"
                  value={formData.database}
                  onChange={(e) => setFormData({ ...formData, database: e.target.value })}
                  required
                />
              </label>

              <label>
                Username:
                <input
                  type="text"
                  value={formData.username || ''}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                />
              </label>

              <label>
                Password:
                <input
                  type="password"
                  value={formData.password || ''}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                />
              </label>

              {formData.db_type === 'postgres' && (
                <label>
                  Schema (optional):
                  <input
                    type="text"
                    value={formData.schema || ''}
                    onChange={(e) => setFormData({ ...formData, schema: e.target.value })}
                    placeholder="public"
                  />
                </label>
              )}
            </>
          )}

          <button type="submit">Save Connection</button>
        </form>
      )}

      <div className="connections-list">
        {connections.length === 0 ? (
          <p className="empty-state">No connections configured</p>
        ) : (
          connections.map((conn) => (
            <div key={conn.id} className="connection-item">
              <div className="connection-info">
                <h4>{conn.name}</h4>
                <p>
                  {conn.db_type} - {conn.database}
                  {conn.host && ` @ ${conn.host}:${conn.port}`}
                </p>
              </div>
              <div className="connection-actions">
                <button onClick={() => onSelectConnection(conn.id)}>Use</button>
                <button
                  onClick={() => handleTest(conn)}
                  disabled={testingConnection === conn.id}
                >
                  {testingConnection === conn.id ? 'Testing...' : 'Test'}
                </button>
                <button onClick={() => handleDelete(conn.id)} className="danger">
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
