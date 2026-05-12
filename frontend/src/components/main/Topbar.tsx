import type { FormEvent, RefObject } from 'react'
import { ArrowLeft, Loader2, Play, RefreshCw, Search } from 'lucide-react'
import { classNames } from '../../utils/classNames'
import type { BusyTask, Source } from '../../types'
import controls from '../controls.module.css'
import styles from '../MainPanel.module.css'

type TopbarProps = {
  busy: BusyTask
  onBackToSources: () => void
  onRefreshSources: () => void
  onSearchDocs: (event: FormEvent) => void
  query: string
  searchInputRef: RefObject<HTMLInputElement | null>
  selectedSource: Source | null
  setQuery: (value: string) => void
}

export function Topbar({
  busy,
  onBackToSources,
  onRefreshSources,
  onSearchDocs,
  query,
  searchInputRef,
  selectedSource,
  setQuery,
}: TopbarProps) {
  return (
    <div className={styles.topbar}>
      <div className={styles.sourceHeader}>
        <button
          className={classNames(controls.button, controls.iconButton, controls.ghost)}
          type="button"
          title="Back to sources"
          onClick={onBackToSources}
          disabled={busy !== null}
        >
          <ArrowLeft size={16} />
        </button>
        <div>
          <h1>{selectedSource?.name ?? 'Source'}</h1>
          <p>{selectedSource?.origin ?? 'Loading source details'}</p>
        </div>
      </div>
      <form className={styles.searchbar} onSubmit={onSearchDocs}>
        <Search size={18} />
        <input
          ref={searchInputRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search indexed documentation"
        />
        <button className={controls.button} type="submit" disabled={busy !== null || !query.trim()}>
          {busy === 'search' ? <Loader2 className={controls.spin} size={16} /> : <Play size={16} />}
          Search
        </button>
      </form>
      <button
        className={classNames(controls.button, controls.ghost)}
        type="button"
        onClick={onRefreshSources}
        disabled={busy !== null}
      >
        <RefreshCw size={16} />
        Refresh
      </button>
    </div>
  )
}
