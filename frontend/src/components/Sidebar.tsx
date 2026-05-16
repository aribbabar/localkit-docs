import type { DragEvent, FormEvent } from 'react'
import { FiSettings, FiZap } from 'react-icons/fi'
import { ProgressPanel } from './ProgressPanel'
import { Brand } from './sidebar/Brand'
import { LocalDocsForm } from './sidebar/LocalDocsForm'
import { RemoteDocsForm } from './sidebar/RemoteDocsForm'
import type { BusyTask, FolderFile, OperationProgress } from '../types'
import styles from './Sidebar.module.css'

type SidebarProps = {
  activeProgress: OperationProgress | null
  busy: BusyTask
  crawlScope: 'path' | 'domain'
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
  setCrawlScope: (value: 'path' | 'domain') => void
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
      <div className={styles.consoleIntro}>
        <Brand message={props.message} />
        <button className={styles.settingsButton} type="button" onClick={props.onOpenSettings}>
          <FiSettings size={16} />
          Settings
        </button>
      </div>
      <div className={styles.homeHero}>
        <span className={styles.eyebrow}>
          <FiZap aria-hidden="true" />
          Local-first docs search
        </span>
        <h2>Documentation index</h2>
        <p>Bring local folders and remote docs into one searchable workspace for coding agents.</p>
      </div>
      {props.activeProgress ? <ProgressPanel progress={props.activeProgress} /> : null}
      <div className={styles.ingestGrid}>
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
          crawlScope={props.crawlScope}
          exclude={props.exclude}
          include={props.include}
          maxDepth={props.maxDepth}
          maxPages={props.maxPages}
          onAddRemote={props.onAddRemote}
          onResetRemoteCrawlSettings={props.onResetRemoteCrawlSettings}
          remoteName={props.remoteName}
          remoteUrl={props.remoteUrl}
          setExclude={props.setExclude}
          setCrawlScope={props.setCrawlScope}
          setInclude={props.setInclude}
          setMaxDepth={props.setMaxDepth}
          setMaxPages={props.setMaxPages}
          setRemoteName={props.setRemoteName}
          setRemoteUrl={props.setRemoteUrl}
        />
      </div>
    </aside>
  )
}
