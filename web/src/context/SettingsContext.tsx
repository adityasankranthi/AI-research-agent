import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { loadSettings, saveSettings } from "@/lib/storage"
import type { ResearchSettings } from "@/lib/types"

interface SettingsContextValue {
  settings: ResearchSettings
  updateSettings: (patch: Partial<ResearchSettings>) => void
}

const SettingsContext = createContext<SettingsContextValue | null>(null)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<ResearchSettings>(loadSettings)

  useEffect(() => {
    saveSettings(settings)
  }, [settings])

  const updateSettings = (patch: Partial<ResearchSettings>) =>
    setSettings((prev) => ({ ...prev, ...patch }))

  return (
    <SettingsContext.Provider value={{ settings, updateSettings }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error("useSettings must be used within a SettingsProvider")
  return ctx
}
