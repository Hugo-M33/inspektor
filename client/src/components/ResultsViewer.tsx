import type { QueryResult } from '../types/database';

interface ResultsViewerProps {
  results: QueryResult;
  sql: string;
}

export function ResultsViewer({ results, sql }: ResultsViewerProps) {
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
    <div className="results-viewer">
      <div className="results-header">
        <div className="results-info">
          <h3>Results</h3>
          <p>
            {results.row_count} row{results.row_count !== 1 ? 's' : ''} returned in{' '}
            {results.execution_time_ms}ms
          </p>
        </div>
        <div className="export-actions">
          <button onClick={handleExportCSV} className="secondary">
            Export CSV
          </button>
          <button onClick={handleExportJSON} className="secondary">
            Export JSON
          </button>
        </div>
      </div>

      <details className="sql-details">
        <summary>View SQL</summary>
        <pre className="sql-code">{sql}</pre>
      </details>

      <div className="results-table-container">
        {results.row_count === 0 ? (
          <p className="empty-results">No results found</p>
        ) : (
          <table className="results-table">
            <thead>
              <tr>
                {results.columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.rows.map((row, idx) => (
                <tr key={idx}>
                  {results.columns.map((col) => (
                    <td key={col}>{formatValue(row[col])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
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
