import { FiFileText, FiSearch } from 'react-icons/fi'
import { classNames } from '../../utils/classNames'
import { getDocumentTitle } from '../../utils/documentDisplay'
import type { BusyTask, SearchResult, Source } from '../../types'
import styles from '../MainPanel.module.css'

type ResultListProps = {
  busy: BusyTask
  onOpenDocument: (documentId: string) => void
  query: string
  results: SearchResult[]
  selectedSource: Source | null
}

function getRelevanceLabel(score: number) {
  if (score >= 0.72) return 'Strong'
  if (score >= 0.48) return 'Good'
  return 'Related'
}

export function ResultList({ busy, onOpenDocument, query, results, selectedSource }: ResultListProps) {
  const hasQuery = query.trim().length > 0

  return (
    <section className={classNames(styles.section, styles.resultsSection)}>
      <header>
        <div>
          <h2>Results</h2>
          <span>
            {selectedSource ? `${results.length} matches in selected source` : `${results.length} matches`}
          </span>
        </div>
      </header>
      <div className={classNames(styles.list, styles.resultsList)}>
        {results.map((result) => (
          <button
            className={styles.resultRow}
            key={result.chunk_id}
            type="button"
            onClick={() => onOpenDocument(result.document_id)}
            disabled={busy !== null}
          >
            <div className={styles.resultMeta}>
              <span className={styles.resultIcon} aria-hidden="true">
                <FiFileText />
              </span>
              <span>
                <strong>{getDocumentTitle(result)}</strong>
                <small title={result.source_url || result.path}>{result.source_url || result.path}</small>
              </span>
              <b title={`Score ${result.score.toFixed(3)}`}>
                {getRelevanceLabel(result.score)}
                <span style={{ width: `${Math.max(12, Math.min(100, result.score * 100))}%` }} />
              </b>
            </div>
            <p>{result.text}</p>
          </button>
        ))}
        {results.length === 0 ? (
          <div className={styles.emptyState}>
            <FiSearch aria-hidden="true" />
            <strong>{hasQuery ? 'No matches yet' : 'Search this source'}</strong>
            <p>
              {hasQuery
                ? 'Try a more specific function, error message, or configuration term.'
                : 'Ask a concrete docs question to see ranked answer excerpts here.'}
            </p>
          </div>
        ) : null}
      </div>
    </section>
  )
}
