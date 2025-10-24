import { useState, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import type { MetadataRequest, QueryResponse } from '../types/database';
import {
  getDatabaseTables,
  getDatabaseTableSchema,
  getDatabaseRelationships,
} from '../services/tauri';
import { submitMetadata, processQuery } from '../services/llm';

interface MetadataApprovalProps {
  databaseId: string;
  conversationId: string;
  originalQuery: string;
  metadataRequest: MetadataRequest;
  onApproved: (response: QueryResponse, wasAutoApproved?: boolean) => void;
  onRejected: () => void;
  autoMode?: boolean;
  maxAutoApprovals?: number;
  currentAutoApprovalCount?: number;
}

export function MetadataApproval({
  databaseId,
  conversationId,
  originalQuery,
  metadataRequest,
  onApproved,
  onRejected,
  autoMode = false,
  maxAutoApprovals = 5,
  currentAutoApprovalCount = 0,
}: MetadataApprovalProps) {
  const [loading, setLoading] = useState(false);
  const [isAutoApproving, setIsAutoApproving] = useState(false);

  // Auto-approve metadata requests when auto mode is enabled
  useEffect(() => {
    const shouldAutoApprove =
      autoMode &&
      !loading &&
      !isAutoApproving &&
      currentAutoApprovalCount < maxAutoApprovals;

    if (shouldAutoApprove) {
      setIsAutoApproving(true);
      handleApprove(true);
    }
  }, [autoMode, maxAutoApprovals, currentAutoApprovalCount]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleApprove = async (isAuto: boolean = false) => {
    setLoading(true);

    try {
      let metadata: any;

      // Gather the requested metadata
      switch (metadataRequest.metadata_type) {
        case 'tables':
          const tables = await getDatabaseTables(databaseId);
          console.log(tables)
          metadata = { tables: tables.map((t) => t.name) };
          break;

        case 'schema':
          console.log(metadataRequest)
          const tableNames = metadataRequest.params?.tables;
          if (!Array.isArray(tableNames) || tableNames.length < 1) {
            throw new Error('At least one table name is required for schema request');
          }

          const schemas = await getDatabaseTableSchema(databaseId, `(${tableNames.map(tableName => `'${tableName}'`).join(', ')})`);

          // Convert schema array to dictionary format expected by the agent
          // Tauri returns: [{ table_name: "users", columns: [...] }, ...]
          // Agent expects: { "users": [...columns...], ... }
          // Don't wrap in { schema: ... } because metadata_type="schema" already provides the key
          const schemaDict: Record<string, any> = {};
          schemas.forEach((tableSchema: any) => {
            schemaDict[tableSchema.table_name] = tableSchema.columns;
          });

          metadata = schemaDict;
          break;

        case 'relationships':
          const relationships = await getDatabaseRelationships(databaseId);
          metadata = { relationships };
          break;

        default:
          throw new Error(`Unknown metadata type: ${metadataRequest.metadata_type}`);
      }

      // Submit metadata to LLM server
      await submitMetadata(databaseId, metadataRequest.metadata_type, metadata);

      // Now re-query the LLM with empty query to continue the conversation
      // Empty query means: "continue with the conversation history and new metadata"
      // The server won't add another user message, just processes with updated metadata
      const response = await processQuery(databaseId, '', conversationId);

      // Pass the response back to parent with auto-approval flag
      onApproved(response, isAuto);
    } catch (error) {
      console.error(`Failed to gather metadata: ${error}`);
      onRejected();
    } finally {
      setLoading(false);
      setIsAutoApproving(false);
    }
  };

  return (
    <Transition appear show={true} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={() => !loading && onRejected()}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-dark-card border border-dark-border shadow-2xl transition-all">
                <div className="p-6">
                  {/* Header */}
                  <div className="flex items-start gap-4 mb-4">
                    <div className={`p-3 rounded-full ${isAutoApproving ? 'bg-accent-green/20' : 'bg-accent-blue/20'}`}>
                      {isAutoApproving ? (
                        <CheckCircle className="w-6 h-6 text-accent-green" />
                      ) : (
                        <AlertTriangle className="w-6 h-6 text-accent-blue" />
                      )}
                    </div>
                    <div className="flex-1">
                      <Dialog.Title className="text-lg font-semibold text-text-primary">
                        Metadata Request
                      </Dialog.Title>
                      {isAutoApproving && (
                        <p className="text-sm text-accent-green mt-1">(Auto-approving...)</p>
                      )}
                    </div>
                  </div>

                  {/* Content */}
                  <div className="space-y-4">
                    <p className="text-text-primary leading-relaxed">
                      {metadataRequest.reason}
                    </p>

                    <div className="bg-dark-secondary rounded-lg p-4 space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="text-sm font-medium text-text-secondary min-w-[80px]">Type:</span>
                        <span className="text-sm text-text-primary font-mono">{metadataRequest.metadata_type}</span>
                      </div>

                      {metadataRequest.params && Object.keys(metadataRequest.params).length > 0 && (
                        <>
                          <div className="flex items-start gap-2">
                            <span className="text-sm font-medium text-text-secondary min-w-[80px]">Scope:</span>
                            <span className="text-sm text-text-primary">
                              {metadataRequest.params.tables ? 'public' : 'database'}
                            </span>
                          </div>
                          {metadataRequest.params.tables && (
                            <div className="flex items-start gap-2">
                              <span className="text-sm font-medium text-text-secondary min-w-[80px]">Limit:</span>
                              <span className="text-sm text-text-primary">
                                {Array.isArray(metadataRequest.params.tables) ? metadataRequest.params.tables.length : '50'}
                              </span>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {/* Auto-approval status */}
                    {autoMode && currentAutoApprovalCount >= maxAutoApprovals && (
                      <div className="flex items-start gap-2 p-3 bg-accent-orange/10 border border-accent-orange/30 rounded-lg">
                        <AlertTriangle className="w-5 h-5 text-accent-orange flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-accent-orange">
                            Auto-approval limit reached ({currentAutoApprovalCount}/{maxAutoApprovals})
                          </p>
                          <p className="text-xs text-accent-orange/80 mt-1">
                            Further actions require manual approval.
                          </p>
                        </div>
                      </div>
                    )}

                    {autoMode && currentAutoApprovalCount < maxAutoApprovals && (
                      <div className="text-sm text-text-tertiary">
                        Auto-approval: {currentAutoApprovalCount + 1}/{maxAutoApprovals}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 mt-6">
                    <button
                      onClick={() => handleApprove(false)}
                      disabled={loading}
                      className="btn-primary flex-1 flex items-center justify-center gap-2"
                    >
                      <CheckCircle className="w-4 h-4" />
                      {loading ? (isAutoApproving ? 'Auto-gathering...' : 'Gathering...') : 'Approve'}
                    </button>
                    <button
                      onClick={onRejected}
                      disabled={loading}
                      className="btn-danger flex items-center justify-center gap-2 px-6"
                    >
                      <XCircle className="w-4 h-4" />
                      Reject
                    </button>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
