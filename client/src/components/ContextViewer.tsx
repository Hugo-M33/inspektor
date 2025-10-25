import { useState, useEffect } from 'react';
import { Brain, X, Edit2, Save, XCircle, Database, Link2, Code, Briefcase, Zap, RefreshCw } from 'lucide-react';
import { getWorkspaceContext, updateWorkspaceContext, type ContextData } from '../services/context';

interface ContextViewerProps {
  workspaceId: string;
  onClose: () => void;
}

export function ContextViewer({ workspaceId, onClose }: ContextViewerProps) {
  const [context, setContext] = useState<ContextData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editedContext, setEditedContext] = useState<ContextData | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadContext();
  }, [workspaceId]);

  const loadContext = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getWorkspaceContext(workspaceId);
      setContext(data.context_data);
      setEditedContext(data.context_data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load context');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editedContext) return;

    setSaving(true);
    setError(null);

    try {
      await updateWorkspaceContext(workspaceId, editedContext);
      setContext(editedContext);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save context');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditedContext(context);
    setEditing(false);
    setError(null);
  };

  const updateField = <K extends keyof ContextData>(
    field: K,
    value: ContextData[K]
  ) => {
    if (!editedContext) return;
    setEditedContext({ ...editedContext, [field]: value });
  };

  if (loading) {
    return (
      <div className="fixed inset-y-0 right-0 w-[500px] bg-dark-secondary border-l border-dark-border z-50 overflow-y-auto custom-scrollbar">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 text-accent-blue animate-spin mx-auto mb-2" />
            <p className="text-sm text-text-secondary">Loading context...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !context) {
    return (
      <div className="fixed inset-y-0 right-0 w-[500px] bg-dark-secondary border-l border-dark-border z-50 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary">Context</h3>
          <button onClick={onClose} className="p-1 hover:bg-dark-hover rounded transition-colors">
            <X className="w-5 h-5 text-text-secondary" />
          </button>
        </div>
        <div className="p-4 bg-accent-orange/10 border border-accent-orange/30 rounded-lg text-center">
          <Brain className="w-12 h-12 text-accent-orange mx-auto mb-3 opacity-50" />
          <p className="text-sm text-accent-orange mb-2">{error}</p>
          <p className="text-xs text-text-tertiary">
            Context will be created when you mark a query as satisfactory
          </p>
        </div>
      </div>
    );
  }

  const contextToDisplay = editing ? editedContext : context;
  if (!contextToDisplay) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-[500px] bg-dark-secondary border-l border-dark-border z-50 overflow-y-auto custom-scrollbar">
      <div className="sticky top-0 bg-dark-secondary border-b border-dark-border p-4 z-10">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-accent-purple" />
            <h3 className="text-lg font-semibold text-text-primary">Workspace Context</h3>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-dark-hover rounded transition-colors">
            <X className="w-5 h-5 text-text-secondary" />
          </button>
        </div>
        <p className="text-xs text-text-tertiary">
          Shared knowledge across all conversations in this workspace
        </p>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="btn btn-secondary text-sm mt-3 flex items-center gap-2"
          >
            <Edit2 className="w-4 h-4" />
            Edit Context
          </button>
        )}
        {editing && (
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn btn-success text-sm flex items-center gap-2 flex-1"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button
              onClick={handleCancel}
              className="btn btn-secondary text-sm flex items-center gap-2"
            >
              <XCircle className="w-4 h-4" />
              Cancel
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="mx-4 mt-4 p-3 bg-accent-red/10 border border-accent-red/30 rounded text-sm text-accent-red">
          {error}
        </div>
      )}

      <div className="p-4 space-y-6">
        {/* Tables Used */}
        <Section
          icon={Database}
          title="Tables Used"
          color="text-accent-blue"
          isEmpty={contextToDisplay.tables_used.length === 0}
        >
          {editing ? (
            <textarea
              value={contextToDisplay.tables_used.join(', ')}
              onChange={(e) =>
                updateField(
                  'tables_used',
                  e.target.value.split(',').map((t) => t.trim()).filter(Boolean)
                )
              }
              className="input text-sm resize-none"
              rows={2}
              placeholder="table1, table2, table3"
            />
          ) : (
            <div className="flex flex-wrap gap-2">
              {contextToDisplay.tables_used.map((table) => (
                <span
                  key={table}
                  className="px-2 py-1 bg-accent-blue/20 text-accent-blue rounded text-sm font-mono"
                >
                  {table}
                </span>
              ))}
            </div>
          )}
        </Section>

        {/* Relationships */}
        <Section
          icon={Link2}
          title="Relationships"
          color="text-accent-green"
          isEmpty={contextToDisplay.relationships.length === 0}
        >
          {editing ? (
            <div className="space-y-2">
              {contextToDisplay.relationships.map((rel, idx) => (
                <div key={idx} className="flex gap-2 items-center text-sm">
                  <input
                    value={`${rel.from_table}.${rel.from_column}`}
                    onChange={(e) => {
                      const [table, column] = e.target.value.split('.');
                      const updated = [...contextToDisplay.relationships];
                      updated[idx] = { ...rel, from_table: table || '', from_column: column || '' };
                      updateField('relationships', updated);
                    }}
                    className="input flex-1 text-xs"
                    placeholder="table.column"
                  />
                  <span>→</span>
                  <input
                    value={`${rel.to_table}.${rel.to_column}`}
                    onChange={(e) => {
                      const [table, column] = e.target.value.split('.');
                      const updated = [...contextToDisplay.relationships];
                      updated[idx] = { ...rel, to_table: table || '', to_column: column || '' };
                      updateField('relationships', updated);
                    }}
                    className="input flex-1 text-xs"
                    placeholder="table.column"
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {contextToDisplay.relationships.map((rel, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm text-text-secondary">
                  <code className="text-accent-green">{rel.from_table}.{rel.from_column}</code>
                  <span>→</span>
                  <code className="text-accent-green">{rel.to_table}.{rel.to_column}</code>
                  <span className="text-xs text-text-tertiary">({rel.type})</span>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Column Typecast Hints */}
        <Section
          icon={Code}
          title="Typecast Hints"
          color="text-accent-orange"
          isEmpty={contextToDisplay.column_typecast_hints.length === 0}
        >
          <div className="space-y-3">
            {contextToDisplay.column_typecast_hints.map((hint, idx) => (
              <div key={idx} className="bg-dark-card p-3 rounded border border-dark-border">
                {editing ? (
                  <>
                    <input
                      value={`${hint.table}.${hint.column}`}
                      className="input text-xs mb-2"
                      placeholder="table.column"
                      onChange={(e) => {
                        const [table, column] = e.target.value.split('.');
                        const updated = [...contextToDisplay.column_typecast_hints];
                        updated[idx] = { ...hint, table: table || '', column: column || '' };
                        updateField('column_typecast_hints', updated);
                      }}
                    />
                    <textarea
                      value={hint.hint}
                      className="input text-xs resize-none"
                      rows={2}
                      placeholder="Hint"
                      onChange={(e) => {
                        const updated = [...contextToDisplay.column_typecast_hints];
                        updated[idx] = { ...hint, hint: e.target.value };
                        updateField('column_typecast_hints', updated);
                      }}
                    />
                  </>
                ) : (
                  <>
                    <div className="flex items-center gap-2 mb-1">
                      <code className="text-sm font-mono text-accent-orange">
                        {hint.table}.{hint.column}
                      </code>
                    </div>
                    <p className="text-sm text-text-secondary">{hint.hint}</p>
                    {hint.example && (
                      <code className="text-xs text-text-tertiary mt-2 block">
                        Example: {hint.example}
                      </code>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </Section>

        {/* Business Context */}
        <Section
          icon={Briefcase}
          title="Business Rules"
          color="text-accent-purple"
          isEmpty={contextToDisplay.business_context.length === 0}
        >
          {editing ? (
            <textarea
              value={contextToDisplay.business_context.join('\n')}
              onChange={(e) =>
                updateField(
                  'business_context',
                  e.target.value.split('\n').filter(Boolean)
                )
              }
              className="input text-sm resize-none"
              rows={6}
              placeholder="One rule per line&#10;Example: Active users are those who logged in within 30 days&#10;Example: Premium tier is tier='premium' in users table"
            />
          ) : (
            <ul className="space-y-2">
              {contextToDisplay.business_context.map((rule, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-text-secondary">
                  <span className="text-accent-purple mt-0.5">•</span>
                  <span>{rule}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        {/* SQL Patterns */}
        <Section
          icon={Zap}
          title="SQL Patterns"
          color="text-accent-yellow"
          isEmpty={contextToDisplay.sql_patterns.length === 0}
        >
          <div className="space-y-3">
            {contextToDisplay.sql_patterns.map((pattern, idx) => (
              <div key={idx} className="bg-dark-card p-3 rounded border border-dark-border">
                {editing ? (
                  <>
                    <input
                      value={pattern.pattern}
                      className="input text-xs mb-2"
                      placeholder="Pattern name"
                      onChange={(e) => {
                        const updated = [...contextToDisplay.sql_patterns];
                        updated[idx] = { ...pattern, pattern: e.target.value };
                        updateField('sql_patterns', updated);
                      }}
                    />
                    <textarea
                      value={pattern.example || ''}
                      className="input text-xs font-mono resize-none"
                      rows={2}
                      placeholder="SQL example"
                      onChange={(e) => {
                        const updated = [...contextToDisplay.sql_patterns];
                        updated[idx] = { ...pattern, example: e.target.value };
                        updateField('sql_patterns', updated);
                      }}
                    />
                  </>
                ) : (
                  <>
                    <div className="text-sm font-medium text-text-primary mb-1">
                      {pattern.pattern}
                    </div>
                    {pattern.example && (
                      <pre className="text-xs bg-dark-secondary p-2 rounded font-mono text-text-secondary overflow-x-auto">
                        {pattern.example}
                      </pre>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}

interface SectionProps {
  icon: React.ElementType;
  title: string;
  color: string;
  isEmpty: boolean;
  children: React.ReactNode;
}

function Section({ icon: Icon, title, color, isEmpty, children }: SectionProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Icon className={`w-4 h-4 ${color}`} />
        <h4 className="text-sm font-semibold text-text-primary">{title}</h4>
      </div>
      {isEmpty ? (
        <p className="text-sm text-text-tertiary italic">No {title.toLowerCase()} yet</p>
      ) : (
        children
      )}
    </div>
  );
}
