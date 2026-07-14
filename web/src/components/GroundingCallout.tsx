import { ShieldAlert, ShieldCheck } from "lucide-react"

export function GroundingCallout({ unverifiedClaims }: { unverifiedClaims: string[] | null }) {
  if (!unverifiedClaims || unverifiedClaims.length === 0) {
    return (
      <div className="flex items-center gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300">
        <ShieldCheck className="size-4.5 shrink-0" />
        <span>
          <strong className="font-semibold">All claims verified</strong> — every citation in
          this report matched a source that was actually gathered.
        </span>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
      <div className="flex items-center gap-2.5">
        <ShieldAlert className="size-4.5 shrink-0" />
        <span>
          <strong className="font-semibold">
            {unverifiedClaims.length} claim{unverifiedClaims.length === 1 ? "" : "s"} could not be
            automatically verified
          </strong>{" "}
          against gathered sources.
        </span>
      </div>
      <ul className="mt-2 ml-7 list-disc space-y-1 text-amber-800/90 dark:text-amber-200/80">
        {unverifiedClaims.map((claim, i) => (
          <li key={i}>{claim}</li>
        ))}
      </ul>
    </div>
  )
}
