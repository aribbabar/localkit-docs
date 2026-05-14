import { FiFileText } from 'react-icons/fi'
import { classNames } from '../../utils/classNames'
import type { BusyTask, DocumentDetail, IndexedDocument, Source } from '../../types'
import styles from '../MainPanel.module.css'

type DocumentListProps = {
  busy: BusyTask
  documents: IndexedDocument[]
  onOpenDocument: (documentId: string) => void
  selectedDocument: DocumentDetail | null
  selectedSource: Source | null
}

export function DocumentList({
  busy,
  documents,
  onOpenDocument,
  selectedDocument,
  selectedSource,
}: DocumentListProps) {
  return (
    <section className={styles.section}>
      <header>
        <h2>{selectedSource ? `${selectedSource.name} Docs` : 'Documents'}</h2>
        <span>{documents.length} indexed</span>
      </header>
      <div className={styles.list}>
        {documents.map((document) => (
          <button
            className={classNames(
              styles.documentRow,
              selectedDocument?.document.id === document.id && styles.documentSelected,
            )}
            key={document.id}
            type="button"
            onClick={() => onOpenDocument(document.id)}
            disabled={busy !== null}
          >
            <FiFileText size={16} />
            <span>
              <strong>{document.title || document.path}</strong>
              <small>
                {document.path} - {document.chunk_count} chunks
              </small>
            </span>
          </button>
        ))}
        {documents.length === 0 ? (
          <p className={styles.empty}>Select a source to browse docs.</p>
        ) : null}
      </div>
    </section>
  )
}
