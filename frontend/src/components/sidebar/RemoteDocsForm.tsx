import type { FormEvent } from 'react'
import { FiGlobe, FiRotateCcw } from 'react-icons/fi'
import { ImSpinner2 } from 'react-icons/im'
import type { BusyTask } from '../../types'
import controls from '../controls.module.css'
import styles from '../Sidebar.module.css'

type RemoteDocsFormProps = {
  busy: BusyTask
  crawlScope: 'path' | 'domain'
  exclude: string
  include: string
  maxDepth: number
  maxPages: number
  onAddRemote: (event: FormEvent) => void
  onResetRemoteCrawlSettings: () => void
  remoteName: string
  remoteUrl: string
  setExclude: (value: string) => void
  setCrawlScope: (value: 'path' | 'domain') => void
  setInclude: (value: string) => void
  setMaxDepth: (value: number) => void
  setMaxPages: (value: number) => void
  setRemoteName: (value: string) => void
  setRemoteUrl: (value: string) => void
}

export function RemoteDocsForm({
  busy,
  crawlScope,
  exclude,
  include,
  maxDepth,
  maxPages,
  onAddRemote,
  onResetRemoteCrawlSettings,
  remoteName,
  remoteUrl,
  setExclude,
  setCrawlScope,
  setInclude,
  setMaxDepth,
  setMaxPages,
  setRemoteName,
  setRemoteUrl,
}: RemoteDocsFormProps) {
  const includeDisabled = crawlScope === 'domain'

  return (
    <form className={styles.sourceForm} onSubmit={onAddRemote}>
      <div className={styles.sourceFormHeader}>
        <h2>Remote Docs</h2>
        <button
          className={styles.resetButton}
          type="button"
          onClick={onResetRemoteCrawlSettings}
          title="Reset remote crawl settings"
        >
          <FiRotateCcw size={14} />
          Reset
        </button>
      </div>
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
        Scope
        <span className={styles.selectWrap}>
          <select
            className={styles.scopeSelect}
            value={crawlScope}
            onChange={(event) => setCrawlScope(event.target.value === 'domain' ? 'domain' : 'path')}
          >
            <option value="path">Docs path</option>
            <option value="domain">Entire domain</option>
          </select>
        </span>
      </label>
      <label className={includeDisabled ? styles.disabledField : undefined}>
        Include patterns
        <textarea
          className={styles.patternTextarea}
          value={includeDisabled ? '' : include}
          onChange={(event) => setInclude(event.target.value)}
          disabled={includeDisabled}
          placeholder={includeDisabled ? 'Not used for entire-domain crawls' : undefined}
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
        <button className={controls.button} type="submit" disabled={busy !== null}>
          {busy === 'remote' ? <ImSpinner2 className={controls.spin} size={16} /> : <FiGlobe size={16} />}
          Crawl remote
        </button>
      </div>
    </form>
  )
}
