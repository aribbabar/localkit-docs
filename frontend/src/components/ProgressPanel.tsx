import { formatPhase } from '../utils/operations'
import type { OperationProgress } from '../types'
import styles from './ProgressPanel.module.css'

type ProgressPanelProps = {
  progress: OperationProgress
}

export function ProgressPanel({ progress }: ProgressPanelProps) {
  const current = typeof progress.current === 'number' ? progress.current : 0
  const total = typeof progress.total === 'number' ? progress.total : 0
  const percent =
    total > 0
      ? Math.min(100, Math.round((current / total) * 100))
      : progress.status === 'completed'
        ? 100
        : null
  const events = (progress.events ?? []).slice(-4).reverse()

  return (
    <section className={styles.panel} aria-live="polite">
      <div className={styles.header}>
        <strong>{formatPhase(progress.phase)}</strong>
        <span>{percent !== null ? `${percent}%` : progress.status ?? 'running'}</span>
      </div>
      <div
        className={styles.track}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total || undefined}
        aria-valuenow={total > 0 ? current : undefined}
      >
        <span style={{ width: `${percent ?? 42}%` }} />
      </div>
      <p>{progress.message ?? 'Working'}</p>
      {progress.current_item ? <small>{progress.current_item}</small> : null}
      {events.length > 0 ? (
        <ol className={styles.events}>
          {events.map((event, index) => (
            <li
              className={styles.event}
              key={`${event.phase}:${event.current_item}:${event.current}:${index}`}
            >
              <span className={styles.eventPhase}>{formatPhase(event.phase)}</span>
              <b className={styles.eventItem}>{event.current_item}</b>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  )
}
