import { FiClock, FiFolder, FiRefreshCw, FiServer, FiTrash2 } from 'react-icons/fi'
import { ImSpinner2 } from 'react-icons/im'
import { classNames } from '../../utils/classNames'
import type { BusyTask, Source } from '../../types'
import controls from '../controls.module.css'
import styles from '../MainPanel.module.css'

type SourceListProps = {
  activeSources?: number
  busy: BusyTask
  onReindex: (sourceId: string) => void
  onRemove: (sourceId: string) => void
  onSelectSource: (sourceId: string) => void
  sources: Source[]
}

function getSourceLabel(source: Source) {
  return source.kind === 'local' ? 'Local folder' : 'Remote site'
}

function getSourceOriginLabel(source: Source) {
  if (source.kind !== 'remote') return source.origin

  try {
    const url = new URL(source.origin)
    return url.origin
  } catch {
    return source.origin
  }
}

function getStatusLabel(status: string) {
  if (status === 'indexed') return 'Ready'
  if (status === 'indexing') return 'Indexing'
  if (status === 'pending') return 'Pending'
  if (status === 'failed') return 'Failed'
  return status
}

export function SourceList({
  activeSources = 0,
  busy,
  onReindex,
  onRemove,
  onSelectSource,
  sources,
}: SourceListProps) {
  return (
    <section className={classNames(styles.section, styles.sourceSection)}>
      <header>
        <div>
          <h2>Sources</h2>
          <span>
            {activeSources > 0
              ? `${activeSources} updating, ${sources.length} total`
              : `${sources.length} total`}
          </span>
        </div>
      </header>
      <div className={classNames(styles.list, styles.sourceGrid, sources.length === 0 && styles.sourceGridEmpty)}>
        {sources.map((source) => (
          <article
            className={styles.sourceRow}
            key={source.id}
            role="button"
            tabIndex={busy === null ? 0 : -1}
            aria-label={`Open ${source.name}`}
            onClick={() => {
              if (busy === null) onSelectSource(source.id)
            }}
            onKeyDown={(event) => {
              if (busy !== null || event.currentTarget !== event.target) return
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onSelectSource(source.id)
              }
            }}
          >
            <div className={styles.sourceCardHeader}>
              <span className={styles.sourceIcon} aria-hidden="true">
                {source.kind === 'local' ? <FiFolder /> : <FiServer />}
              </span>
              <span className={styles.sourceIdentity}>
                <strong>{source.name}</strong>
                <small>{getSourceLabel(source)}</small>
              </span>
              <span className={classNames(styles.status, styles[source.status])}>
                <span className={styles.statusDot} />
                {getStatusLabel(source.status)}
              </span>
            </div>
            <span className={styles.sourceOrigin} title={source.origin}>
              {getSourceOriginLabel(source)}
            </span>
            <div className={styles.rowActions}>
              <button
                className={classNames(controls.button, controls.iconButton)}
                type="button"
                title="Reindex"
                onClick={(event) => {
                  event.stopPropagation()
                  onReindex(source.id)
                }}
                disabled={busy !== null}
              >
                {busy === `index:${source.id}` ? (
                  <ImSpinner2 className={controls.spin} size={16} />
                ) : (
                  <FiRefreshCw size={16} />
                )}
              </button>
              <button
                className={classNames(controls.button, controls.iconButton, controls.danger)}
                type="button"
                title="Remove"
                onClick={(event) => {
                  event.stopPropagation()
                  onRemove(source.id)
                }}
                disabled={busy !== null}
              >
                <FiTrash2 size={16} />
              </button>
            </div>
          </article>
        ))}
        {sources.length === 0 ? (
          <div className={styles.emptyState}>
            <FiClock aria-hidden="true" />
            <strong>No sources yet</strong>
            <p>Add a local folder or crawl a remote docs site from the sidebar.</p>
          </div>
        ) : null}
      </div>
    </section>
  )
}
