import type { IndexedDocument, SearchResult } from '../types'

type DocumentLike = Pick<IndexedDocument, 'path' | 'title'> | Pick<SearchResult, 'path' | 'title'>

function isLowValueTitle(title: string | null | undefined): boolean {
  if (!title) return true
  return /^depth:\s*\d+$/i.test(title.trim())
}

function humanizeSegment(segment: string): string {
  return segment
    .replace(/\.(md|mdx|html?)$/i, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function getDocumentTitle(document: DocumentLike): string {
  if (!isLowValueTitle(document.title)) {
    return String(document.title).trim()
  }

  const cleanPath = document.path.replace(/\/index\.(md|mdx|html?)$/i, '')
  const segments = cleanPath.split('/').filter(Boolean)
  const lastSegment = segments.at(-1) ?? document.path
  return humanizeSegment(lastSegment)
}

export function getDocumentMeta(document: Pick<IndexedDocument, 'path' | 'chunk_count'>): string {
  const chunkLabel = document.chunk_count === 1 ? '1 chunk' : `${document.chunk_count} chunks`
  return `${chunkLabel} · ${document.path}`
}
