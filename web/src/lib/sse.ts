import type { ResearchEvent } from "./types"

/**
 * Streams Server-Sent Events from a POST endpoint.
 *
 * `EventSource` can't send a POST body, and the topic/API keys must never travel
 * in a query string (query strings land in server access logs and browser
 * history). So this parses `text/event-stream` frames by hand off a plain
 * `fetch()` response body instead.
 */
export async function* streamResearch(
  url: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<ResearchEvent> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok || !response.body) {
    const detail = await response.text().catch(() => "")
    throw new Error(detail || `Request failed with status ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary: number
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawFrame = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      const parsed = parseFrame(rawFrame)
      if (parsed) yield parsed
    }
  }
}

function parseFrame(rawFrame: string): ResearchEvent | null {
  let event = ""
  let data = ""
  for (const line of rawFrame.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice("event: ".length)
    else if (line.startsWith("data: ")) data = line.slice("data: ".length)
  }
  if (!event || !data) return null
  return { event, data: JSON.parse(data) } as ResearchEvent
}
