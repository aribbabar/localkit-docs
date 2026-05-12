import type { FolderFile } from '../types'

type DataTransferItemWithEntry = DataTransferItem & {
  webkitGetAsEntry?: () => FileSystemEntry | null
}

export function getFileRelativePath(file: File): string {
  const fileWithPath = file as File & { webkitRelativePath?: string }
  return normalizeRelativePath(fileWithPath.webkitRelativePath || file.name)
}

export function inferDocsName(files: FolderFile[]): string {
  const roots = getRootNames(files)
  if (roots.length === 1) return roots[0]
  return 'local-docs'
}

export function summarizePendingFiles(files: FolderFile[]): string {
  if (files.length === 0) return 'Drop folders or files here'

  const roots = getRootNames(files)
  const fileLabel = files.length === 1 ? 'file' : 'files'
  if (roots.length === 0) return `${files.length} ${fileLabel} ready`
  if (roots.length === 1) return `${roots[0]} - ${files.length} ${fileLabel} ready`
  return `${roots.length} folders - ${files.length} ${fileLabel} ready`
}

export function mergeFolderFiles(
  currentFiles: FolderFile[],
  newFiles: FolderFile[],
): FolderFile[] {
  const mergedFiles = [...currentFiles]
  const existingKeys = new Set(currentFiles.map(getFolderFileKey))

  for (const item of newFiles) {
    let candidate = item
    let key = getFolderFileKey(candidate)
    if (existingKeys.has(key)) continue

    candidate = withUniquePath(candidate, new Set(mergedFiles.map((file) => file.relativePath)))
    key = getFolderFileKey(candidate)
    existingKeys.add(key)
    mergedFiles.push(candidate)
  }

  return mergedFiles
}

export async function getDroppedFolderFiles(
  dataTransfer: DataTransfer,
): Promise<FolderFile[]> {
  const entries = Array.from(dataTransfer.items)
    .map((item) => (item as DataTransferItemWithEntry).webkitGetAsEntry?.() ?? null)
    .filter((entry): entry is FileSystemEntry => entry !== null)

  if (entries.length === 0) return []

  const files = await Promise.all(entries.map((entry) => readEntryFiles(entry)))
  return files.flat()
}

function getRootNames(files: FolderFile[]): string[] {
  return Array.from(
    new Set(
      files
        .filter((item) => item.relativePath.includes('/'))
        .map((item) => item.relativePath.split('/')[0])
        .filter(Boolean),
    ),
  )
}

function withUniquePath(item: FolderFile, existingPaths: Set<string>): FolderFile {
  if (!existingPaths.has(item.relativePath)) return item

  const pathParts = item.relativePath.split('/')
  const filename = pathParts.pop() ?? item.file.name
  const dotIndex = filename.lastIndexOf('.')
  const stem = dotIndex > 0 ? filename.slice(0, dotIndex) : filename
  const extension = dotIndex > 0 ? filename.slice(dotIndex) : ''
  let index = 2
  let nextPath = [...pathParts, `${stem}-${index}${extension}`].join('/')

  while (existingPaths.has(nextPath)) {
    index += 1
    nextPath = [...pathParts, `${stem}-${index}${extension}`].join('/')
  }

  return { ...item, relativePath: nextPath }
}

function getFolderFileKey(item: FolderFile): string {
  return `${item.relativePath}:${item.file.size}:${item.file.lastModified}`
}

async function readEntryFiles(entry: FileSystemEntry): Promise<FolderFile[]> {
  if (entry.isFile) {
    const file = await readFileEntry(entry as FileSystemFileEntry)
    const relativePath = normalizeRelativePath(entry.fullPath || file.name)
    return relativePath ? [{ file, relativePath }] : []
  }

  if (!entry.isDirectory) return []

  const reader = (entry as FileSystemDirectoryEntry).createReader()
  const childEntries: FileSystemEntry[] = []
  let batch = await readEntryBatch(reader)

  while (batch.length > 0) {
    childEntries.push(...batch)
    batch = await readEntryBatch(reader)
  }

  const childFiles = await Promise.all(childEntries.map((child) => readEntryFiles(child)))
  return childFiles.flat()
}

function readFileEntry(entry: FileSystemFileEntry): Promise<File> {
  return new Promise<File>((resolve, reject) => {
    entry.file(resolve, reject)
  })
}

function readEntryBatch(reader: FileSystemDirectoryReader): Promise<FileSystemEntry[]> {
  return new Promise<FileSystemEntry[]>((resolve, reject) => {
    reader.readEntries(resolve, reject)
  })
}

function normalizeRelativePath(path: string): string {
  const normalized = path.replace(/\\/g, '/').replace(/^\/+/, '')
  return normalized
    .split('/')
    .filter((part) => part && part !== '.' && part !== '..')
    .join('/')
}
