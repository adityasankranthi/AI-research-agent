/**
 * Fixed, full-viewport gradient-mesh blobs behind every screen. This is what a
 * glassmorphic UI is actually frosting against -- without something behind them,
 * the blurred/translucent panels elsewhere just look like grey boxes.
 */
export function AmbientBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-zinc-50 dark:bg-[#08090d]"
    >
      <div className="animate-drift-a absolute top-[-10%] left-[-10%] size-[36rem] rounded-full bg-violet-400/40 blur-3xl dark:bg-violet-600/25" />
      <div className="animate-drift-b absolute top-[10%] right-[-15%] size-[40rem] rounded-full bg-cyan-300/30 blur-3xl dark:bg-cyan-500/15" />
      <div className="animate-drift-c absolute bottom-[-15%] left-[20%] size-[34rem] rounded-full bg-fuchsia-300/25 blur-3xl dark:bg-fuchsia-600/15" />
      <div className="absolute inset-0 bg-white/40 dark:bg-black/30" />
    </div>
  )
}
