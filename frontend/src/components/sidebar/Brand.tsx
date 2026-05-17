import styles from '../Sidebar.module.css'

type BrandProps = {
  message: string
}

export function Brand({ message }: BrandProps) {
  return (
    <div className={styles.brand}>
      <span className={styles.brandMark} aria-hidden="true">
        LK
      </span>
      <div>
        <h1>LocalKit Docs</h1>
        <span>{message}</span>
      </div>
    </div>
  )
}
