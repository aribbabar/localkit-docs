import { Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { classNames } from '../../utils/classNames'
import type { BusyTask, Source } from '../../types'
import controls from '../controls.module.css'
import styles from '../MainPanel.module.css'

type SourceListProps = {
  busy: BusyTask
  onReindex: (sourceId: string) => void
  onRemove: (sourceId: string) => void
  onSelectSource: (sourceId: string) => void
  sources: Source[]
}

export function SourceList({ busy, onReindex, onRemove, onSelectSource, sources }: SourceListProps) {
  return (
    <section className={styles.section}>
      <header>
        <h2>Sources</h2>
        <span>{sources.length} total</span>
      </header>
      <div className={styles.list}>
        {sources.map((source) => (
          <article className={styles.sourceRow} key={source.id}>
            <button
              className={styles.sourceSelectButton}
              type="button"
              onClick={() => onSelectSource(source.id)}
              disabled={busy !== null}
            >
              <span className={styles.sourceCopy}>
                <strong>{source.name}</strong>
                <span>{source.origin}</span>
              </span>
              <span className={classNames(styles.status, styles[source.status])}>
                <span className={styles.statusDot} />
                {source.status}
              </span>
            </button>
            <div className={styles.rowActions}>
              <button
                className={classNames(controls.button, controls.iconButton)}
                type="button"
                title="Reindex"
                onClick={() => onReindex(source.id)}
                disabled={busy !== null}
              >
                {busy === `index:${source.id}` ? (
                  <Loader2 className={controls.spin} size={16} />
                ) : (
                  <RefreshCw size={16} />
                )}
              </button>
              <button
                className={classNames(controls.button, controls.iconButton, controls.danger)}
                type="button"
                title="Remove"
                onClick={() => onRemove(source.id)}
                disabled={busy !== null}
              >
                <Trash2 size={16} />
              </button>
            </div>
          </article>
        ))}
        {sources.length === 0 ? <p className={styles.empty}>No sources indexed.</p> : null}
      </div>
    </section>
  )
}
