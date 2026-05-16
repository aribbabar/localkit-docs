import { useState } from 'react'
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

type PendingAction = {
  kind: 'reindex' | 'remove'
  source: Source
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
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null)
  const confirmTitle =
    pendingAction?.kind === 'remove' ? `Delete ${pendingAction.source.name}?` : `Reindex ${pendingAction?.source.name}?`
  const confirmBody =
    pendingAction?.kind === 'remove'
      ? 'This removes the source and its indexed documents from the local index.'
      : 'This refreshes the source index and may replace the currently indexed documents.'
  const confirmLabel = pendingAction?.kind === 'remove' ? 'Delete index' : 'Reindex source'

  function confirmPendingAction() {
    if (!pendingAction) return
    if (pendingAction.kind === 'remove') {
      onRemove(pendingAction.source.id)
    } else {
      onReindex(pendingAction.source.id)
    }
    setPendingAction(null)
  }

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
            <div className={styles.sourceCardFooter}>
              <span className={styles.sourceOrigin} title={source.origin}>
                {getSourceOriginLabel(source)}
              </span>
              <div className={styles.rowActions} aria-label={`${source.name} actions`}>
                <button
                  className={classNames(controls.button, controls.iconButton)}
                  type="button"
                  title="Reindex source"
                  aria-label={`Reindex ${source.name}`}
                  onClick={(event) => {
                    event.stopPropagation()
                    setPendingAction({ kind: 'reindex', source })
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
                  title="Delete index"
                  aria-label={`Delete ${source.name}`}
                  onClick={(event) => {
                    event.stopPropagation()
                    setPendingAction({ kind: 'remove', source })
                  }}
                  disabled={busy !== null}
                >
                  <FiTrash2 size={16} />
                </button>
              </div>
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
      {pendingAction ? (
        <div className={styles.confirmOverlay} role="presentation" onClick={() => setPendingAction(null)}>
          <div
            aria-labelledby="source-action-title"
            aria-describedby="source-action-description"
            aria-modal="true"
            className={styles.confirmDialog}
            role="dialog"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 id="source-action-title">{confirmTitle}</h3>
            <p id="source-action-description">
              {confirmBody}
              <span>{getSourceOriginLabel(pendingAction.source)}</span>
            </p>
            <div className={styles.confirmActions}>
              <button
                className={classNames(controls.button, controls.ghost)}
                type="button"
                onClick={() => setPendingAction(null)}
              >
                Cancel
              </button>
              <button
                className={classNames(
                  controls.button,
                  pendingAction.kind === 'remove' && controls.dangerButton,
                )}
                type="button"
                onClick={confirmPendingAction}
              >
                {confirmLabel}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
