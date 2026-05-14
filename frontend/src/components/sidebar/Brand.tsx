import { FiDatabase } from 'react-icons/fi'
import styles from '../Sidebar.module.css'

type BrandProps = {
  message: string
}

export function Brand({ message }: BrandProps) {
  return (
    <div className={styles.brand}>
      <FiDatabase size={24} />
      <div>
        <h1>LocalKit Docs</h1>
        <span>{message}</span>
      </div>
    </div>
  )
}
