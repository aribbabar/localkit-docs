import type { FormEvent } from 'react'
import { Save } from 'lucide-react'
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
        <button className={styles.refreshButton} type="button" onClick={onBackToSources}>
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
          <Save size={16} />
          Save settings
        </button>
      </form>
    </section>
  )
}
