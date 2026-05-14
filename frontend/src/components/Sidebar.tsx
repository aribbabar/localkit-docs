import type { DragEvent, FormEvent } from 'react'
import { FiSettings } from 'react-icons/fi'
import { ProgressPanel } from './ProgressPanel'
import { Brand } from './sidebar/Brand'
import { LocalDocsForm } from './sidebar/LocalDocsForm'
import { MetricGrid } from './sidebar/MetricGrid'
import { RemoteDocsForm } from './sidebar/RemoteDocsForm'
import type { BusyTask, FolderFile, OperationProgress } from '../types'
import styles from './Sidebar.module.css'

type SidebarProps = {
  activeProgress: OperationProgress | null
  busy: BusyTask
  exclude: string
  folderFiles: FolderFile[]
  include: string
  indexedSources: number
  maxDepth: number
  maxPages: number
  message: string
  onAddRemote: (event: FormEvent) => void
  onAddUploadedFolder: (event?: FormEvent) => void
  onFolderDrop: (event: DragEvent<HTMLDivElement>) => Promise<void>
  onOpenSettings: () => void
  onResetRemoteCrawlSettings: () => void
  onSelectFolderFiles: (files: FileList | File[]) => void
  remoteName: string
  remoteUrl: string
  setExclude: (value: string) => void
  setInclude: (value: string) => void
  setMaxDepth: (value: number) => void
  setMaxPages: (value: number) => void
  setRemoteName: (value: string) => void
  setRemoteUrl: (value: string) => void
  setUploadedFolderName: (value: string) => void
  sourcesCount: number
  uploadedFolderName: string
}

export function Sidebar(props: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <Brand message={props.message} />
      <MetricGrid sourcesCount={props.sourcesCount} indexedSources={props.indexedSources} />
      {props.activeProgress ? <ProgressPanel progress={props.activeProgress} /> : null}
      <LocalDocsForm
        busy={props.busy}
        folderFiles={props.folderFiles}
        onAddUploadedFolder={props.onAddUploadedFolder}
        onFolderDrop={props.onFolderDrop}
        onSelectFolderFiles={props.onSelectFolderFiles}
        setUploadedFolderName={props.setUploadedFolderName}
        uploadedFolderName={props.uploadedFolderName}
      />
      <RemoteDocsForm
        busy={props.busy}
        exclude={props.exclude}
        include={props.include}
        maxDepth={props.maxDepth}
        maxPages={props.maxPages}
        onAddRemote={props.onAddRemote}
        onResetRemoteCrawlSettings={props.onResetRemoteCrawlSettings}
        remoteName={props.remoteName}
        remoteUrl={props.remoteUrl}
        setExclude={props.setExclude}
        setInclude={props.setInclude}
        setMaxDepth={props.setMaxDepth}
        setMaxPages={props.setMaxPages}
        setRemoteName={props.setRemoteName}
        setRemoteUrl={props.setRemoteUrl}
      />
      <button className={styles.settingsButton} type="button" onClick={props.onOpenSettings}>
        <FiSettings size={16} />
        Settings
      </button>
    </aside>
  )
}
