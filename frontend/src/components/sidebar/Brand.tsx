import { Database } from 'lucide-react'
import styles from '../Sidebar.module.css'

type BrandProps = {
  message: string
}

export function Brand({ message }: BrandProps) {
  return (
    <div className={styles.brand}>
      <Database size={24} />
      <div>
        <h1>LocalKit Docs</h1>
        <span>{message}</span>
      </div>
    </div>
  )
}
