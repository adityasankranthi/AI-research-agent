/**
 * research_agent/grounding.py's `annotate_ungrounded` appends a
 * "### Unverified claims" section (bullet list) into the report body only when at
 * least one claim's citation didn't match a gathered source. This pulls that
 * section out so it can render as a distinct callout instead of blending into the
 * report's normal prose -- the project's whole differentiator is citation
 * accuracy, so it deserves to be visually first-class, not just another heading.
 */
export interface GroundingSplit {
  body: string
  unverifiedClaims: string[] | null
}

const SECTION_HEADING = "### Unverified claims"

export function splitGroundingSection(markdown: string): GroundingSplit {
  const start = markdown.indexOf(SECTION_HEADING)
  if (start === -1) {
    return { body: markdown, unverifiedClaims: null }
  }

  const afterHeading = start + SECTION_HEADING.length
  const nextHeadingIdx = markdown.indexOf("\n### ", afterHeading)
  const sectionEnd = nextHeadingIdx === -1 ? markdown.length : nextHeadingIdx
  const sectionText = markdown.slice(afterHeading, sectionEnd)

  const claims = sectionText
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2).trim())

  const body = (markdown.slice(0, start) + markdown.slice(sectionEnd)).trim()
  return { body, unverifiedClaims: claims }
}
