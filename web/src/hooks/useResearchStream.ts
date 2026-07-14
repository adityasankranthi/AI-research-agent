import { useCallback, useRef, useState } from "react"
import { streamResearch } from "@/lib/sse"
import { pushHistoryEntry } from "@/lib/storage"
import { useSettings } from "@/context/SettingsContext"
import type { DoneEvent, IterationEvent, SourceRef } from "@/lib/types"

export type RunStatus = "idle" | "running" | "done" | "error"

export interface ResearchStreamState {
  status: RunStatus
  currentQuery: string | null
  iterations: IterationEvent[]
  sources: SourceRef[]
  result: DoneEvent | null
  errorMessage: string | null
  start: (topic: string) => void
  reset: () => void
}

const initialState = {
  status: "idle" as RunStatus,
  currentQuery: null as string | null,
  iterations: [] as IterationEvent[],
  sources: [] as SourceRef[],
  result: null as DoneEvent | null,
  errorMessage: null as string | null,
}

export function useResearchStream(): ResearchStreamState {
  const { settings } = useSettings()
  const [state, setState] = useState(initialState)
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(initialState)
  }, [])

  const start = useCallback(
    (topic: string) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setState({ ...initialState, status: "running" })

      const body = {
        topic,
        model: settings.model,
        api_base: settings.apiBase || null,
        search_backend: settings.searchBackend,
        max_search_results: settings.maxSearchResults,
        fetch_full_page: settings.fetchFullPage,
        loops: settings.loops,
        llm_api_key: settings.llmApiKey,
        tavily_api_key: settings.searchBackend === "tavily" ? settings.tavilyApiKey : null,
      }

      ;(async () => {
        try {
          for await (const evt of streamResearch("/api/research", body, controller.signal)) {
            if (evt.event === "searching") {
              setState((s) => ({ ...s, currentQuery: evt.data.query }))
            } else if (evt.event === "iteration") {
              setState((s) => ({
                ...s,
                iterations: [...s.iterations, evt.data],
                sources: [...s.sources, ...evt.data.new_sources],
              }))
            } else if (evt.event === "done") {
              setState((s) => ({ ...s, status: "done", result: evt.data }))
              pushHistoryEntry({
                id: crypto.randomUUID(),
                topic: evt.data.topic,
                timestamp: Date.now(),
                reportMarkdown: evt.data.report_markdown,
                sources: evt.data.sources,
                cost: evt.data.llm_cost,
                calls: evt.data.llm_calls,
                loopCount: evt.data.loop_count,
              })
            } else if (evt.event === "error") {
              setState((s) => ({ ...s, status: "error", errorMessage: evt.data.message }))
            }
          }
        } catch (err) {
          if (controller.signal.aborted) return
          const message = err instanceof Error ? err.message : "Something went wrong."
          setState((s) => ({ ...s, status: "error", errorMessage: message }))
        }
      })()
    },
    [settings],
  )

  return { ...state, start, reset }
}
