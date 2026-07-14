import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { AlertTriangle, RotateCcw, Sparkles } from "lucide-react"
import { ThemeToggle } from "@/components/ThemeToggle"
import { TopicForm } from "@/components/TopicForm"
import { SettingsDrawer } from "@/components/SettingsDrawer"
import { HistorySidebar } from "@/components/HistorySidebar"
import { ResearchProgress } from "@/components/ResearchProgress"
import { FinalReportView } from "@/components/FinalReportView"
import { useSettings } from "@/context/SettingsContext"
import { useResearchStream } from "@/hooks/useResearchStream"
import type { DoneEvent, HistoryEntry } from "@/lib/types"

function toDoneEvent(entry: HistoryEntry): DoneEvent {
  return {
    topic: entry.topic,
    report_markdown: entry.reportMarkdown,
    sources: entry.sources,
    loop_count: entry.loopCount,
    llm_cost: entry.cost,
    llm_calls: entry.calls,
  }
}

export default function App() {
  const { settings } = useSettings()
  const stream = useResearchStream()
  const [activeTopic, setActiveTopic] = useState("")
  const [viewingHistory, setViewingHistory] = useState<HistoryEntry | null>(null)
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0)

  useEffect(() => {
    if (stream.status === "done") setHistoryRefreshKey((k) => k + 1)
  }, [stream.status])

  const handleSubmit = (topic: string) => {
    setActiveTopic(topic)
    setViewingHistory(null)
    stream.start(topic)
  }

  const handleReset = () => {
    setViewingHistory(null)
    stream.reset()
  }

  const displayedResult = viewingHistory ? toDoneEvent(viewingHistory) : stream.result

  return (
    <div className="min-h-screen bg-gradient-to-b from-violet-50/40 via-transparent to-transparent dark:from-violet-500/[0.04]">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-10 sm:px-6">
        <header className="mb-10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-cyan-400 text-white shadow-sm shadow-violet-500/30">
              <Sparkles className="size-4.5" />
            </div>
            <div>
              <h1 className="text-base leading-tight font-semibold text-zinc-800 dark:text-zinc-100">
                Research Agent
              </h1>
              <p className="text-xs text-zinc-400 dark:text-zinc-500">
                Search · summarize · reflect · cite
              </p>
            </div>
          </div>
          <ThemeToggle />
        </header>

        <main className="flex flex-1 flex-col gap-8">
          <AnimatePresence mode="wait">
            {displayedResult ? (
              <motion.div
                key="report"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <FinalReportView result={displayedResult} onReset={handleReset} />
              </motion.div>
            ) : stream.status === "running" ? (
              <motion.div
                key="running"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                <div>
                  <p className="text-xs font-medium text-zinc-400 dark:text-zinc-500">Researching</p>
                  <h2 className="text-lg font-medium text-zinc-800 dark:text-zinc-100">
                    {activeTopic}
                  </h2>
                </div>
                <ResearchProgress
                  currentQuery={stream.currentQuery}
                  iterations={stream.iterations}
                  loopsTotal={settings.loops}
                />
              </motion.div>
            ) : stream.status === "error" ? (
              <motion.div
                key="error"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                <div className="flex items-start gap-2.5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
                  <AlertTriangle className="mt-0.5 size-4.5 shrink-0" />
                  <span>{stream.errorMessage}</span>
                </div>
                <button
                  onClick={handleReset}
                  className="inline-flex items-center gap-1.5 rounded-md bg-violet-600 px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500"
                >
                  <RotateCcw className="size-3.5" />
                  Try again
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                <TopicForm onSubmit={handleSubmit} />
                <SettingsDrawer />
                <HistorySidebar onSelect={setViewingHistory} refreshKey={historyRefreshKey} />
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        <footer className="mt-12 text-center font-mono text-xs text-zinc-300 dark:text-zinc-600">
          Every claim is cited inline and checked against gathered sources.
        </footer>
      </div>
    </div>
  )
}
