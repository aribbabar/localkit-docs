import type { FormEvent } from 'react'
import { FiArrowLeft, FiSave } from 'react-icons/fi'
import { classNames } from '../../utils/classNames'
import controls from '../controls.module.css'
import styles from '../MainPanel.module.css'

type SettingsPanelProps = {
  localDocsMaxFiles: number
  onBackToSources: () => void
  onSaveLocalDocsMaxFiles: (value: number) => void
}

export function SettingsPanel({
  localDocsMaxFiles,
  onBackToSources,
  onSaveLocalDocsMaxFiles,
}: SettingsPanelProps) {
  function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    onSaveLocalDocsMaxFiles(Number(formData.get('localDocsMaxFiles')))
  }

  return (
    <section className={styles.panel}>
      <div className={styles.panelHeader}>
        <div>
          <h1>Settings</h1>
          <p>Adjust local ingestion limits for this browser.</p>
        </div>
        <button className={classNames(controls.button, controls.ghost)} type="button" onClick={onBackToSources}>
          <FiArrowLeft size={15} />
          Sources
        </button>
      </div>
      <form className={styles.settingsForm} onSubmit={saveSettings}>
        <section className={styles.settingsSection}>
          <div>
            <h2>Local Docs</h2>
            <p>Set how many files a folder upload can include before LocalKit stops it.</p>
          </div>
          <label>
            Maximum files
            <input
              name="localDocsMaxFiles"
              type="number"
              min={1}
              max={100000}
              step={100}
              defaultValue={localDocsMaxFiles}
            />
          </label>
        </section>
        <button className={controls.button} type="submit">
          <FiSave size={16} />
          Save settings
        </button>
      </form>
    </section>
  )
}
