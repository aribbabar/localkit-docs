import { FiFileText } from 'react-icons/fi'
import { classNames } from '../../utils/classNames'
import { getDocumentMeta, getDocumentTitle } from '../../utils/documentDisplay'
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
    <section className={classNames(styles.section, styles.documentsSection)}>
      <header>
        <div>
          <h2>Indexed pages</h2>
          <span>
            {selectedSource ? `${selectedSource.name} · ${documents.length} pages` : `${documents.length} pages`}
          </span>
        </div>
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
              <strong>{getDocumentTitle(document)}</strong>
              <small>{getDocumentMeta(document)}</small>
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
