import { useEffect, useRef, useState } from 'react'
import { fetchOperation } from '../api/docsApi'
import type { OperationProgress } from '../types'

export function useOperationProgress() {
  const [activeProgress, setActiveProgress] = useState<OperationProgress | null>(null)
  const progressTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (progressTimeoutRef.current !== null) window.clearTimeout(progressTimeoutRef.current)
    }
  }, [])

  async function refreshOperation(operationId: string): Promise<void> {
    const progress = await fetchOperation(operationId)
    if (progress) setActiveProgress(progress)
  }

  function startProgressPolling(operationId: string): () => Promise<void> {
    if (progressTimeoutRef.current !== null) {
      window.clearTimeout(progressTimeoutRef.current)
      progressTimeoutRef.current = null
    }

    setActiveProgress({
      operation_id: operationId,
      phase: 'queued',
      status: 'running',
      message: 'Waiting for operation to start',
      current: 0,
      events: [],
    })
    void refreshOperation(operationId)

    const intervalId = window.setInterval(() => {
      void refreshOperation(operationId)
    }, 500)

    return async () => {
      window.clearInterval(intervalId)
      await refreshOperation(operationId)
      progressTimeoutRef.current = window.setTimeout(() => {
        setActiveProgress((current) =>
          current?.operation_id === operationId ? null : current,
        )
        progressTimeoutRef.current = null
      }, 3500)
    }
  }

  return { activeProgress, startProgressPolling }
}
