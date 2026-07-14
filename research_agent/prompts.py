from datetime import datetime


def current_date() -> str:
    return datetime.now().strftime("%B %d, %Y")


QUERY_WRITER_SYSTEM_PROMPT = """Your goal is to generate a targeted web search query.

Current date: {current_date}
Please ensure your query accounts for the most current information available as of this date.

Research topic:
{research_topic}

Call the generate_search_query tool with a specific, well-targeted search query and a
brief rationale for why it addresses the topic."""

SEARCH_QUERY_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_search_query",
        "description": "Propose a web search query for the current research topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The actual search query string."},
                "rationale": {
                    "type": "string",
                    "description": "Brief explanation of why this query is relevant.",
                },
            },
            "required": ["query", "rationale"],
        },
    },
}


SUMMARIZER_SYSTEM_PROMPT = """Generate a high-quality summary of the provided context, \
addressing the user's research topic.

When creating a NEW summary:
1. Highlight the most relevant information related to the topic from the search results.
2. Ensure a coherent flow of information.
3. Whenever you state a fact drawn from a source, cite it inline immediately after the \
claim using markdown link syntax: [Source Title](URL), using the exact Title and URL \
given in that source's block below. Do not invent a citation for a claim that isn't \
drawn from the given sources.

When EXTENDING an existing summary:
1. Read the existing summary and new search results carefully.
2. For each piece of new information: integrate it into an existing paragraph if it's \
related, add a new paragraph if it's new but relevant, or skip it if it isn't relevant.
3. Verify that your final output differs from the input summary.
4. Preserve existing inline [Source Title](URL) citations, and cite new claims the same way.

Start directly with the updated summary, without preamble or titles. Do not use XML \
tags in the output."""


def summarizer_user_message(topic: str, existing_summary: str, new_context: str) -> str:
    if existing_summary:
        return (
            f"<Existing Summary>\n{existing_summary}\n</Existing Summary>\n\n"
            f"<New Context>\n{new_context}\n</New Context>\n\n"
            f"Update the Existing Summary with the New Context on this topic: {topic}"
        )
    return (
        f"<Context>\n{new_context}\n</Context>\n\n"
        f"Create a Summary using the Context on this topic: {topic}"
    )


REFLECTION_SYSTEM_PROMPT = """You are an expert research assistant analyzing a summary \
about {research_topic}.

First, judge whether the summary already sufficiently answers the research topic as a \
person asking this question would reasonably expect -- not whether every conceivable \
tangent, mechanism, or edge case has been explored. Most direct factual questions are \
fully answered in one or two loops; do not manufacture a gap just to have one. If it \
does, set research_complete to true and you're done -- follow_up_query and \
knowledge_gap won't be used, but still fill them in briefly.

Otherwise, if there's a genuine, material gap in addressing the topic itself (not a \
tangential technical detail or emerging trend unrelated to what was actually asked):
1. Identify that knowledge gap.
2. Generate a follow-up query that would help close it.
3. Set research_complete to false.

Ensure the follow-up query is self-contained and includes enough context to be used \
directly as a web search query.

Call the propose_followup_query tool with the knowledge gap you found and a follow-up \
query to address it."""

REFLECTION_TOOL = {
    "type": "function",
    "function": {
        "name": "propose_followup_query",
        "description": (
            "Propose a follow-up web search query that addresses a gap in the "
            "current research summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "knowledge_gap": {
                    "type": "string",
                    "description": "What information is missing or needs clarification.",
                },
                "follow_up_query": {
                    "type": "string",
                    "description": "A specific, self-contained search query to address the gap.",
                },
                "research_complete": {
                    "type": "boolean",
                    "description": (
                        "True if the current summary already sufficiently addresses the "
                        "research topic and further search loops are unlikely to add "
                        "meaningful new information. Default to false if unsure."
                    ),
                },
            },
            "required": ["knowledge_gap", "follow_up_query", "research_complete"],
        },
    },
}


def reflection_user_message(running_summary: str) -> str:
    return (
        f"Reflect on our existing knowledge:\n===\n{running_summary}\n===\n"
        "Identify a knowledge gap and propose a follow-up web search query."
    )
