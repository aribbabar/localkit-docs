import { classNames } from '../../utils/classNames'
import type { DocumentDetail } from '../../types'
import styles from '../MainPanel.module.css'

type PreviewProps = {
  selectedDocument: DocumentDetail | null
}

export function Preview({ selectedDocument }: PreviewProps) {
  return (
    <section className={classNames(styles.section, styles.preview)}>
      <header>
        <h2>{selectedDocument?.document.title || 'Preview'}</h2>
        <span>{selectedDocument?.document.path || 'No document selected'}</span>
      </header>
      {selectedDocument ? (
        <pre>{selectedDocument.content}</pre>
      ) : (
        <p className={styles.empty}>Click an indexed document or search result to view its content.</p>
      )}
    </section>
  )
}
