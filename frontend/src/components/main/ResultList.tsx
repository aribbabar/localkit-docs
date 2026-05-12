import type { BusyTask, SearchResult, Source } from '../../types'
import styles from '../MainPanel.module.css'

type ResultListProps = {
  busy: BusyTask
  onOpenDocument: (documentId: string) => void
  results: SearchResult[]
  selectedSource: Source | null
}

export function ResultList({ busy, onOpenDocument, results, selectedSource }: ResultListProps) {
  return (
    <section className={styles.section}>
      <header>
        <h2>Results</h2>
        <span>
          {selectedSource ? `${results.length} matches in selected source` : `${results.length} matches`}
        </span>
      </header>
      <div className={styles.list}>
        {results.map((result) => (
          <button
            className={styles.resultRow}
            key={result.chunk_id}
            type="button"
            onClick={() => onOpenDocument(result.document_id)}
            disabled={busy !== null}
          >
            <div className={styles.resultMeta}>
              <strong>{result.title || result.path}</strong>
              <span>{result.path}</span>
              <b>{result.score.toFixed(3)}</b>
            </div>
            <p>{result.text}</p>
          </button>
        ))}
        {results.length === 0 ? <p className={styles.empty}>No search results.</p> : null}
      </div>
    </section>
  )
}
