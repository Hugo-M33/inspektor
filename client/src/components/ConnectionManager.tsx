import { useState, useEffect } from 'react';
import { Trash2, Play, Database as DatabaseIcon } from 'lucide-react';
import type { DatabaseCredentials, DatabaseType } from '../types/database';
import {
  saveCredentials,
  listCredentials,
  deleteCredentials,
  testDatabaseConnection,
} from '../services/tauri';
import { AlertModal } from './AlertModal';
import { ConfirmModal } from './ConfirmModal';

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

  // Modal states
  const [alertModal, setAlertModal] = useState<{
    message: string;
    type: 'info' | 'success' | 'error';
  } | null>(null);
  const [confirmModal, setConfirmModal] = useState<{
    message: string;
    onConfirm: () => void;
  } | null>(null);

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
      setAlertModal({
        message: `Failed to save connection: ${error}`,
        type: 'error',
      });
    }
  };

  const handleTest = async (cred: DatabaseCredentials) => {
    setTestingConnection(cred.id);
    try {
      const result = await testDatabaseConnection(cred);
      setAlertModal({
        message: `${result.success ? 'Success' : 'Failed'}: ${result.message}\n${result.server_version ? `Version: ${result.server_version}` : ''
        }`,
        type: result.success ? 'success' : 'error',
      });
    } catch (error) {
      setAlertModal({
        message: `Connection test failed: ${error}`,
        type: 'error',
      });
    } finally {
      setTestingConnection(null);
    }
  };

  const handleDelete = (id: string) => {
    setConfirmModal({
      message: 'Are you sure you want to delete this connection?',
      onConfirm: async () => {
        try {
          await deleteCredentials(id);
          loadConnections();
          setConfirmModal(null);
        } catch (error) {
          setConfirmModal(null);
          setAlertModal({
            message: `Failed to delete connection: ${error}`,
            type: 'error',
          });
        }
      },
    });
  };

  const handleTypeChange = (type: DatabaseType) => {
    setFormData({
      ...formData,
      db_type: type,
      port: type === 'postgres' ? 5432 : type === 'mysql' ? 3306 : undefined,
    });
  };

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-text-primary">
          Database Connections (Local)
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className={'btn ' + (showForm ? 'btn-secondary' : 'btn-primary')}
        >
          {showForm ? 'Cancel' : '+ Add Connection'}
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">New Connection</h3>

          <form onSubmit={handleSave} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Production DB"
                  required
                  className="input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Type
                </label>
                <select
                  value={formData.db_type}
                  onChange={(e) => handleTypeChange(e.target.value as DatabaseType)}
                  className="input"
                >
                  <option value="postgres">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlite">SQLite</option>
                </select>
              </div>
            </div>

            {formData.db_type === 'sqlite' ? (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Database File Path
                </label>
                <input
                  type="text"
                  value={formData.file_path || ''}
                  onChange={(e) => setFormData({ ...formData, file_path: e.target.value })}
                  placeholder="/path/to/database.db"
                  required
                  className="input"
                />
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Host
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                      placeholder="localhost"
                      required
                      className="input"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Port
                    </label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) =>
                        setFormData({ ...formData, port: parseInt(e.target.value) })
                      }
                      required
                      className="input"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    Database
                  </label>
                  <input
                    type="text"
                    value={formData.database}
                    onChange={(e) => setFormData({ ...formData, database: e.target.value })}
                    placeholder="myapp"
                    required
                    className="input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      value={formData.username || ''}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      placeholder="postgres"
                      required
                      className="input"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Password
                    </label>
                    <input
                      type="password"
                      value={formData.password || ''}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      placeholder="••••••••"
                      required
                      className="input"
                    />
                  </div>
                </div>
              </>
            )}

            <div className="flex gap-3 pt-2">
              <button type="submit" className="btn btn-primary">
                Save Connection
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-3">
        {connections.length === 0 ? (
          <div className="card text-center py-12">
            <DatabaseIcon className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
            <p className="text-text-secondary">No connections configured</p>
            <p className="text-sm text-text-tertiary mt-1">Add a connection to get started</p>
          </div>
        ) : (
          connections.map((conn) => (
            <div key={conn.id} className="card-hover">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <DatabaseIcon className="w-5 h-5 text-accent-blue" />
                    <h4 className="text-lg font-semibold text-text-primary">{conn.name}</h4>
                  </div>
                  <p className="text-sm text-text-tertiary">
                    {conn.db_type} • {conn.database}
                    {conn.host && ` • ${conn.host}:${conn.port}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onSelectConnection(conn.id)}
                    className="btn btn-primary flex items-center gap-2"
                  >
                    <Play className="w-4 h-4" />
                    Use
                  </button>
                  <button
                    onClick={() => handleTest(conn)}
                    disabled={testingConnection === conn.id}
                    className="btn btn-secondary"
                  >
                    {testingConnection === conn.id ? 'Testing...' : 'Test'}
                  </button>
                  <button
                    onClick={() => handleDelete(conn.id)}
                    className="p-2 hover:bg-accent-red/20 rounded-lg transition-colors group"
                    title="Delete connection"
                  >
                    <Trash2 className="w-4 h-4 text-text-tertiary group-hover:text-accent-red" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Alert Modal */}
      {alertModal && (
        <AlertModal
          message={alertModal.message}
          type={alertModal.type}
          onClose={() => setAlertModal(null)}
        />
      )}

      {/* Confirm Modal */}
      {confirmModal && (
        <ConfirmModal
          title="Confirm Deletion"
          message={confirmModal.message}
          confirmText="Delete"
          confirmVariant="danger"
          onConfirm={confirmModal.onConfirm}
          onCancel={() => setConfirmModal(null)}
        />
      )}
    </div>
  );
}
