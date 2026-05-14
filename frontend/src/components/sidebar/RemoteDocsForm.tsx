import type { FormEvent } from 'react'
import { FiGlobe, FiRotateCcw } from 'react-icons/fi'
import { ImSpinner2 } from 'react-icons/im'
import type { BusyTask } from '../../types'
import { classNames } from '../../utils/classNames'
import controls from '../controls.module.css'
import styles from '../Sidebar.module.css'

type RemoteDocsFormProps = {
  busy: BusyTask
  exclude: string
  include: string
  maxDepth: number
  maxPages: number
  onAddRemote: (event: FormEvent) => void
  onResetRemoteCrawlSettings: () => void
  remoteName: string
  remoteUrl: string
  setExclude: (value: string) => void
  setInclude: (value: string) => void
  setMaxDepth: (value: number) => void
  setMaxPages: (value: number) => void
  setRemoteName: (value: string) => void
  setRemoteUrl: (value: string) => void
}

export function RemoteDocsForm({
  busy,
  exclude,
  include,
  maxDepth,
  maxPages,
  onAddRemote,
  onResetRemoteCrawlSettings,
  remoteName,
  remoteUrl,
  setExclude,
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
      <label>
        Include patterns
        <textarea
          className={styles.patternTextarea}
          value={include}
          onChange={(event) => setInclude(event.target.value)}
          rows={2}
          spellCheck={false}
        />
      </label>
      <label>
        Exclude patterns
        <textarea
          className={styles.patternTextarea}
          value={exclude}
          onChange={(event) => setExclude(event.target.value)}
          rows={6}
          spellCheck={false}
        />
      </label>
      <div className={styles.splitEven}>
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
      </div>
      <div className={styles.formActions}>
        <button className={classNames(controls.button, controls.ghost)} type="button" onClick={onResetRemoteCrawlSettings}>
          <FiRotateCcw size={16} />
          Reset
        </button>
        <button className={controls.button} type="submit" disabled={busy !== null}>
          {busy === 'remote' ? <ImSpinner2 className={controls.spin} size={16} /> : <FiGlobe size={16} />}
          Crawl remote
        </button>
      </div>
    </form>
  )
}
