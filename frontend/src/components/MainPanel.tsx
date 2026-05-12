import type { FormEvent, RefObject } from 'react'
import { DocumentList } from './main/DocumentList'
import { Preview } from './main/Preview'
import { ResultList } from './main/ResultList'
import { SettingsPanel } from './main/SettingsPanel'
import { SourceList } from './main/SourceList'
import { Topbar } from './main/Topbar'
import type { BusyTask, DocumentDetail, IndexedDocument, SearchResult, Source } from '../types'
import styles from './MainPanel.module.css'

type Route = { page: 'home' } | { page: 'settings' } | { page: 'source'; sourceId: string }

type MainPanelProps = {
  busy: BusyTask
  documents: IndexedDocument[]
  localDocsMaxFiles: number
  onBackToSources: () => void
  onOpenDocument: (documentId: string) => void
  onRefreshSources: () => void
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
  onRefreshSources,
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
        <div className={styles.panelHeader}>
          <div>
            <h1>Sources</h1>
            <p>Add documentation from the sidebar, then open a source to search it.</p>
          </div>
          <button
            className={styles.refreshButton}
            type="button"
            onClick={onRefreshSources}
            disabled={busy !== null}
          >
            Refresh
          </button>
        </div>
        <SourceList
          busy={busy}
          onReindex={onReindex}
          onRemove={onRemove}
          onSelectSource={onSelectSource}
          sources={sources}
        />
      </section>
    )
  }

  return (
    <section className={styles.panel}>
      <Topbar
        busy={busy}
        onBackToSources={onBackToSources}
        onRefreshSources={onRefreshSources}
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
          results={results}
          selectedSource={selectedSource}
        />
        <Preview selectedDocument={selectedDocument} />
      </div>
    </section>
  )
}
