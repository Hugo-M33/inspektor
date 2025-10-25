import { useState, useEffect } from 'react';
import { Lock, Plus, Trash2 } from 'lucide-react';
import { listWorkspaces, createWorkspace, deleteWorkspace, type Workspace } from '../services/workspaces';
import { ConfirmModal } from './ConfirmModal';

interface WorkspaceSelectorProps {
  selectedWorkspaceId: string | null;
  onSelectWorkspace: (workspace: Workspace) => void;
  onWorkspacesLoaded?: (workspaces: Workspace[]) => void;
}

export function WorkspaceSelector({
  selectedWorkspaceId,
  onSelectWorkspace,
  onWorkspacesLoaded,
}: WorkspaceSelectorProps) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmModal, setConfirmModal] = useState<{
    message: string;
    onConfirm: () => void;
  } | null>(null);

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listWorkspaces();
      setWorkspaces(data);

      if (onWorkspacesLoaded) {
        onWorkspacesLoaded(data);
      }

      // Auto-select first workspace if none selected and workspaces exist
      if (!selectedWorkspaceId && data.length > 0) {
        onSelectWorkspace(data[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workspaces');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newWorkspaceName.trim()) {
      setError('Workspace name is required');
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const newWorkspace = await createWorkspace(newWorkspaceName.trim());
      setWorkspaces((prev) => [...prev, newWorkspace]);
      setNewWorkspaceName('');
      setShowCreateForm(false);
      onSelectWorkspace(newWorkspace);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create workspace');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteWorkspace = (workspaceId: string) => {
    setConfirmModal({
      message: 'Are you sure you want to delete this workspace and all its connections?',
      onConfirm: async () => {
        try {
          await deleteWorkspace(workspaceId);
          setWorkspaces((prev) => prev.filter((ws) => ws.id !== workspaceId));

          // If deleted workspace was selected, select another one
          if (workspaceId === selectedWorkspaceId) {
            const remaining = workspaces.filter((ws) => ws.id !== workspaceId);
            if (remaining.length > 0) {
              onSelectWorkspace(remaining[0]);
            }
          }
          setConfirmModal(null);
        } catch (err) {
          setConfirmModal(null);
          setError(err instanceof Error ? err.message : 'Failed to delete workspace');
        }
      },
    });
  };

  if (loading) {
    return (
      <div className="text-center py-4">
        <p className="text-sm text-text-tertiary">Loading workspaces...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">
          Workspaces
        </h3>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="p-1 hover:bg-dark-hover rounded transition-colors"
          title="Create new workspace"
        >
          <Plus className="w-4 h-4 text-text-secondary hover:text-accent-blue" />
        </button>
      </div>

      {error && (
        <div className="mb-3 p-2 bg-accent-red/10 border border-accent-red/30 rounded text-xs text-accent-red">
          {error}
        </div>
      )}

      {showCreateForm && (
        <form onSubmit={handleCreateWorkspace} className="mb-3 space-y-2">
          <input
            type="text"
            value={newWorkspaceName}
            onChange={(e) => setNewWorkspaceName(e.target.value)}
            placeholder="Workspace name"
            autoFocus
            disabled={creating}
            className="w-full px-3 py-2 text-sm bg-dark-card border border-dark-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent-blue"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={creating || !newWorkspaceName.trim()}
              className="flex-1 px-3 py-1.5 text-sm bg-accent-blue text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowCreateForm(false);
                setNewWorkspaceName('');
              }}
              disabled={creating}
              className="px-3 py-1.5 text-sm bg-dark-card text-text-secondary border border-dark-border rounded-lg hover:bg-dark-hover"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {workspaces.length === 0 ? (
        <div className="text-center py-6 px-2">
          <p className="text-sm text-text-tertiary mb-1">No workspaces yet</p>
          <p className="text-xs text-text-tertiary/70">Create your first workspace!</p>
        </div>
      ) : (
        <div className="space-y-1">
          {workspaces.map((workspace) => (
            <div
              key={workspace.id}
              onClick={() => onSelectWorkspace(workspace)}
              className={`group px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                workspace.id === selectedWorkspaceId
                  ? 'bg-accent-blue/20 border border-accent-blue/30'
                  : 'bg-dark-card hover:bg-dark-hover border border-transparent'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Lock className="w-3 h-3 text-text-tertiary flex-shrink-0" />
                    <div className={`text-sm font-medium truncate ${
                      workspace.id === selectedWorkspaceId ? 'text-accent-blue' : 'text-text-primary'
                    }`}>
                      {workspace.name}
                    </div>
                  </div>
                  <div className="text-xs text-text-tertiary">
                    {workspace.connection_count} connection{workspace.connection_count !== 1 ? 's' : ''}
                  </div>
                </div>
                {workspaces.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteWorkspace(workspace.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-accent-red/20 rounded transition-all"
                    title="Delete workspace"
                  >
                    <Trash2 className="w-3 h-3 text-accent-red" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
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
