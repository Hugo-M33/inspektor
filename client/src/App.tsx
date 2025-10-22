import { useState, useEffect } from 'react';
import './App.css';
import { ConnectionManager } from './components/ConnectionManager';
import { QueryInterface } from './components/QueryInterface';
import { getCredentials } from './services/tauri';
import { checkHealth } from './services/llm';

function App() {
  const [selectedConnection, setSelectedConnection] = useState<string | null>(null);
  const [connectionName, setConnectionName] = useState<string>('');
  const [llmServerStatus, setLlmServerStatus] = useState<'checking' | 'online' | 'offline'>(
    'checking'
  );

  useEffect(() => {
    // Check LLM server health on startup
    checkHealth()
      .then(() => setLlmServerStatus('online'))
      .catch(() => setLlmServerStatus('offline'));
  }, []);

  const handleSelectConnection = async (id: string) => {
    try {
      const creds = await getCredentials(id);
      setSelectedConnection(id);
      setConnectionName(creds.name);
    } catch (error) {
      alert(`Failed to load connection: ${error}`);
    }
  };

  const handleBackToConnections = () => {
    setSelectedConnection(null);
    setConnectionName('');
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Inspektor</h1>
        <div className="status-indicators">
          <span className={`status ${llmServerStatus}`}>
            LLM Server: {llmServerStatus}
          </span>
        </div>
      </header>

      <main className="app-main">
        {llmServerStatus === 'offline' && (
          <div className="warning-banner">
            Warning: LLM server is offline. Please start the Python server to use natural
            language queries.
          </div>
        )}

        {!selectedConnection ? (
          <ConnectionManager onSelectConnection={handleSelectConnection} />
        ) : (
          <div className="query-section">
            <button onClick={handleBackToConnections} className="back-button">
              ← Back to Connections
            </button>
            <QueryInterface databaseId={selectedConnection} databaseName={connectionName} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
