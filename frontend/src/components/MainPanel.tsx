import type { FormEvent, RefObject } from 'react'
import { FiDatabase, FiFolder, FiServer, FiZap } from 'react-icons/fi'
import { DocumentList } from './main/DocumentList'
import { Preview } from './main/Preview'
import { ResultList } from './main/ResultList'
import { SettingsPanel } from './main/SettingsPanel'
import { SourceList } from './main/SourceList'
import { Topbar } from './main/Topbar'
import type { BusyTask, DocumentDetail, IndexedDocument, SearchResult, Source } from '../types'
import { classNames } from '../utils/classNames'
import styles from './MainPanel.module.css'

type Route = { page: 'home' } | { page: 'settings' } | { page: 'source'; sourceId: string }

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
  const indexedSources = sources.filter((source) => source.status === 'indexed').length
  const localSources = sources.filter((source) => source.kind === 'local').length
  const remoteSources = sources.filter((source) => source.kind === 'remote').length
  const activeSources = sources.filter(
    (source) => source.status === 'indexing' || source.status === 'pending',
  ).length

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
      <Topbar
        busy={busy}
        onBackToSources={onBackToSources}
        onSearchDocs={onSearchDocs}
        query={query}
        searchInputRef={searchInputRef}
        selectedSource={selectedSource}
        setQuery={setQuery}
      />
      <div className={styles.contentStack}>
        <DocumentList
          busy={busy}
          documents={documents}
          onOpenDocument={onOpenDocument}
          selectedDocument={selectedDocument}
          selectedSource={selectedSource}
        />
        <ResultList
          busy={busy}
          onOpenDocument={onOpenDocument}
          query={query}
          results={results}
          selectedSource={selectedSource}
        />
        <Preview selectedDocument={selectedDocument} />
      </div>
    </section>
  )
}
