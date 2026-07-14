import { Lock } from "lucide-react"
import { useSettings } from "@/context/SettingsContext"

export function ApiKeyPanel() {
  const { settings, updateSettings } = useSettings()

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2 rounded-lg bg-zinc-50 px-3 py-2.5 text-xs text-zinc-500 dark:bg-white/[0.03] dark:text-zinc-400">
        <Lock className="mt-0.5 size-3.5 shrink-0 text-zinc-400 dark:text-zinc-500" />
        <span>
          Keys are stored only in your browser (localStorage) and sent directly with each
          research request — never saved on our server.
        </span>
      </div>

      <label className="block space-y-1">
        <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
          Model provider API key
        </span>
        <input
          type="password"
          autoComplete="off"
          spellCheck={false}
          value={settings.llmApiKey}
          onChange={(e) => updateSettings({ llmApiKey: e.target.value })}
          placeholder="sk-... / anthropic key / openrouter key"
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 font-mono text-sm text-zinc-800 placeholder:text-zinc-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10 focus:outline-none dark:border-white/10 dark:bg-white/[0.03] dark:text-zinc-100 dark:placeholder:text-zinc-500"
        />
      </label>

      {settings.searchBackend === "tavily" && (
        <label className="block space-y-1">
          <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
            Tavily API key{" "}
            <a
              href="https://tavily.com"
              target="_blank"
              rel="noreferrer"
              className="text-violet-500 hover:underline"
            >
              (free tier)
            </a>
          </span>
          <input
            type="password"
            autoComplete="off"
            spellCheck={false}
            value={settings.tavilyApiKey}
            onChange={(e) => updateSettings({ tavilyApiKey: e.target.value })}
            placeholder="tvly-..."
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 font-mono text-sm text-zinc-800 placeholder:text-zinc-400 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/10 focus:outline-none dark:border-white/10 dark:bg-white/[0.03] dark:text-zinc-100 dark:placeholder:text-zinc-500"
          />
        </label>
      )}
    </div>
  )
}
