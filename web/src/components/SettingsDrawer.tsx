import { useState } from "react"
import { ChevronDown, Settings2 } from "lucide-react"
import { useSettings } from "@/context/SettingsContext"
import { ApiKeyPanel } from "./ApiKeyPanel"
import type { SearchBackend } from "@/lib/types"

const MODEL_SUGGESTIONS = [
  "openrouter/anthropic/claude-haiku-4-5",
  "anthropic/claude-haiku-4-5",
  "anthropic/claude-sonnet-5",
  "openai/gpt-4o-mini",
  "openai/gpt-4o",
]

export function SettingsDrawer() {
  const [open, setOpen] = useState(false)
  const { settings, updateSettings } = useSettings()

  return (
    <div className="w-full rounded-xl border border-zinc-200 bg-white dark:border-white/10 dark:bg-white/[0.02]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-zinc-600 dark:text-zinc-300"
      >
        <span className="flex items-center gap-2">
          <Settings2 className="size-4" />
          Settings
        </span>
        <ChevronDown className={`size-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="space-y-5 border-t border-zinc-100 px-4 py-4 dark:border-white/5">
          <ApiKeyPanel />

          <label className="block space-y-1">
            <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">Model</span>
            <input
              list="model-suggestions"
              value={settings.model}
              onChange={(e) => updateSettings({ model: e.target.value })}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 font-mono text-sm text-zinc-800 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10 focus:outline-none dark:border-white/10 dark:bg-white/[0.03] dark:text-zinc-100"
            />
            <datalist id="model-suggestions">
              {MODEL_SUGGESTIONS.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          </label>

          <div className="grid grid-cols-2 gap-4">
            <label className="block space-y-1">
              <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
                Search backend
              </span>
              <select
                value={settings.searchBackend}
                onChange={(e) => updateSettings({ searchBackend: e.target.value as SearchBackend })}
                className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-800 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10 focus:outline-none dark:border-white/10 dark:bg-white/[0.03] dark:text-zinc-100"
              >
                <option value="tavily">Tavily (needs key)</option>
                <option value="duckduckgo">DuckDuckGo (no key)</option>
              </select>
            </label>

            <label className="block space-y-1">
              <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
                Research loops: {settings.loops}
              </span>
              <input
                type="range"
                min={1}
                max={5}
                value={settings.loops}
                onChange={(e) => updateSettings({ loops: Number(e.target.value) })}
                className="w-full accent-violet-600"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <label className="block space-y-1">
              <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
                Results per search: {settings.maxSearchResults}
              </span>
              <input
                type="range"
                min={1}
                max={6}
                value={settings.maxSearchResults}
                onChange={(e) => updateSettings({ maxSearchResults: Number(e.target.value) })}
                className="w-full accent-violet-600"
              />
            </label>

            <label className="flex items-center gap-2 self-end pb-1.5">
              <input
                type="checkbox"
                checked={settings.fetchFullPage}
                onChange={(e) => updateSettings({ fetchFullPage: e.target.checked })}
                className="size-4 accent-violet-600"
              />
              <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
                Fetch full page text
              </span>
            </label>
          </div>

          <label className="block space-y-1">
            <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
              Custom API base (optional — for a self-hosted/local model server)
            </span>
            <input
              value={settings.apiBase}
              onChange={(e) => updateSettings({ apiBase: e.target.value })}
              placeholder="http://localhost:11434"
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 font-mono text-sm text-zinc-800 placeholder:text-zinc-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10 focus:outline-none dark:border-white/10 dark:bg-white/[0.03] dark:text-zinc-100 dark:placeholder:text-zinc-500"
            />
          </label>
        </div>
      )}
    </div>
  )
}
