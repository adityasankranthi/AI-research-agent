import { useMemo, useState } from "react"
import { motion } from "framer-motion"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Check, Copy, Download, RotateCcw } from "lucide-react"
import { GroundingCallout } from "./GroundingCallout"
import { CostBadge } from "./CostBadge"
import { splitGroundingSection } from "@/lib/grounding"
import type { DoneEvent } from "@/lib/types"

export function FinalReportView({ result, onReset }: { result: DoneEvent; onReset: () => void }) {
  const [copied, setCopied] = useState(false)
  const { body, unverifiedClaims } = useMemo(
    () => splitGroundingSection(result.report_markdown),
    [result.report_markdown],
  )

  const handleCopy = async () => {
    await navigator.clipboard.writeText(result.report_markdown)
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  const handleDownload = () => {
    const blob = new Blob([result.report_markdown], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${result.topic.slice(0, 60).replace(/[^\w\- ]/g, "").trim() || "report"}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="w-full space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <CostBadge cost={result.llm_cost} calls={result.llm_calls} />
          <span className="font-mono text-xs text-zinc-400 dark:text-zinc-500">
            {result.loop_count} loop{result.loop_count === 1 ? "" : "s"} · {result.sources.length}{" "}
            source{result.sources.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="glass-subtle inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-white/60 dark:text-zinc-300 dark:hover:bg-white/10"
          >
            {copied ? <Check className="size-3.5 text-emerald-500" /> : <Copy className="size-3.5" />}
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            onClick={handleDownload}
            className="glass-subtle inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-600 transition-colors hover:bg-white/60 dark:text-zinc-300 dark:hover:bg-white/10"
          >
            <Download className="size-3.5" />
            Download
          </button>
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={onReset}
            className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-br from-violet-600 to-fuchsia-600 px-3 py-1.5 text-xs font-medium text-white shadow-md shadow-violet-500/30 transition-shadow hover:shadow-lg hover:shadow-violet-500/40"
          >
            <RotateCcw className="size-3.5" />
            New research
          </motion.button>
        </div>
      </div>

      <GroundingCallout unverifiedClaims={unverifiedClaims} />

      <article className="glass prose prose-zinc dark:prose-invert prose-sm sm:prose-base max-w-none rounded-2xl p-6 prose-a:text-violet-600 dark:prose-a:text-violet-400">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{body}</ReactMarkdown>
      </article>
    </div>
  )
}
