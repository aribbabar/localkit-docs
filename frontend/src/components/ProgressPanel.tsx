import { FiActivity, FiAlertTriangle, FiCheckCircle, FiClock } from 'react-icons/fi'
import { formatPhase } from '../utils/operations'
import type { OperationProgress } from '../types'
import styles from './ProgressPanel.module.css'

type ProgressPanelProps = {
  progress: OperationProgress
}

export function ProgressPanel({ progress }: ProgressPanelProps) {
  const current = typeof progress.current === 'number' ? progress.current : 0
  const total = typeof progress.total === 'number' ? progress.total : 0
  const status = progress.status ?? 'running'
  const percent =
    total > 0
      ? Math.min(100, Math.round((current / total) * 100))
      : status === 'completed'
        ? 100
        : null
  const events = (progress.events ?? []).slice(-5).reverse()
  const isCompleted = status === 'completed'
  const isFailed = status === 'failed'
  const statusLabel = isCompleted ? 'Complete' : isFailed ? 'Needs attention' : 'Running'
  const countLabel = total > 0 ? `${current.toLocaleString()} / ${total.toLocaleString()}` : 'In progress'
  const metricLabel = percent !== null ? `${percent}%` : isFailed ? 'Failed' : countLabel
  const Icon = isCompleted ? FiCheckCircle : isFailed ? FiAlertTriangle : FiActivity

  return (
    <section className={styles.panel} aria-live="polite" data-status={status}>
      <div className={styles.summary}>
        <span className={styles.statusIcon}>
          <Icon aria-hidden="true" />
        </span>
        <div className={styles.heading}>
          <span>Docs pipeline</span>
          <strong>{formatPhase(progress.phase)}</strong>
        </div>
        <div className={styles.metrics} aria-label="Current operation progress">
          <span>{statusLabel}</span>
          <strong>{metricLabel}</strong>
        </div>
      </div>
      <div className={styles.progressBlock}>
        <div
          className={styles.track}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={total || undefined}
          aria-valuenow={total > 0 ? current : undefined}
        >
          <span style={{ width: `${percent ?? 42}%` }} />
        </div>
        <div className={styles.progressMeta}>
          <p>{progress.message ?? 'Working'}</p>
          <span>{countLabel}</span>
        </div>
        {progress.current_item ? (
          <small className={styles.currentItem}>{progress.current_item}</small>
        ) : null}
      </div>
      {events.length > 0 ? (
        <div className={styles.activityLog}>
          <div className={styles.activityHeader}>
            <FiClock aria-hidden="true" />
            <span>Recent activity</span>
          </div>
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
        </div>
      ) : null}
    </section>
  )
}
