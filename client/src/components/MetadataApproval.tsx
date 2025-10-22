import { useState } from 'react';
import type { MetadataRequest, QueryResponse } from '../types/database';
import {
  getDatabaseTables,
  getDatabaseTableSchema,
  getDatabaseRelationships,
} from '../services/tauri';
import { submitMetadata, processQuery } from '../services/llm';

interface MetadataApprovalProps {
  databaseId: string;
  metadataRequest: MetadataRequest;
  onApproved: (response: QueryResponse) => void;
  onRejected: () => void;
}

export function MetadataApproval({
  databaseId,
  metadataRequest,
  onApproved,
  onRejected,
}: MetadataApprovalProps) {
  const [loading, setLoading] = useState(false);

  const handleApprove = async () => {
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
          const tableName = metadataRequest.params?.table_name;
          if (!tableName) {
            throw new Error('Table name is required for schema request');
          }
          const schema = await getDatabaseTableSchema(databaseId, tableName);
          metadata = { schema };
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

      // Continue the query processing
      const response = await processQuery(databaseId, '', []);
      onApproved(response);
    } catch (error) {
      console.error(`Failed to gather metadata: ${error}`);
      onRejected();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="metadata-approval">
      <h3>Metadata Request</h3>
      <div className="request-info">
        <p className="reason">{metadataRequest.reason}</p>
        <div className="request-details">
          <strong>Type:</strong> {metadataRequest.metadata_type}
          {metadataRequest.params && Object.keys(metadataRequest.params).length > 0 && (
            <>
              <br />
              <strong>Parameters:</strong> {JSON.stringify(metadataRequest.params)}
            </>
          )}
        </div>
      </div>
      <div className="actions">
        <button onClick={handleApprove} disabled={loading}>
          {loading ? 'Gathering metadata...' : 'Approve'}
        </button>
        <button onClick={onRejected} disabled={loading} className="secondary">
          Reject
        </button>
      </div>
    </div>
  );
}
