import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { AlertTriangle, RotateCcw, Sparkles } from "lucide-react"
import { AmbientBackground } from "@/components/AmbientBackground"
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

const screenTransition = {
  initial: { opacity: 0, y: 8, filter: "blur(4px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -8, filter: "blur(4px)" },
  transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] as const },
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
    <div className="min-h-screen">
      <AmbientBackground />
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-10 sm:px-6">
        <header className="mb-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 via-fuchsia-500 to-cyan-400 text-white shadow-lg shadow-violet-500/30">
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-violet-500 via-fuchsia-500 to-cyan-400 opacity-60 blur-md" />
              <Sparkles className="relative size-5" />
            </div>
            <div>
              <h1 className="text-base leading-tight font-semibold tracking-tight text-zinc-800 dark:text-zinc-100">
                Research Agent
              </h1>
              <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">
                search · summarize · reflect · cite
              </p>
            </div>
          </div>
          <ThemeToggle />
        </header>

        <main className="flex flex-1 flex-col gap-8">
          <AnimatePresence mode="wait">
            {displayedResult ? (
              <motion.div key="report" {...screenTransition}>
                <FinalReportView result={displayedResult} onReset={handleReset} />
              </motion.div>
            ) : stream.status === "running" ? (
              <motion.div key="running" {...screenTransition} className="space-y-6">
                <div>
                  <p className="font-mono text-xs font-medium tracking-wide text-violet-500 uppercase dark:text-violet-400">
                    Researching
                  </p>
                  <h2 className="text-xl font-medium tracking-tight text-zinc-800 dark:text-zinc-100">
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
              <motion.div key="error" {...screenTransition} className="space-y-4">
                <div className="glass flex items-start gap-2.5 rounded-xl border-red-300/50 px-4 py-3 text-sm text-red-700 dark:border-red-500/20 dark:text-red-300">
                  <AlertTriangle className="mt-0.5 size-4.5 shrink-0" />
                  <span>{stream.errorMessage}</span>
                </div>
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={handleReset}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-br from-violet-600 to-fuchsia-600 px-3.5 py-2 text-sm font-medium text-white shadow-md shadow-violet-500/30 transition-shadow hover:shadow-lg hover:shadow-violet-500/40"
                >
                  <RotateCcw className="size-3.5" />
                  Try again
                </motion.button>
              </motion.div>
            ) : (
              <motion.div key="idle" {...screenTransition} className="space-y-8">
                <div className="space-y-2 pt-4 text-center">
                  <h2 className="text-3xl font-semibold tracking-tight text-zinc-800 sm:text-4xl dark:text-zinc-100">
                    What should I <span className="text-gradient">research</span>?
                  </h2>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    Every claim comes back cited, and checked against the sources gathered for it.
                  </p>
                </div>
                <TopicForm onSubmit={handleSubmit} />
                <SettingsDrawer />
                <HistorySidebar onSelect={setViewingHistory} refreshKey={historyRefreshKey} />
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        <footer className="mt-12 text-center font-mono text-xs text-zinc-400 dark:text-zinc-600">
          Every claim is cited inline and checked against gathered sources.
        </footer>
      </div>
    </div>
  )
}
