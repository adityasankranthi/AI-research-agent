import type { HistoryEntry, ResearchSettings } from "./types"

const SETTINGS_KEY = "research-agent:settings"
const HISTORY_KEY = "research-agent:history"
const THEME_KEY = "research-agent:theme"
const MAX_HISTORY_ENTRIES = 20

export const DEFAULT_SETTINGS: ResearchSettings = {
  llmApiKey: "",
  tavilyApiKey: "",
  model: "openrouter/anthropic/claude-haiku-4-5",
  apiBase: "",
  searchBackend: "tavily",
  maxSearchResults: 3,
  fetchFullPage: false,
  loops: 2,
}

export function loadSettings(): ResearchSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (!raw) return DEFAULT_SETTINGS
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) }
  } catch {
    return DEFAULT_SETTINGS
  }
}

export function saveSettings(settings: ResearchSettings): void {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
}

export function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    return JSON.parse(raw)
  } catch {
    return []
  }
}

export function pushHistoryEntry(entry: HistoryEntry): HistoryEntry[] {
  const next = [entry, ...loadHistory()].slice(0, MAX_HISTORY_ENTRIES)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
  return next
}

export function clearHistory(): void {
  localStorage.removeItem(HISTORY_KEY)
}

export type Theme = "light" | "dark"

export function loadTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === "light" || stored === "dark") return stored
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
}

export function saveTheme(theme: Theme): void {
  localStorage.setItem(THEME_KEY, theme)
}
