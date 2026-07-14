import { AnimatePresence, motion } from "framer-motion"
import { Loader2, Search } from "lucide-react"
import { CostBadge } from "./CostBadge"
import { SourceCard } from "./SourceCard"
import type { IterationEvent } from "@/lib/types"

interface ResearchProgressProps {
  currentQuery: string | null
  iterations: IterationEvent[]
  loopsTotal: number
}

export function ResearchProgress({ currentQuery, iterations, loopsTotal }: ResearchProgressProps) {
  const latest = iterations[iterations.length - 1]
  const loopsDone = latest?.loop ?? 0
  const isSearchingNextLoop = currentQuery !== null && currentQuery !== latest?.search_query

  return (
    <div className="w-full space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-mono text-sm text-zinc-500 dark:text-zinc-400">
          <Loader2 className="size-4 animate-spin text-violet-500" />
          <span>
            loop {Math.min(loopsDone + (isSearchingNextLoop ? 1 : 0), loopsTotal)}/{loopsTotal}
          </span>
        </div>
        {latest && <CostBadge cost={latest.cost_so_far} calls={latest.calls_so_far} />}
      </div>

      <AnimatePresence mode="wait">
        {currentQuery && (
          <motion.div
            key={currentQuery}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 rounded-lg border border-violet-200 bg-violet-50/60 px-4 py-3 dark:border-violet-400/20 dark:bg-violet-500/[0.07]"
          >
            <Search className="size-4 shrink-0 text-violet-500" />
            <p className="font-mono text-sm text-violet-800 italic dark:text-violet-300">
              Searching: {currentQuery}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-6">
        {iterations.map((iteration) => (
          <div key={iteration.loop} className="animate-fade-in-up space-y-2.5">
            <p className="font-mono text-xs tracking-wide text-zinc-400 uppercase dark:text-zinc-500">
              Loop {iteration.loop} · {iteration.new_sources.length} new source
              {iteration.new_sources.length === 1 ? "" : "s"} · {iteration.sources_total} total
            </p>
            {iteration.new_sources.length > 0 && (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {iteration.new_sources.map((source, i) => (
                  <SourceCard key={source.url} source={source} index={i} />
                ))}
              </div>
            )}
            {iteration.summary_preview && (
              <p className="line-clamp-2 text-sm text-zinc-500 dark:text-zinc-400">
                {iteration.summary_preview}…
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
