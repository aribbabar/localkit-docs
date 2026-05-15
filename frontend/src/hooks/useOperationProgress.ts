import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchOperation } from '../api/docsApi'
import type { OperationProgress } from '../types'

const ACTIVE_OPERATION_KEY = 'localkit.activeOperation'
const ACTIVE_OPERATION_TTL_MS = 12 * 60 * 60 * 1000

export function useOperationProgress() {
  const [activeProgress, setActiveProgress] = useState<OperationProgress | null>(null)
  const progressTimeoutRef = useRef<number | null>(null)
  const progressIntervalRef = useRef<number | null>(null)

  const clearProgressInterval = useCallback(() => {
    if (progressIntervalRef.current !== null) {
      window.clearInterval(progressIntervalRef.current)
      progressIntervalRef.current = null
    }
  }, [])

  const clearProgressTimeout = useCallback(() => {
    if (progressTimeoutRef.current !== null) {
      window.clearTimeout(progressTimeoutRef.current)
      progressTimeoutRef.current = null
    }
  }, [])

  const refreshOperation = useCallback(
    async (operationId: string): Promise<OperationProgress | null> => {
      const progress = await fetchOperation(operationId)
      if (!progress) return null

      setActiveProgress(progress)
      if (isTerminalProgress(progress)) {
        clearSavedOperation(operationId)
        clearProgressInterval()
      }
      return progress
    },
    [clearProgressInterval],
  )

  const scheduleProgressClear = useCallback(
    (operationId: string) => {
      clearProgressTimeout()
      progressTimeoutRef.current = window.setTimeout(() => {
        setActiveProgress((current) =>
          current?.operation_id === operationId ? null : current,
        )
        progressTimeoutRef.current = null
      }, 3500)
    },
    [clearProgressTimeout],
  )

  const startProgressPolling = useCallback(
    (operationId: string): () => Promise<void> => {
      clearProgressTimeout()
      clearProgressInterval()
      saveOperationId(operationId)

      setActiveProgress({
        operation_id: operationId,
        phase: 'queued',
        status: 'running',
        message: 'Waiting for operation to start',
        current: 0,
        events: [],
      })
      void refreshOperation(operationId)

      progressIntervalRef.current = window.setInterval(() => {
        void refreshOperation(operationId)
      }, 500)

      return async () => {
        clearProgressInterval()
        const progress = await refreshOperation(operationId)
        if (!progress || isTerminalProgress(progress)) {
          clearSavedOperation(operationId)
        }
        scheduleProgressClear(operationId)
      }
    },
    [clearProgressInterval, clearProgressTimeout, refreshOperation, scheduleProgressClear],
  )

  const waitForOperation = useCallback(async (operationId: string): Promise<OperationProgress> => {
    while (true) {
      const progress = await refreshOperation(operationId)
      if (progress && isTerminalProgress(progress)) {
        if (progress.status === 'failed') {
          throw new Error(progress.message ?? 'Operation failed')
        }
        return progress
      }
      await sleep(500)
    }
  }, [refreshOperation])

  useEffect(() => {
    const savedOperationId = readSavedOperationId()
    let resumeTimeout: number | null = null
    if (savedOperationId) {
      resumeTimeout = window.setTimeout(() => {
        startProgressPolling(savedOperationId)
      }, 0)
    }

    return () => {
      if (resumeTimeout !== null) window.clearTimeout(resumeTimeout)
      if (progressTimeoutRef.current !== null) window.clearTimeout(progressTimeoutRef.current)
      if (progressIntervalRef.current !== null) window.clearInterval(progressIntervalRef.current)
    }
  }, [startProgressPolling])

  return { activeProgress, startProgressPolling, waitForOperation }
}

function isTerminalProgress(progress: OperationProgress): boolean {
  return progress.status === 'completed' || progress.status === 'failed'
}

function saveOperationId(operationId: string) {
  window.localStorage.setItem(
    ACTIVE_OPERATION_KEY,
    JSON.stringify({ operationId, savedAt: Date.now() }),
  )
}

function readSavedOperationId(): string | null {
  try {
    const value = window.localStorage.getItem(ACTIVE_OPERATION_KEY)
    if (!value) return null
    const parsed = JSON.parse(value) as { operationId?: unknown; savedAt?: unknown }
    if (typeof parsed.operationId !== 'string' || typeof parsed.savedAt !== 'number') {
      window.localStorage.removeItem(ACTIVE_OPERATION_KEY)
      return null
    }
    if (Date.now() - parsed.savedAt > ACTIVE_OPERATION_TTL_MS) {
      window.localStorage.removeItem(ACTIVE_OPERATION_KEY)
      return null
    }
    return parsed.operationId
  } catch {
    window.localStorage.removeItem(ACTIVE_OPERATION_KEY)
    return null
  }
}

function clearSavedOperation(operationId: string) {
  const savedOperationId = readSavedOperationId()
  if (savedOperationId === operationId) {
    window.localStorage.removeItem(ACTIVE_OPERATION_KEY)
  }
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}
