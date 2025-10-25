import { useState, useEffect } from 'react';
import { Shield, Database, LogOut } from 'lucide-react';
import './App.css';
import { ConnectionManager } from './components/ConnectionManager';
import { WorkspaceSelector } from './components/WorkspaceSelector';
import { WorkspaceConnectionManager } from './components/WorkspaceConnectionManager';
import { QueryInterface } from './components/QueryInterface';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { AlertModal } from './components/AlertModal';
import { getCredentials } from './services/tauri';
import { checkHealth } from './services/llm';
import { getAuthState, logout, type User } from './services/auth';
import type { Workspace } from './services/workspaces';
import type { DatabaseCredentials } from './types/database';

type AuthView = 'login' | 'register';
type ViewMode = 'local' | 'workspace';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authView, setAuthView] = useState<AuthView>('login');
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('workspace');

  // Workspace state
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [selectedWorkspaceConnection, setSelectedWorkspaceConnection] = useState<DatabaseCredentials | null>(null);

  // Local connection state (legacy)
  const [selectedConnection, setSelectedConnection] = useState<string | null>(null);
  const [connectionName, setConnectionName] = useState<string>('');
  const [connectionDbType, setConnectionDbType] = useState<DatabaseCredentials['db_type'] | null>(null);

  const [llmServerStatus, setLlmServerStatus] = useState<'checking' | 'online' | 'offline'>(
    'checking'
  );

  // Alert modal state
  const [alertModal, setAlertModal] = useState<{
    message: string;
    type: 'info' | 'success' | 'error';
  } | null>(null);

  useEffect(() => {
    // Check authentication status on startup
    checkAuthStatus();

    // Check LLM server health on startup
    checkHealth()
      .then((response) => {
        console.log('LLM Server health:', response);
        setLlmServerStatus('online');
      })
      .catch((error) => {
        console.error('LLM Server health check failed:', error);
        setLlmServerStatus('offline');
      });
  }, []);

  const checkAuthStatus = async () => {
    try {
      const authState = await getAuthState();
      if (authState.isAuthenticated && authState.user) {
        setUser(authState.user);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setCheckingAuth(false);
    }
  };

  const handleLogin = (loggedInUser: User) => {
    setUser(loggedInUser);
  };

  const handleRegister = (registeredUser: User) => {
    setUser(registeredUser);
  };

  const handleLogout = async () => {
    try {
      await logout();
      setUser(null);
      setSelectedConnection(null);
      setConnectionName('');
      setConnectionDbType(null);
      setSelectedWorkspace(null);
      setSelectedWorkspaceConnection(null);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  // Local connection handlers (legacy)
  const handleSelectConnection = async (id: string) => {
    try {
      const creds = await getCredentials(id);
      setSelectedConnection(id);
      setConnectionName(creds.name);
      setConnectionDbType(creds.db_type);
    } catch (error) {
      setAlertModal({
        message: `Failed to load connection: ${error}`,
        type: 'error',
      });
    }
  };

  // Workspace connection handlers
  const handleSelectWorkspaceConnection = (credentials: DatabaseCredentials) => {
    setSelectedWorkspaceConnection(credentials);
  };

  const handleBackToConnections = () => {
    setSelectedConnection(null);
    setConnectionName('');
    setConnectionDbType(null);
    setSelectedWorkspaceConnection(null);
  };

  // Show loading state while checking authentication
  if (checkingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-dark-primary via-dark-secondary to-dark-primary">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-text-primary mb-4">Inspektor</h1>
          <p className="text-text-secondary">Loading...</p>
        </div>
      </div>
    );
  }

  // Show login/register if not authenticated
  if (!user) {
    if (authView === 'login') {
      return <Login onLogin={handleLogin} onSwitchToRegister={() => setAuthView('register')} />;
    } else {
      return <Register onRegister={handleRegister} onSwitchToLogin={() => setAuthView('login')} />;
    }
  }

  // Main app for authenticated users
  return (
    <div className="min-h-screen bg-dark-primary flex flex-col">
      {/* Header */}
      <header className="bg-dark-secondary border-b border-dark-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-6 h-6 text-accent-blue" />
            <h1 className="text-xl font-bold text-text-primary">Inspektor</h1>
          </div>

          <div className="flex items-center gap-6">
            {/* LLM Server Status */}
            <div className="flex items-center gap-2">
              <div className={`status-dot-${llmServerStatus}`}></div>
              <span className="text-sm text-text-secondary">
                LLM Server: <span className={llmServerStatus === 'online' ? 'text-accent-green' : llmServerStatus === 'offline' ? 'text-accent-red' : 'text-accent-orange'}>{llmServerStatus}</span>
              </span>
            </div>

            {/* User Info */}
            <div className="flex items-center gap-3">
              <span className="text-sm text-text-secondary">{user.email}</span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-3 py-1.5 bg-accent-red/10 hover:bg-accent-red/20 text-accent-red rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm font-medium">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-dark-secondary border-r border-dark-border p-4 overflow-y-auto custom-scrollbar">
          <div className="mb-6">
            <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">
              Workspace Mode
            </h3>

            {/* View Mode Toggle */}
            <div className="flex flex-col gap-2">
              <button
                onClick={() => setViewMode('workspace')}
                className={`px-4 py-2.5 rounded-lg text-left flex items-center gap-2 transition-colors ${
                  viewMode === 'workspace'
                    ? 'bg-accent-blue text-white'
                    : 'bg-dark-card text-text-secondary hover:bg-dark-hover hover:text-text-primary'
                }`}
              >
                <Database className="w-4 h-4" />
                <div className="flex-1">
                  <div className="text-sm font-medium">Cloud Workspaces</div>
                  <div className="text-xs opacity-75">Encrypted</div>
                </div>
              </button>

              <button
                onClick={() => setViewMode('local')}
                className={`px-4 py-2.5 rounded-lg text-left flex items-center gap-2 transition-colors ${
                  viewMode === 'local'
                    ? 'bg-accent-blue text-white'
                    : 'bg-dark-card text-text-secondary hover:bg-dark-hover hover:text-text-primary'
                }`}
              >
                <Database className="w-4 h-4" />
                <div className="flex-1">
                  <div className="text-sm font-medium">Local Connections</div>
                  <div className="text-xs opacity-75">Legacy</div>
                </div>
              </button>
            </div>
          </div>

          {/* Workspace/Connection List in Sidebar */}
          {viewMode === 'workspace' && !selectedWorkspaceConnection && (
            <WorkspaceSelector
              selectedWorkspaceId={selectedWorkspace?.id || null}
              onSelectWorkspace={setSelectedWorkspace}
            />
          )}
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto custom-scrollbar">
          {llmServerStatus === 'offline' && (
            <div className="m-6 p-4 bg-accent-orange/10 border border-accent-orange/30 rounded-lg">
              <p className="text-sm text-accent-orange">
                Warning: LLM server is offline. Please start the Python server to use natural language queries.
              </p>
            </div>
          )}

          <div className="p-6">
            {viewMode === 'workspace' ? (
              // Workspace mode
              <>
                {!selectedWorkspaceConnection ? (
                  <>
                    {selectedWorkspace && (
                      <WorkspaceConnectionManager
                        workspaceId={selectedWorkspace.id}
                        workspaceName={selectedWorkspace.name}
                        onSelectConnection={handleSelectWorkspaceConnection}
                      />
                    )}
                  </>
                ) : (
                  <div>
                    <button
                      onClick={handleBackToConnections}
                      className="mb-4 px-4 py-2 text-accent-blue hover:text-blue-400 transition-colors"
                    >
                      ← Back to Connections
                    </button>
                    <QueryInterface
                      databaseId={selectedWorkspaceConnection.id}
                      databaseName={selectedWorkspaceConnection.name}
                      dbType={selectedWorkspaceConnection.db_type}
                      workspaceId={selectedWorkspace?.id}
                    />
                  </div>
                )}
              </>
            ) : (
              // Local mode (legacy)
              <>
                {!selectedConnection ? (
                  <ConnectionManager onSelectConnection={handleSelectConnection} />
                ) : (
                  <div>
                    <button
                      onClick={handleBackToConnections}
                      className="mb-4 px-4 py-2 text-accent-blue hover:text-blue-400 transition-colors"
                    >
                      ← Back to Connections
                    </button>
                    <QueryInterface databaseId={selectedConnection} databaseName={connectionName} dbType={connectionDbType!} />
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </div>

      {/* Alert Modal */}
      {alertModal && (
        <AlertModal
          message={alertModal.message}
          type={alertModal.type}
          onClose={() => setAlertModal(null)}
        />
      )}
    </div>
  );
}

export default App;
