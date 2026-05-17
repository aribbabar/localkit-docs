import { useMemo, useState } from 'react'
import type { FormEvent, RefObject } from 'react'
import {
  FiArrowLeft,
  FiDatabase,
  FiFileText,
  FiFolder,
  FiRefreshCw,
  FiSearch,
  FiServer,
  FiTrash2,
  FiZap,
} from 'react-icons/fi'
import { Preview } from './main/Preview'
import { ResultList } from './main/ResultList'
import { SettingsPanel } from './main/SettingsPanel'
import { SourceList } from './main/SourceList'
import type { BusyTask, DocumentDetail, IndexedDocument, SearchResult, Source } from '../types'
import { classNames } from '../utils/classNames'
import { getDocumentMeta, getDocumentTitle } from '../utils/documentDisplay'
import controls from './controls.module.css'
import styles from './MainPanel.module.css'

type Route = { page: 'home' } | { page: 'settings' } | { page: 'source'; sourceId: string }
type DocumentKindFilter = 'all' | 'markdown' | 'html' | 'json'

const DOCUMENT_KIND_FILTERS: Array<{ label: string; value: DocumentKindFilter }> = [
  { label: 'All', value: 'all' },
  { label: 'Markdown', value: 'markdown' },
  { label: 'HTML', value: 'html' },
  { label: 'JSON', value: 'json' },
]

function getSourceKindLabel(source: Source | null): string {
  if (!source) return 'Loading'
  return source.kind === 'local' ? 'Local folder' : 'Remote site'
}

function getStatusLabel(status: string | undefined): string {
  if (status === 'indexed') return 'Ready'
  if (status === 'indexing') return 'Indexing'
  if (status === 'pending') return 'Pending'
  if (status === 'failed') return 'Failed'
  return status ?? 'Loading'
}

function getDocumentExtension(path: string): string {
  const filename = path.split('/').pop() ?? path
  const extension = filename.includes('.') ? filename.split('.').pop() : ''
  return extension ? extension.toUpperCase() : 'DOC'
}

function getDocumentKind(path: string): DocumentKindFilter | 'other' {
  const extension = getDocumentExtension(path).toLowerCase()
  if (extension === 'md' || extension === 'mdx') return 'markdown'
  if (extension === 'html' || extension === 'htm') return 'html'
  if (extension === 'json') return 'json'
  return 'other'
}

function formatRelativeDate(value: string | null | undefined): string {
  if (!value) return 'Never'
  const timestamp = new Date(value).getTime()
  if (!Number.isFinite(timestamp)) return 'Unknown'

  const elapsedMs = Math.max(0, Date.now() - timestamp)
  const elapsedMinutes = Math.max(1, Math.floor(elapsedMs / 60000))
  if (elapsedMinutes < 60) return `${elapsedMinutes} min ago`

  const elapsedHours = Math.floor(elapsedMinutes / 60)
  if (elapsedHours < 24) return `${elapsedHours} hr ago`

  const elapsedDays = Math.floor(elapsedHours / 24)
  if (elapsedDays < 30) return `${elapsedDays} day${elapsedDays === 1 ? '' : 's'} ago`

  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(
    new Date(timestamp),
  )
}

type MainPanelProps = {
  busy: BusyTask
  documents: IndexedDocument[]
  localDocsMaxFiles: number
  onBackToSources: () => void
  onOpenDocument: (documentId: string) => void
  onSaveLocalDocsMaxFiles: (value: number) => void
  onReindex: (sourceId: string) => void
  onRemove: (sourceId: string) => void
  onSearchDocs: (event: FormEvent) => void
  onSelectSource: (sourceId: string) => void
  query: string
  results: SearchResult[]
  route: Route
  selectedDocument: DocumentDetail | null
  selectedSource: Source | null
  searchInputRef: RefObject<HTMLInputElement | null>
  setQuery: (value: string) => void
  sources: Source[]
}

export function MainPanel({
  busy,
  documents,
  localDocsMaxFiles,
  onBackToSources,
  onOpenDocument,
  onSaveLocalDocsMaxFiles,
  onReindex,
  onRemove,
  onSearchDocs,
  onSelectSource,
  query,
  results,
  route,
  selectedDocument,
  selectedSource,
  searchInputRef,
  setQuery,
  sources,
}: MainPanelProps) {
  const [documentKindFilter, setDocumentKindFilter] = useState<DocumentKindFilter>('all')
  const indexedSources = sources.filter((source) => source.status === 'indexed').length
  const localSources = sources.filter((source) => source.kind === 'local').length
  const remoteSources = sources.filter((source) => source.kind === 'remote').length
  const activeSources = sources.filter(
    (source) => source.status === 'indexing' || source.status === 'pending',
  ).length
  const totalChunks = documents.reduce((total, document) => total + document.chunk_count, 0)
  const visibleDocuments = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    return documents.filter((document) => {
      const matchesKind =
        documentKindFilter === 'all' || getDocumentKind(document.path) === documentKindFilter
      if (!matchesKind) return false
      if (!normalizedQuery) return true

      const title = getDocumentTitle(document).toLowerCase()
      return title.includes(normalizedQuery) || document.path.toLowerCase().includes(normalizedQuery)
    })
  }, [documentKindFilter, documents, query])

  if (route.page === 'settings') {
    return (
      <SettingsPanel
        localDocsMaxFiles={localDocsMaxFiles}
        onBackToSources={onBackToSources}
        onSaveLocalDocsMaxFiles={onSaveLocalDocsMaxFiles}
      />
    )
  }

  if (route.page === 'home') {
    return (
      <section className={styles.panel}>
        <div className={styles.overviewGrid} aria-label="Source overview">
          <div className={styles.overviewItem}>
            <FiDatabase aria-hidden="true" />
            <span>Total sources</span>
            <strong>{sources.length}</strong>
          </div>
          <div className={styles.overviewItem}>
            <FiZap aria-hidden="true" />
            <span>Indexed</span>
            <strong>{indexedSources}</strong>
          </div>
          <div className={styles.overviewItem}>
            <FiFolder aria-hidden="true" />
            <span>Local</span>
            <strong>{localSources}</strong>
          </div>
          <div className={styles.overviewItem}>
            <FiServer aria-hidden="true" />
            <span>Remote</span>
            <strong>{remoteSources}</strong>
          </div>
        </div>
        <SourceList
          busy={busy}
          activeSources={activeSources}
          onReindex={onReindex}
          onRemove={onRemove}
          onSelectSource={onSelectSource}
          sources={sources}
        />
      </section>
    )
  }

  return (
    <section className={classNames(styles.panel, styles.sourcePanel)}>
      <div className={styles.sourcePage}>
        <header className={styles.sourceTopbar}>
          <div className={styles.sourceTitleGroup}>
            <button
              className={classNames(controls.button, controls.iconButton, controls.ghost)}
              type="button"
              title="Back to sources"
              onClick={onBackToSources}
              disabled={busy !== null}
            >
              <FiArrowLeft size={16} />
            </button>
            <div>
              <h1>{selectedSource?.name ?? 'Source'}</h1>
              <p>
                {getSourceKindLabel(selectedSource)}
                {selectedSource ? ` · ${selectedSource.origin}` : ''}
              </p>
            </div>
          </div>
          <div className={styles.sourceActions}>
            <button
              className={classNames(controls.button, controls.ghost)}
              type="button"
              onClick={() => selectedSource && onReindex(selectedSource.id)}
              disabled={busy !== null || !selectedSource}
            >
              <FiRefreshCw size={15} />
              Reindex
            </button>
            <button
              className={classNames(controls.button, controls.ghost, controls.danger)}
              type="button"
              onClick={() => selectedSource && onRemove(selectedSource.id)}
              disabled={busy !== null || !selectedSource}
            >
              <FiTrash2 size={15} />
              Remove
            </button>
          </div>
        </header>

        <section className={styles.sourceInfoCard}>
          <div className={styles.sourceInfoHeading}>
            <h2>Source info</h2>
            <span className={classNames(styles.status, selectedSource && styles[selectedSource.status])}>
              <span className={styles.statusDot} />
              {getStatusLabel(selectedSource?.status).toUpperCase()}
            </span>
          </div>
          <dl className={styles.sourceInfoGrid}>
            <div>
              <dt>Type</dt>
              <dd>{getSourceKindLabel(selectedSource)}</dd>
            </div>
            <div>
              <dt>Path</dt>
              <dd title={selectedSource?.origin}>{selectedSource?.origin ?? 'Loading source'}</dd>
            </div>
            <div>
              <dt>Documents</dt>
              <dd>{documents.length.toLocaleString()}</dd>
            </div>
            <div>
              <dt>Last indexed</dt>
              <dd>{formatRelativeDate(selectedSource?.updated_at)}</dd>
            </div>
            <div>
              <dt>Chunks</dt>
              <dd>{totalChunks.toLocaleString()}</dd>
            </div>
            <div>
              <dt>ID</dt>
              <dd>{selectedSource?.id ?? route.sourceId}</dd>
            </div>
          </dl>
        </section>

        <form className={styles.documentSearch} onSubmit={onSearchDocs}>
          <FiSearch aria-hidden="true" />
          <input
            ref={searchInputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search documents in this index..."
          />
        </form>

        <div className={styles.documentTabs} role="tablist" aria-label="Document type filter">
          {DOCUMENT_KIND_FILTERS.map((filter) => (
            <button
              className={classNames(
                styles.documentTab,
                documentKindFilter === filter.value && styles.documentTabActive,
              )}
              key={filter.value}
              type="button"
              role="tab"
              aria-selected={documentKindFilter === filter.value}
              onClick={() => setDocumentKindFilter(filter.value)}
            >
              {filter.label}
            </button>
          ))}
        </div>

        <section className={styles.documentTable}>
          <div className={styles.documentTableHeader}>
            <span>Document</span>
            <span>Chunks</span>
            <span>Type</span>
          </div>
          {visibleDocuments.map((document) => (
            <button
              className={classNames(
                styles.documentTableRow,
                selectedDocument?.document.id === document.id && styles.documentTableRowSelected,
              )}
              key={document.id}
              type="button"
              onClick={() => onOpenDocument(document.id)}
              disabled={busy !== null}
            >
              <span className={styles.documentTableIdentity}>
                <span className={styles.documentIcon} aria-hidden="true">
                  <FiFileText size={15} />
                </span>
                <span>
                  <strong>{getDocumentTitle(document)}</strong>
                  <small>{document.path}</small>
                </span>
              </span>
              <span>{getDocumentMeta(document).split(' · ')[0]}</span>
              <span>{getDocumentExtension(document.path)}</span>
            </button>
          ))}
          {visibleDocuments.length === 0 ? (
            <div className={styles.documentTableEmpty}>
              <strong>No documents match this view</strong>
              <span>Adjust the search text or switch document type.</span>
            </div>
          ) : null}
        </section>

        {results.length > 0 || selectedDocument ? (
          <div className={styles.sourceDetailGrid}>
            {results.length > 0 ? (
              <ResultList
                busy={busy}
                onOpenDocument={onOpenDocument}
                query={query}
                results={results}
                selectedSource={selectedSource}
              />
            ) : null}
            {selectedDocument ? <Preview selectedDocument={selectedDocument} /> : null}
          </div>
        ) : null}
      </div>
    </section>
  )
}
