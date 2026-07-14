import { useState } from "react"
import { motion } from "framer-motion"
import { ArrowRight, KeyRound } from "lucide-react"
import { useSettings } from "@/context/SettingsContext"

const EXAMPLE_TOPICS = [
  "What is the Model Context Protocol (MCP)?",
  "What is Retrieval-Augmented Generation (RAG)?",
  "What is Kubernetes?",
  "What is the HTTP/3 protocol?",
]

export function TopicForm({ onSubmit }: { onSubmit: (topic: string) => void }) {
  const { settings } = useSettings()
  const [topic, setTopic] = useState("")

  const missingLlmKey = settings.llmApiKey.trim().length === 0
  const missingSearchKey = settings.searchBackend === "tavily" && settings.tavilyApiKey.trim().length === 0
  const canSubmit = topic.trim().length >= 3 && !missingLlmKey && !missingSearchKey

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (canSubmit) onSubmit(topic.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      <div className="glass focus-within:border-violet-300/70 focus-within:ring-4 focus-within:ring-violet-500/10 relative rounded-2xl transition-all dark:focus-within:border-violet-400/40">
        <textarea
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What do you want to research?"
          rows={3}
          className="w-full resize-none rounded-2xl bg-transparent px-5 py-4 text-base text-zinc-800 placeholder:text-zinc-400 focus:outline-none dark:text-zinc-100 dark:placeholder:text-zinc-500"
        />
        <motion.button
          type="submit"
          disabled={!canSubmit}
          whileHover={canSubmit ? { scale: 1.03 } : undefined}
          whileTap={canSubmit ? { scale: 0.97 } : undefined}
          className="absolute right-3 bottom-3 inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-violet-500/30 transition-shadow enabled:hover:shadow-lg enabled:hover:shadow-violet-500/40 disabled:cursor-not-allowed disabled:bg-none disabled:bg-zinc-200 disabled:text-zinc-400 disabled:shadow-none dark:disabled:bg-white/5 dark:disabled:text-zinc-600"
        >
          Research
          <ArrowRight className="size-4" />
        </motion.button>
      </div>

      <div className="flex flex-wrap gap-2">
        {EXAMPLE_TOPICS.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => setTopic(example)}
            className="glass-subtle rounded-full px-3 py-1.5 text-xs text-zinc-500 transition-colors hover:border-violet-300/70 hover:text-violet-600 dark:text-zinc-400 dark:hover:border-violet-400/40 dark:hover:text-violet-300"
          >
            {example}
          </button>
        ))}
      </div>

      {(missingLlmKey || missingSearchKey) && (
        <p className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400">
          <KeyRound className="size-3.5" />
          Add {missingLlmKey && missingSearchKey ? "a model API key and a Tavily key" : missingLlmKey ? "a model API key" : "a Tavily API key"} in
          Settings below to start researching.
        </p>
      )}
    </form>
  )
}
