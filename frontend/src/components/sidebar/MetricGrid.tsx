import styles from '../Sidebar.module.css'

type MetricGridProps = {
  indexedSources: number
  sourcesCount: number
}

export function MetricGrid({ indexedSources, sourcesCount }: MetricGridProps) {
  return (
    <div className={styles.metricGrid}>
      <div>
        <strong>{sourcesCount}</strong>
        <span>Sources</span>
      </div>
      <div>
        <strong>{indexedSources}</strong>
        <span>Indexed</span>
      </div>
    </div>
  )
}
