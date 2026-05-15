export type BusyTask = string | null

export type FolderFile = {
  file: File
  relativePath: string
}

export type Source = {
  id: string
  name: string
  kind: 'local' | 'remote'
  origin: string
  stored_path: string
  status: string
  options: Record<string, unknown>
  created_at?: string | null
  updated_at?: string | null
}

export type SearchResult = {
  chunk_id: string
  document_id: string
  score: number
  text: string
  source_id: string
  path: string
  source_url?: string | null
  title: string
}

export type IndexedDocument = {
  id: string
  source_id: string
  path: string
  title: string | null
  content_hash: string
  chunk_count: number
}

export type DocumentDetail = {
  document: IndexedDocument
  source: Source
  content: string
}

export type OperationEvent = {
  phase?: string
  message?: string
  current?: number
  total?: number
  current_item?: string
}

export type OperationProgress = OperationEvent & {
  operation_id: string
  status?: string
  events?: OperationEvent[]
}
