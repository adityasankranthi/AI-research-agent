import { motion } from "framer-motion"
import type { SourceRef } from "@/lib/types"

function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return url
  }
}

export function SourceCard({ source, index }: { source: SourceRef; index: number }) {
  const domain = hostname(source.url)

  return (
    <motion.a
      href={source.url}
      target="_blank"
      rel="noreferrer"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05 }}
      className="group flex items-start gap-2.5 rounded-lg border border-zinc-200 bg-white px-3 py-2.5 transition-colors hover:border-violet-300 hover:bg-violet-50/50 dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-violet-400/30 dark:hover:bg-violet-500/[0.06]"
    >
      <img
        src={`https://www.google.com/s2/favicons?domain=${domain}&sz=32`}
        alt=""
        className="mt-0.5 size-4 shrink-0 rounded-sm"
        loading="lazy"
      />
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-zinc-800 group-hover:text-violet-700 dark:text-zinc-200 dark:group-hover:text-violet-300">
          {source.title}
        </p>
        <p className="truncate font-mono text-xs text-zinc-400 dark:text-zinc-500">{domain}</p>
      </div>
    </motion.a>
  )
}
