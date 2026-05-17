import { useEffect, useMemo, useRef, useState } from 'react'
import type { DragEvent, FormEvent } from 'react'
import { FiFolderPlus, FiUploadCloud } from 'react-icons/fi'
import { ImSpinner2 } from 'react-icons/im'
import { classNames } from '../../utils/classNames'
import { summarizePendingFiles } from '../../utils/folderFiles'
import type { BusyTask, FolderFile } from '../../types'
import controls from '../controls.module.css'
import styles from '../Sidebar.module.css'

type LocalDocsFormProps = {
  busy: BusyTask
  folderFiles: FolderFile[]
  onAddUploadedFolder: (event?: FormEvent) => void
  onFolderDrop: (event: DragEvent<HTMLDivElement>) => Promise<void>
  onSelectFolderFiles: (files: FileList | File[]) => void
  setUploadedFolderName: (value: string) => void
  uploadedFolderName: string
}

export function LocalDocsForm({
  busy,
  folderFiles,
  onAddUploadedFolder,
  onFolderDrop,
  onSelectFolderFiles,
  setUploadedFolderName,
  uploadedFolderName,
}: LocalDocsFormProps) {
  const [dragActive, setDragActive] = useState(false)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const pendingSummary = useMemo(() => summarizePendingFiles(folderFiles), [folderFiles])

  useEffect(() => {
    folderInputRef.current?.setAttribute('webkitdirectory', '')
    folderInputRef.current?.setAttribute('directory', '')
  }, [])

  async function handleDrop(event: DragEvent<HTMLDivElement>) {
    setDragActive(false)
    await onFolderDrop(event)
  }

  function chooseFolderFiles(files: FileList | null) {
    onSelectFolderFiles(files ?? [])
    if (folderInputRef.current) {
      folderInputRef.current.value = ''
    }
  }

  return (
    <form className={styles.sourceForm} onSubmit={onAddUploadedFolder}>
      <h2>Local Docs</h2>
      <input
        ref={folderInputRef}
        className={controls.srOnly}
        type="file"
        multiple
        onChange={(event) => chooseFolderFiles(event.target.files)}
      />
      <div
        className={classNames(styles.dropzone, dragActive && styles.dropzoneActive)}
        role="button"
        tabIndex={0}
        onDragEnter={(event) => {
          event.preventDefault()
          setDragActive(true)
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (event.currentTarget.contains(event.relatedTarget as Node | null)) return
          setDragActive(false)
        }}
        onDrop={handleDrop}
        onClick={() => {
          if (busy === null) folderInputRef.current?.click()
        }}
        onKeyDown={(event) => {
          if (busy !== null) return
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            folderInputRef.current?.click()
          }
        }}
      >
        <FiUploadCloud size={22} />
        <strong>
          {busy === 'upload-folder'
            ? `Adding ${uploadedFolderName || 'local docs'}`
            : folderFiles.length > 0
              ? pendingSummary
              : 'Drop folders or files here'}
        </strong>
        <span>
          {busy === 'upload-folder'
            ? `${folderFiles.length} files uploading`
            : folderFiles.length > 0
              ? 'Drop more folders or files to add them to this source.'
              : 'Click to choose a folder, or drop folders and files.'}
        </span>
      </div>
      <label>
        Name
        <input
          value={uploadedFolderName}
          onChange={(event) => setUploadedFolderName(event.target.value)}
          placeholder="e.g. library-docs"
        />
      </label>
      <button className={controls.button} type="submit" disabled={busy !== null || folderFiles.length === 0}>
        {busy === 'upload-folder' ? (
          <ImSpinner2 className={controls.spin} size={16} />
        ) : (
          <FiFolderPlus size={16} />
        )}
        Add local
      </button>
    </form>
  )
}
