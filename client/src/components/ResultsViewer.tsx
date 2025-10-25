import { useState } from 'react';
import { Download, Code, ChevronDown, ChevronUp } from 'lucide-react';
import type { QueryResult, DatabaseType } from '../types/database';
import { SQLDisplay } from './SQLDisplay';

interface ResultsViewerProps {
  results: QueryResult;
  sql: string;
  dbType: DatabaseType;
}

export function ResultsViewer({ results, sql, dbType }: ResultsViewerProps) {
  const [showSql, setShowSql] = useState(false);
  const handleExportCSV = () => {
    const csv = [
      results.columns.join(','),
      ...results.rows.map((row) =>
        results.columns.map((col) => JSON.stringify(row[col] ?? '')).join(',')
      ),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query-results-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    const json = JSON.stringify(results.rows, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query-results-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="card space-y-4">
      {/* Header with stats and actions */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-text-primary">
            {results.row_count} row{results.row_count !== 1 ? 's' : ''} returned in {results.execution_time_ms}ms
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            className="btn btn-secondary flex items-center gap-2 text-sm px-3 py-1.5"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
          <button
            onClick={handleExportJSON}
            className="btn btn-secondary flex items-center gap-2 text-sm px-3 py-1.5"
          >
            <Download className="w-4 h-4" />
            Export JSON
          </button>
          <button
            onClick={() => setShowSql(!showSql)}
            className="btn btn-secondary flex items-center gap-2 text-sm px-3 py-1.5"
          >
            <Code className="w-4 h-4" />
            View SQL
            {showSql ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* SQL Display */}
      {showSql && sql && (
        <SQLDisplay sql={sql} dbType={dbType} />
      )}

      {/* Results Table */}
      <div className="border border-dark-border rounded-lg overflow-hidden">
        {results.row_count === 0 ? (
          <div className="text-center py-12">
            <p className="text-text-secondary">Empty result. Try adjusting filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full">
              <thead>
                <tr className="bg-dark-secondary">
                  {results.columns.map((col) => (
                    <th
                      key={col}
                      className="px-4 py-3 text-left text-xs font-semibold text-text-primary uppercase tracking-wider border-b border-dark-border"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-dark-card">
                {results.rows.map((row, idx) => (
                  <tr
                    key={idx}
                    className="hover:bg-dark-hover transition-colors border-b border-dark-border/50 last:border-b-0"
                  >
                    {results.columns.map((col) => (
                      <td key={col} className="px-4 py-3 text-sm text-text-primary whitespace-nowrap">
                        {formatValue(row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return 'NULL';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}
