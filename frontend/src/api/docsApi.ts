import { API_URL } from '../config'
import type {
  DocumentDetail,
  FolderFile,
  IndexedDocument,
  OperationProgress,
  SearchResult,
  Source,
} from '../types'

type SearchResponse = {
  results: SearchResult[]
}

type RemoteSourceInput = {
  crawlScope: 'path' | 'domain'
  exclude: string[]
  include: string[]
  maxDepth: number
  maxPages: number
  name: string | null
  operationId: string
  url: string
}

export async function fetchSources(): Promise<Source[]> {
  return requestJson<Source[]>('/sources')
}

export async function fetchSourceDocuments(sourceId: string): Promise<IndexedDocument[]> {
  return requestJson<IndexedDocument[]>(`/sources/${sourceId}/documents`)
}

export async function fetchDocument(documentId: string): Promise<DocumentDetail> {
  return requestJson<DocumentDetail>(`/documents/${documentId}`)
}

export async function uploadLocalSource({
  files,
  folderName,
  maxFiles,
  operationId,
}: {
  files: FolderFile[]
  folderName: string
  maxFiles: number
  operationId: string
}): Promise<void> {
  const formData = new FormData()
  if (folderName.trim()) {
    formData.append('name', folderName.trim())
  }
  formData.append('operation_id', operationId)
  for (const item of files) {
    formData.append('files', item.file, item.relativePath)
  }

  await request(`/sources/local/upload?max_files=${encodeURIComponent(String(maxFiles))}`, {
    method: 'POST',
    body: formData,
  })
}

export async function createRemoteSource({
  crawlScope,
  exclude,
  include,
  maxDepth,
  maxPages,
  name,
  operationId,
  url,
}: RemoteSourceInput): Promise<void> {
  await request('/sources/remote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      url,
      name,
      include,
      exclude,
      crawl_scope: crawlScope,
      max_pages: maxPages,
      max_depth: maxDepth,
      delay_seconds: 0.15,
      index: true,
      operation_id: operationId,
    }),
  })
}

export async function searchDocuments({
  query,
  sourceId,
}: {
  query: string
  sourceId: string | null
}): Promise<SearchResult[]> {
  const payload = await requestJson<SearchResponse>('/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit: 8, source_id: sourceId }),
  })
  return payload.results
}

export async function reindexSource(sourceId: string, operationId: string): Promise<void> {
  await request(`/sources/${sourceId}/index?operation_id=${operationId}`, {
    method: 'POST',
  })
}

export async function removeSource(sourceId: string): Promise<void> {
  await request(`/sources/${sourceId}`, { method: 'DELETE' })
}

export async function fetchOperation(operationId: string): Promise<OperationProgress | null> {
  const response = await fetch(`${API_URL}/operations/${operationId}`)
  if (!response.ok) return null
  return (await response.json()) as OperationProgress
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await request(path, init)
  return (await response.json()) as T
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${API_URL}${path}`, init)
  if (!response.ok) throw new Error(await response.text())
  return response
}
