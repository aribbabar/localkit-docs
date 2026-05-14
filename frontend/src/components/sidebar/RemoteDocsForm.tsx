import type { FormEvent } from 'react'
import { FiGlobe } from 'react-icons/fi'
import { ImSpinner2 } from 'react-icons/im'
import type { BusyTask } from '../../types'
import controls from '../controls.module.css'
import styles from '../Sidebar.module.css'

type RemoteDocsFormProps = {
  busy: BusyTask
  include: string
  maxDepth: number
  maxPages: number
  onAddRemote: (event: FormEvent) => void
  remoteName: string
  remoteUrl: string
  setInclude: (value: string) => void
  setMaxDepth: (value: number) => void
  setMaxPages: (value: number) => void
  setRemoteName: (value: string) => void
  setRemoteUrl: (value: string) => void
}

export function RemoteDocsForm({
  busy,
  include,
  maxDepth,
  maxPages,
  onAddRemote,
  remoteName,
  remoteUrl,
  setInclude,
  setMaxDepth,
  setMaxPages,
  setRemoteName,
  setRemoteUrl,
}: RemoteDocsFormProps) {
  return (
    <form className={styles.sourceForm} onSubmit={onAddRemote}>
      <h2>Remote Docs</h2>
      <label>
        URL
        <input
          value={remoteUrl}
          onChange={(event) => setRemoteUrl(event.target.value)}
          placeholder="https://example.com/docs/"
          required
        />
      </label>
      <label>
        Name
        <input
          value={remoteName}
          onChange={(event) => setRemoteName(event.target.value)}
          placeholder="example-docs"
        />
      </label>
      <div className={styles.split}>
        <label>
          Include
          <input value={include} onChange={(event) => setInclude(event.target.value)} />
        </label>
        <label>
          Depth
          <input
            type="number"
            min={1}
            max={20}
            value={maxDepth}
            onChange={(event) => setMaxDepth(Number(event.target.value))}
          />
        </label>
      </div>
      <label>
        Max pages
        <input
          type="number"
          min={1}
          max={5000}
          value={maxPages}
          onChange={(event) => setMaxPages(Number(event.target.value))}
        />
      </label>
      <button className={controls.button} type="submit" disabled={busy !== null}>
        {busy === 'remote' ? <ImSpinner2 className={controls.spin} size={16} /> : <FiGlobe size={16} />}
        Crawl remote
      </button>
    </form>
  )
}
