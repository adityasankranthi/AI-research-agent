// Mirrors api/schemas.py's ResearchRequest and api/stream.py's SSE event payloads.

export type SearchBackend = "duckduckgo" | "tavily"

export interface ResearchSettings {
  llmApiKey: string
  tavilyApiKey: string
  model: string
  apiBase: string
  searchBackend: SearchBackend
  maxSearchResults: number
  fetchFullPage: boolean
  loops: number
}

export interface SourceRef {
  title: string
  url: string
}

export interface SearchingEvent {
  query: string
}

export interface IterationEvent {
  loop: number
  loops_total: number
  search_query: string
  new_sources: SourceRef[]
  sources_total: number
  summary_preview: string
  cost_so_far: number
  calls_so_far: number
}

export interface DoneEvent {
  topic: string
  report_markdown: string
  sources: SourceRef[]
  loop_count: number
  llm_cost: number
  llm_calls: number
}

export interface ErrorEvent {
  message: string
}

export type ResearchEvent =
  | { event: "searching"; data: SearchingEvent }
  | { event: "iteration"; data: IterationEvent }
  | { event: "done"; data: DoneEvent }
  | { event: "error"; data: ErrorEvent }

// A completed run persisted to history -- deliberately has no key fields, so it's
// structurally impossible to accidentally serialize an API key into history.
export interface HistoryEntry {
  id: string
  topic: string
  timestamp: number
  reportMarkdown: string
  sources: SourceRef[]
  cost: number
  calls: number
  loopCount: number
}
