import { useEffect, useState } from "react"
import { History, Trash2 } from "lucide-react"
import { clearHistory, loadHistory } from "@/lib/storage"
import type { HistoryEntry } from "@/lib/types"

interface HistorySidebarProps {
  onSelect: (entry: HistoryEntry) => void
  refreshKey: number
}

export function HistorySidebar({ onSelect, refreshKey }: HistorySidebarProps) {
  const [history, setHistory] = useState<HistoryEntry[]>([])

  useEffect(() => {
    setHistory(loadHistory())
  }, [refreshKey])

  if (history.length === 0) return null

  return (
    <div className="w-full space-y-2">
      <div className="flex items-center justify-between px-1">
        <span className="flex items-center gap-1.5 text-xs font-medium text-zinc-400 dark:text-zinc-500">
          <History className="size-3.5" />
          Past research
        </span>
        <button
          onClick={() => {
            clearHistory()
            setHistory([])
          }}
          className="flex items-center gap-1 text-xs text-zinc-400 hover:text-red-500 dark:text-zinc-500"
        >
          <Trash2 className="size-3" />
          Clear
        </button>
      </div>
      <div className="flex flex-col gap-1.5">
        {history.map((entry) => (
          <button
            key={entry.id}
            onClick={() => onSelect(entry)}
            className="glass-subtle truncate rounded-lg px-3 py-2 text-left text-sm text-zinc-600 transition-colors hover:border-violet-300/70 hover:text-violet-700 dark:text-zinc-300 dark:hover:border-violet-400/30 dark:hover:text-violet-300"
          >
            {entry.topic}
          </button>
        ))}
      </div>
    </div>
  )
}
