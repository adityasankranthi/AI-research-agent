import { Coins } from "lucide-react"

export function CostBadge({ cost, calls }: { cost: number; calls: number }) {
  return (
    <div className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-3 py-1 font-mono text-xs text-zinc-600 dark:border-white/10 dark:bg-white/5 dark:text-zinc-300">
      <Coins className="size-3.5 text-amber-500" />
      <span>${cost.toFixed(4)}</span>
      <span className="text-zinc-300 dark:text-zinc-600">·</span>
      <span>
        {calls} call{calls === 1 ? "" : "s"}
      </span>
    </div>
  )
}
