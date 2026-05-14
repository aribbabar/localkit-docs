import { useEffect, useMemo, useRef, useState } from 'react'
import type { DragEvent, FormEvent } from 'react'
import {
  createRemoteSource,
  fetchDocument,
  fetchSourceDocuments,
  fetchSources,
  reindexSource,
  removeSource,
  searchDocuments,
  uploadLocalSource,
} from './api/docsApi'
import { MainPanel } from './components/MainPanel'
import { Sidebar } from './components/Sidebar'
import { useOperationProgress } from './hooks/useOperationProgress'
import {
  getDroppedFolderFiles,
  getFileRelativePath,
  inferDocsName,
  mergeFolderFiles,
} from './utils/folderFiles'
import { createOperationId } from './utils/operations'
import type {
  BusyTask,
  DocumentDetail,
  FolderFile,
  IndexedDocument,
  SearchResult,
  Source,
} from './types'
import styles from './App.module.css'

const DEFAULT_LOCAL_DOCS_MAX_FILES = 10000
const LOCAL_DOCS_MAX_FILES_KEY = 'localkit.localDocsMaxFiles'
const REMOTE_CRAWL_SETTINGS_KEY = 'localkit.remoteCrawlSettings'
const DEFAULT_REMOTE_CRAWL_SETTINGS = {
  excludePatterns: [
    '*changelog*',
    '*change-log*',
    '*release-notes*',
    '*license*',
    '*code-of-conduct*',
    '*code_conduct*',
    '*package-lock*',
    '*pnpm-lock*',
    '*yarn.lock*',
    '*/test/*',
    '*/tests/*',
    '*/archive/*',
    '*/archived/*',
    '*/deprecated/*',
    '*/build/*',
    '*/target/*',
    '*/old/*',
    '*/old-docs/*',
    '*/docs-old/*',
    '*/dist/*',
    '*/coverage/*',
    '*/node_modules/*',
    '*/.git/*',
    '*.zip',
    '*.tar',
    '*.tar.gz',
    '*.tgz',
  ],
  includePatterns: ['/docs/'],
  maxDepth: 3,
  maxPages: 1000,
}

type RemoteCrawlSettings = typeof DEFAULT_REMOTE_CRAWL_SETTINGS
type RemoteCrawlForm = {
  exclude: string
  include: string
  maxDepth: number
  maxPages: number
}

type Route = { page: 'home' } | { page: 'settings' } | { page: 'source'; sourceId: string }

function parseRoute(): Route {
  if (/^\/settings\/?$/.test(window.location.pathname)) {
    return { page: 'settings' }
  }
  const sourceMatch = window.location.pathname.match(/^\/sources\/([^/]+)\/?$/)
  if (sourceMatch?.[1]) {
    return { page: 'source', sourceId: decodeURIComponent(sourceMatch[1]) }
  }
  return { page: 'home' }
}

function readLocalDocsMaxFiles(): number {
  const savedValue = Number(window.localStorage.getItem(LOCAL_DOCS_MAX_FILES_KEY))
  if (Number.isFinite(savedValue) && savedValue >= 1) {
    return Math.floor(savedValue)
  }
  return DEFAULT_LOCAL_DOCS_MAX_FILES
}

function parsePatternInput(value: string): string[] {
  return value
    .split(/[\n,]+/)
    .map((pattern) => pattern.trim())
    .filter(Boolean)
}

function formatPatterns(patterns: string[]): string {
  return patterns.join('\n')
}

function clampInteger(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min
  return Math.max(min, Math.min(max, Math.floor(value)))
}

function readSavedInteger(value: unknown, fallback: number, min: number, max: number): number {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return fallback
  return clampInteger(numericValue, min, max)
}

function readRemoteCrawlSettings(): RemoteCrawlSettings {
  const fallback = DEFAULT_REMOTE_CRAWL_SETTINGS
  try {
    const savedSettings = JSON.parse(window.localStorage.getItem(REMOTE_CRAWL_SETTINGS_KEY) || 'null') as Partial<
      RemoteCrawlSettings
    > | null
    if (!savedSettings || typeof savedSettings !== 'object') return fallback

    return {
      excludePatterns: Array.isArray(savedSettings.excludePatterns)
        ? savedSettings.excludePatterns.filter((pattern): pattern is string => typeof pattern === 'string')
        : fallback.excludePatterns,
      includePatterns: Array.isArray(savedSettings.includePatterns)
        ? savedSettings.includePatterns.filter((pattern): pattern is string => typeof pattern === 'string')
        : fallback.includePatterns,
      maxDepth: readSavedInteger(savedSettings.maxDepth, fallback.maxDepth, 1, 20),
      maxPages: readSavedInteger(savedSettings.maxPages, fallback.maxPages, 1, 5000),
    }
  } catch {
    return fallback
  }
}

function createRemoteCrawlForm(settings: RemoteCrawlSettings = readRemoteCrawlSettings()): RemoteCrawlForm {
  return {
    exclude: formatPatterns(settings.excludePatterns),
    include: formatPatterns(settings.includePatterns),
    maxDepth: settings.maxDepth,
    maxPages: settings.maxPages,
  }
}

function persistRemoteCrawlForm(settings: RemoteCrawlForm) {
  window.localStorage.setItem(
    REMOTE_CRAWL_SETTINGS_KEY,
    JSON.stringify({
      excludePatterns: parsePatternInput(settings.exclude),
      includePatterns: parsePatternInput(settings.include),
      maxDepth: settings.maxDepth,
      maxPages: settings.maxPages,
    }),
  )
}

function App() {
  const [sources, setSources] = useState<Source[]>([])
  const [documents, setDocuments] = useState<IndexedDocument[]>([])
  const [selectedDocument, setSelectedDocument] = useState<DocumentDetail | null>(null)
  const [results, setResults] = useState<SearchResult[]>([])
  const [query, setQuery] = useState('')
  const [route, setRoute] = useState<Route>(() => parseRoute())
  const [uploadedFolderName, setUploadedFolderName] = useState('')
  const [folderFiles, setFolderFiles] = useState<FolderFile[]>([])
  const [remoteUrl, setRemoteUrl] = useState('')
  const [remoteName, setRemoteName] = useState('')
  const [remoteCrawlForm, setRemoteCrawlForm] = useState(createRemoteCrawlForm)
  const [localDocsMaxFiles, setLocalDocsMaxFilesState] = useState(readLocalDocsMaxFiles)
  const [busy, setBusy] = useState<BusyTask>(null)
  const [message, setMessage] = useState('Backend not checked')
  const searchInputRef = useRef<HTMLInputElement>(null)
  const settledOperationRef = useRef<string | null>(null)
  const { activeProgress, startProgressPolling, waitForOperation } = useOperationProgress()
  const selectedSourceId = route.page === 'source' ? route.sourceId : null

  const indexedSources = useMemo(
    () => sources.filter((source) => source.status === 'indexed').length,
    [sources],
  )
  const selectedSource = useMemo(
    () => sources.find((source) => source.id === selectedSourceId) ?? null,
    [selectedSourceId, sources],
  )

  useEffect(() => {
    refreshSources()
  }, [])

  useEffect(() => {
    if (!activeProgress || !['completed', 'failed'].includes(activeProgress.status ?? '')) return
    if (settledOperationRef.current === activeProgress.operation_id) return
    settledOperationRef.current = activeProgress.operation_id
    void refreshSources()
    if (selectedSourceId) {
      void fetchSourceDocuments(selectedSourceId).then(setDocuments).catch(() => undefined)
    }
  }, [activeProgress, selectedSourceId])

  useEffect(() => {
    function handlePopState() {
      clearSourceView()
      setRoute(parseRoute())
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  useEffect(() => {
    if (route.page !== 'source') return

    runTask(`documents:${route.sourceId}`, async () => {
      setDocuments(await fetchSourceDocuments(route.sourceId))
    })
  }, [route])

  async function refreshSources() {
    try {
      setSources(await fetchSources())
      setMessage('Connected')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to connect')
    }
  }

  function clearSourceView() {
    setDocuments([])
    setSelectedDocument(null)
    setResults([])
    setQuery('')
  }

  function navigateHome() {
    window.history.pushState({}, '', '/')
    clearSourceView()
    setRoute({ page: 'home' })
  }

  function navigateSettings() {
    window.history.pushState({}, '', '/settings')
    clearSourceView()
    setRoute({ page: 'settings' })
  }

  function selectSource(sourceId: string) {
    window.history.pushState({}, '', `/sources/${encodeURIComponent(sourceId)}`)
    clearSourceView()
    setRoute({ page: 'source', sourceId })
    window.requestAnimationFrame(() => searchInputRef.current?.focus())
  }

  async function openDocument(documentId: string) {
    await runTask(`document:${documentId}`, async () => {
      const payload = await fetchDocument(documentId)
      setSelectedDocument(payload)
    })
  }

  async function addUploadedFolder(event?: FormEvent) {
    event?.preventDefault()
    const files = folderFiles
    const folderName = uploadedFolderName
    if (files.length === 0) return
    if (files.length > localDocsMaxFiles) {
      setMessage(`Select ${localDocsMaxFiles} files or fewer, or increase the Local Docs limit in Settings.`)
      return
    }

    await runTask('upload-folder', async () => {
      const operationId = createOperationId()
      const stopProgress = startProgressPolling(operationId)
      try {
        await uploadLocalSource({ files, folderName, maxFiles: localDocsMaxFiles, operationId })
        clearFolderSelection()
        await refreshSources()
      } finally {
        await stopProgress()
      }
    })
  }

  function clearFolderSelection() {
    setFolderFiles([])
    setUploadedFolderName('')
  }

  function selectFolderFiles(files: FileList | File[]) {
    const newFiles = Array.from(files)
      .map((file) => {
        const relativePath = getFileRelativePath(file)
        return relativePath ? { file, relativePath } : null
      })
      .filter((file): file is FolderFile => file !== null)

    appendFolderFiles(newFiles)
  }

  function appendFolderFiles(newFiles: FolderFile[]) {
    if (newFiles.length === 0) return

    const mergedFiles = mergeFolderFiles(folderFiles, newFiles)
    setFolderFiles(mergedFiles)
    setUploadedFolderName((currentName) => currentName || inferDocsName(mergedFiles))
    if (mergedFiles.length > localDocsMaxFiles) {
      setMessage(`Selected ${mergedFiles.length} files. Increase the Local Docs limit in Settings before uploading.`)
    }
  }

  function setLocalDocsMaxFiles(value: number) {
    const nextValue = Math.max(1, Math.min(100000, Math.floor(value || 1)))
    setLocalDocsMaxFilesState(nextValue)
    window.localStorage.setItem(LOCAL_DOCS_MAX_FILES_KEY, String(nextValue))
    setMessage('Settings saved')
  }

  function updateRemoteCrawlForm(update: Partial<RemoteCrawlForm>) {
    setRemoteCrawlForm((currentSettings) => {
      const nextSettings = { ...currentSettings, ...update }
      persistRemoteCrawlForm(nextSettings)
      return nextSettings
    })
  }

  function resetRemoteCrawlSettings() {
    const defaultSettings = createRemoteCrawlForm(DEFAULT_REMOTE_CRAWL_SETTINGS)
    setRemoteCrawlForm(defaultSettings)
    persistRemoteCrawlForm(defaultSettings)
    setMessage('Remote crawl defaults restored')
  }

  async function handleFolderDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()

    const files = await getDroppedFolderFiles(event.dataTransfer)
    if (files.length > 0) {
      appendFolderFiles(files)
      return
    }

    selectFolderFiles(event.dataTransfer.files)
  }

  async function addRemote(event: FormEvent) {
    event.preventDefault()
    await runTask('remote', async () => {
      const operationId = createOperationId()
      const stopProgress = startProgressPolling(operationId)
      try {
        await createRemoteSource({
          url: remoteUrl,
          name: remoteName || null,
          exclude: parsePatternInput(remoteCrawlForm.exclude),
          include: parsePatternInput(remoteCrawlForm.include),
          maxPages: remoteCrawlForm.maxPages,
          maxDepth: remoteCrawlForm.maxDepth,
          operationId,
        })
        await waitForOperation(operationId)
        setRemoteUrl('')
        setRemoteName('')
        await refreshSources()
      } finally {
        await stopProgress()
      }
    })
  }

  async function searchDocs(event: FormEvent) {
    event.preventDefault()
    if (!query.trim() || !selectedSourceId) return
    await runTask('search', async () => {
      setResults(await searchDocuments({ query, sourceId: selectedSourceId }))
    })
  }

  async function reindex(sourceId: string) {
    await runTask(`index:${sourceId}`, async () => {
      const operationId = createOperationId()
      const stopProgress = startProgressPolling(operationId)
      try {
        await reindexSource(sourceId, operationId)
        await waitForOperation(operationId)
        await refreshSources()
      } finally {
        await stopProgress()
      }
    })
  }

  async function remove(sourceId: string) {
    await runTask(`remove:${sourceId}`, async () => {
      await removeSource(sourceId)
      await refreshSources()
      if (selectedSourceId === sourceId) {
        navigateHome()
      }
    })
  }

  async function runTask(name: string, task: () => Promise<void>) {
    setBusy(name)
    setMessage('Working')
    try {
      await task()
      setMessage('Ready')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Request failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <main className={styles.workspace}>
      <Sidebar
        activeProgress={activeProgress}
        busy={busy}
        folderFiles={folderFiles}
        exclude={remoteCrawlForm.exclude}
        include={remoteCrawlForm.include}
        indexedSources={indexedSources}
        maxDepth={remoteCrawlForm.maxDepth}
        maxPages={remoteCrawlForm.maxPages}
        message={message}
        onAddRemote={addRemote}
        onAddUploadedFolder={addUploadedFolder}
        onFolderDrop={handleFolderDrop}
        onOpenSettings={navigateSettings}
        onResetRemoteCrawlSettings={resetRemoteCrawlSettings}
        onSelectFolderFiles={selectFolderFiles}
        remoteName={remoteName}
        remoteUrl={remoteUrl}
        setExclude={(exclude) => updateRemoteCrawlForm({ exclude })}
        setInclude={(include) => updateRemoteCrawlForm({ include })}
        setMaxDepth={(maxDepth) => updateRemoteCrawlForm({ maxDepth: clampInteger(maxDepth, 1, 20) })}
        setMaxPages={(maxPages) => updateRemoteCrawlForm({ maxPages: clampInteger(maxPages, 1, 5000) })}
        setRemoteName={setRemoteName}
        setRemoteUrl={setRemoteUrl}
        setUploadedFolderName={setUploadedFolderName}
        sourcesCount={sources.length}
        uploadedFolderName={uploadedFolderName}
      />
      <MainPanel
        busy={busy}
        documents={documents}
        localDocsMaxFiles={localDocsMaxFiles}
        onBackToSources={navigateHome}
        onOpenDocument={openDocument}
        onRefreshSources={refreshSources}
        onSaveLocalDocsMaxFiles={setLocalDocsMaxFiles}
        onReindex={reindex}
        onRemove={remove}
        onSearchDocs={searchDocs}
        onSelectSource={selectSource}
        query={query}
        results={results}
        route={route}
        selectedDocument={selectedDocument}
        selectedSource={selectedSource}
        searchInputRef={searchInputRef}
        setQuery={setQuery}
        sources={sources}
      />
    </main>
  )
}

export default App
