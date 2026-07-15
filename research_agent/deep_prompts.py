"""Prompts and schemas for the coverage-driven deep-research pipeline."""

PLAN_SYSTEM_PROMPT = """You are planning a rigorous research report. Decompose the
user's request into independently verifiable requirements. Preserve every explicit
comparison, date range, entity, metric, requested recommendation, and output constraint.
Each item must be narrow enough to research with targeted web searches. Call the tool;
do not write the report. Classify breadth as broad when the answer requires a general
method, comparison, synthesis, multiple perspectives, or several distinct subquestions;
otherwise classify it as focused."""

PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "create_research_plan",
        "description": "Create a coverage plan for a research report.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "breadth": {"type": "string", "enum": ["focused", "broad"]},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "question": {"type": "string"},
                            "section": {"type": "string"},
                            "evidence_requirements": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["id", "question", "section", "evidence_requirements"],
                    },
                },
            },
            "required": ["title", "breadth", "items"],
        },
    },
}

QUERY_SYSTEM_PROMPT = """Choose a small portfolio of non-overlapping web searches for a
research agent. Target the highest-priority plan items that lack independent evidence.
Prefer primary-source, quantitative, and countervailing queries over generic overviews.
When a supplied breadth gate is unmet, prioritize previously unseen organizations and
domains even if every plan item has minimal support. Each query must be self-contained
and tied to exactly one plan item."""

QUERY_TOOL = {
    "type": "function",
    "function": {
        "name": "choose_research_query",
        "description": "Choose the next coverage-driven web query.",
        "parameters": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "plan_item_id": {"type": "string"},
                            "expected_information": {"type": "string"},
                        },
                        "required": ["query", "plan_item_id", "expected_information"],
                    },
                }
            },
            "required": ["queries"],
        },
    },
}

EVIDENCE_SYSTEM_PROMPT = """Extract only evidence that directly helps answer a listed
plan item. Every item must be traceable to one provided source, use that source's exact
title and URL, and include a concise supporting excerpt. Do not infer facts absent from
the source text. Return an empty list for irrelevant sources."""

EVIDENCE_TOOL = {
    "type": "function",
    "function": {
        "name": "record_evidence",
        "description": "Record atomic, source-grounded evidence.",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {"type": "string"},
                            "source_title": {"type": "string"},
                            "source_url": {"type": "string"},
                            "excerpt": {"type": "string"},
                            "plan_item_id": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                        "required": [
                            "claim", "source_title", "source_url", "excerpt", "plan_item_id"
                        ],
                    },
                }
            },
            "required": ["items"],
        },
    },
}

REPORT_SYSTEM_PROMPT = """Write an analyst-grade research report that directly answers
the user's request. Follow the supplied plan, synthesize relationships across evidence,
distinguish sourced facts from your analysis, discuss uncertainty and limitations, and
use descriptive markdown headings. Cite every sourced factual claim inline using the
exact [Source Title](URL) supplied with its evidence. Never invent facts or citations.
Do not append a separate sources list; the caller does that deterministically."""

AUDIT_SYSTEM_PROMPT = """Audit retained evidence against the original request and plan.
Identify unsupported requirements, contradictions, weak single-source conclusions, and
missing quantitative context. Do not invent evidence. Return concise instructions that a
report writer can follow, including explicit limitations where retrieval did not succeed."""

AUDIT_TOOL = {
    "type": "function",
    "function": {
        "name": "audit_evidence",
        "description": "Audit evidence coverage before report generation.",
        "parameters": {
            "type": "object",
            "properties": {
                "unsupported_plan_item_ids": {"type": "array", "items": {"type": "string"}},
                "contradictions": {"type": "array", "items": {"type": "string"}},
                "writing_instructions": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "unsupported_plan_item_ids", "contradictions", "writing_instructions"
            ],
        },
    },
}

REVIEW_SYSTEM_PROMPT = """Review a draft research report against the original request,
coverage plan, and evidence audit. Require revision only for material omissions, weak
synthesis, instruction failures, or unsupported claims. Preserve valid inline citations."""

REVIEW_TOOL = {
    "type": "function",
    "function": {
        "name": "review_report",
        "description": "Decide whether a draft needs one final revision.",
        "parameters": {
            "type": "object",
            "properties": {
                "revision_needed": {"type": "boolean"},
                "instructions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["revision_needed", "instructions"],
        },
    },
}

REVISION_SYSTEM_PROMPT = """Revise the supplied report exactly once. Follow the review
instructions, preserve supported inline citations, never add a factual claim absent from
the supplied evidence, and improve coverage, synthesis, and organization. Output only the
complete revised markdown report without a sources appendix."""

CITATION_REPAIR_SYSTEM_PROMPT = """Repair citation placement in the supplied markdown
report without changing its substantive claims, organization, analysis, or conclusions.
Attach the provided exact [Source Title](URL) citation immediately after each factual
claim it supports. Every evidence-backed plan section must contain at least one inline
citation. Use only citations from the evidence inventory. Do not add new facts, remove
analysis, or append a bibliography. Output only the complete repaired report."""
