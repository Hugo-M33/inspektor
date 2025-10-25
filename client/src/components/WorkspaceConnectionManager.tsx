import { useState, useEffect } from 'react';
import { Trash2, Play, Database as DatabaseIcon } from 'lucide-react';
import {
  listWorkspaceConnections,
  addWorkspaceConnection,
  deleteWorkspaceConnection,
  type WorkspaceConnection,
} from '../services/workspaces';
import { encryptConnection, decryptConnection } from '../services/encryption';
import { PasswordPrompt } from './PasswordPrompt';
import { AlertModal } from './AlertModal';
import { ConfirmModal } from './ConfirmModal';
import { testDatabaseConnection, saveCredentials } from '../services/tauri';
import type { DatabaseCredentials, DatabaseType } from '../types/database';

interface WorkspaceConnectionManagerProps {
  workspaceId: string;
  workspaceName: string;
  onSelectConnection: (credentials: DatabaseCredentials) => void;
}

export function WorkspaceConnectionManager({
  workspaceId,
  onSelectConnection,
}: WorkspaceConnectionManagerProps) {
  const [connections, setConnections] = useState<WorkspaceConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [testingConnection, setTestingConnection] = useState<string | null>(null);

  // Password prompts
  const [encryptPassword, setEncryptPassword] = useState<string | null>(null);
  const [decryptPrompt, setDecryptPrompt] = useState<{
    connection: WorkspaceConnection;
    action: 'use' | 'test';
  } | null>(null);

  // Form data
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
  }, [workspaceId]);

  const loadConnections = async () => {
    setLoading(true);
    try {
      const data = await listWorkspaceConnections(workspaceId);
      setConnections(data);
    } catch (error) {
      console.error('Failed to load connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConnection = async (password: string) => {
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
      // Encrypt the credentials
      const encrypted = await encryptConnection(credentials, password);

      // Save to server
      await addWorkspaceConnection(workspaceId, {
        name: credentials.name,
        encrypted_data: encrypted.encrypted_data,
        nonce: encrypted.nonce,
        salt: encrypted.salt,
      });

      // Reset form
      setShowAddForm(false);
      setEncryptPassword(null);
      setFormData({
        name: '',
        db_type: 'postgres',
        database: '',
        host: 'localhost',
        port: 5432,
      });

      // Reload connections
      await loadConnections();
    } catch (error) {
      setAlertModal({
        message: `Failed to save connection: ${error}`,
        type: 'error',
      });
    }
  };

  const handleDecrypt = async (password: string) => {
    if (!decryptPrompt) return;

    try {
      const credentials = await decryptConnection(decryptPrompt.connection, password);

      // Save decrypted credentials to local store temporarily so metadata commands can access them
      await saveCredentials(credentials);

      if (decryptPrompt.action === 'use') {
        onSelectConnection(credentials);
      } else if (decryptPrompt.action === 'test') {
        setTestingConnection(decryptPrompt.connection.id);
        try {
          const result = await testDatabaseConnection(credentials);
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
      }

      setDecryptPrompt(null);
    } catch (error) {
      throw new Error('Decryption failed. Wrong password?');
    }
  };

  const handleDelete = (connectionId: string) => {
    setConfirmModal({
      message: 'Are you sure you want to delete this connection?',
      onConfirm: async () => {
        try {
          await deleteWorkspaceConnection(workspaceId, connectionId);
          await loadConnections();
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

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-text-secondary">Loading connections...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-text-primary">
          Connection Manager
        </h2>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className={'btn ' + (showAddForm ? 'btn-secondary' : 'btn-primary')}
        >
          {showAddForm ? 'Cancel' : '+ Add Connection'}
        </button>
      </div>

      {showAddForm && (
        <div className="card mb-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">New Connection</h3>

          <div className="space-y-4">
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
                      onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
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
                    placeholder="app"
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
              <button
                type="button"
                onClick={() => setEncryptPassword('prompt')}
                disabled={!formData.name}
                className="btn btn-primary"
              >
                Save Connection
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>

            <div className="mt-4 p-3 bg-dark-secondary rounded-lg border border-dark-border">
              <p className="text-xs text-text-tertiary">
                <strong className="text-text-secondary">Loading state example:</strong>
              </p>
              <div className="flex gap-2 mt-2">
                <button className="px-3 py-1.5 text-xs bg-dark-hover text-text-secondary rounded">
                  Testing...
                </button>
                <button className="px-3 py-1.5 text-xs bg-dark-hover text-text-secondary rounded">
                  Saving...
                </button>
              </div>
              <div className="flex gap-2 mt-2">
                <span className="px-2 py-1 text-xs bg-accent-green/20 text-accent-green rounded">
                  Connected
                </span>
                <span className="px-2 py-1 text-xs bg-accent-red/20 text-accent-red rounded">
                  Failed: invalid credentials
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {connections.length === 0 ? (
          <div className="card text-center py-12">
            <DatabaseIcon className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
            <p className="text-text-secondary">No connections in this workspace</p>
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
                  <p className="text-sm text-text-tertiary flex items-center gap-2">
                    <span className="inline-flex items-center gap-1">
                      <span className="w-2 h-2 bg-accent-green rounded-full"></span>
                      Encrypted
                    </span>
                    •
                    <span>Secure</span>
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setDecryptPrompt({ connection: conn, action: 'use' })}
                    className="btn btn-primary flex items-center gap-2"
                  >
                    <Play className="w-4 h-4" />
                    Open
                  </button>
                  <button
                    onClick={() => setDecryptPrompt({ connection: conn, action: 'test' })}
                    disabled={testingConnection === conn.id}
                    className="btn btn-secondary"
                  >
                    {testingConnection === conn.id ? 'Testing...' : 'Test Connection'}
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

      {/* Password prompts */}
      {encryptPassword && (
        <PasswordPrompt
          title="Encrypt Connection"
          message="Enter a password to encrypt this connection. You'll need this password to use the connection later."
          onSubmit={handleSaveConnection}
          onCancel={() => setEncryptPassword(null)}
        />
      )}

      {decryptPrompt && (
        <PasswordPrompt
          title="Decrypt Connection"
          message={`Enter the password for "${decryptPrompt.connection.name}"`}
          onSubmit={handleDecrypt}
          onCancel={() => setDecryptPrompt(null)}
        />
      )}

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
