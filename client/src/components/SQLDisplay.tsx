import { format } from 'sql-formatter';
import { Highlight, themes } from 'prism-react-renderer';
import type { DatabaseType } from '../types/database';

interface SQLDisplayProps {
  sql: string;
  dbType?: DatabaseType;
  className?: string;
}

// Map DatabaseType to sql-formatter language
function mapDbTypeToFormatterLanguage(dbType?: DatabaseType): 'postgresql' | 'mysql' | 'sqlite' | 'sql' {
  switch (dbType) {
    case 'postgres':
      return 'postgresql';
    case 'mysql':
      return 'mysql';
    case 'sqlite':
      return 'sqlite';
    default:
      return 'sql'; // fallback to generic SQL
  }
}

export function SQLDisplay({ sql: sqlQuery, dbType, className = '' }: SQLDisplayProps) {
  // Format the SQL query with the appropriate dialect
  const formattedSQL = format(sqlQuery, {
    language: mapDbTypeToFormatterLanguage(dbType),
    tabWidth: 2,
    keywordCase: 'upper',
    linesBetweenQueries: 2,
  });

  return (
    <div className={`rounded border border-dark-border overflow-hidden ${className}`}>
      <Highlight
        theme={themes.vsDark}
        code={formattedSQL}
        language="sql"
      >
        {({ className: highlightClassName, style, tokens, getLineProps, getTokenProps }) => (
          <pre
            className={highlightClassName}
            style={{
              ...style,
              margin: 0,
              padding: '12px',
              background: '#1a1a1a',
              fontSize: '12px',
              lineHeight: '1.5',
              overflowX: 'auto',
            }}
          >
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line })}>
                {line.map((token, key) => (
                  <span key={key} {...getTokenProps({ token })} />
                ))}
              </div>
            ))}
          </pre>
        )}
      </Highlight>
    </div>
  );
}
