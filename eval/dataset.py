from dataclasses import dataclass


@dataclass
class EvalCase:
    topic: str
    key_facts: list[str]


# Stable, well-documented technical topics -- chosen deliberately over anything
# current-events-shaped so the "correct" facts don't drift between eval runs, which
# would make a score change between runs ambiguous (agent regression vs. the world
# just changing).
DATASET: list[EvalCase] = [
    EvalCase(
        topic="What is the Model Context Protocol (MCP)?",
        key_facts=[
            "MCP was created or introduced by Anthropic",
            "MCP is an open protocol or standard",
            "MCP connects AI applications or models to external data sources or tools",
        ],
    ),
    EvalCase(
        topic="What is Retrieval-Augmented Generation (RAG)?",
        key_facts=[
            "RAG combines information retrieval with text generation",
            "RAG retrieves external documents or knowledge to ground the model's response",
            "RAG helps reduce hallucination compared to generation from the model alone",
        ],
    ),
    EvalCase(
        topic="What is the Transformer architecture in machine learning?",
        key_facts=[
            "Transformers were introduced in the 'Attention Is All You Need' paper",
            "Transformers use a self-attention mechanism",
            "Transformers do not rely on recurrence, unlike RNNs",
        ],
    ),
    EvalCase(
        topic="What is Kubernetes?",
        key_facts=[
            "Kubernetes is an open-source container orchestration platform",
            "Kubernetes was originally developed by Google",
            "Kubernetes automates deployment, scaling, and management of containerized applications",
        ],
    ),
    EvalCase(
        topic="What is the HTTP/3 protocol?",
        key_facts=[
            "HTTP/3 is built on the QUIC transport protocol",
            "HTTP/3 uses UDP instead of TCP",
            "HTTP/3 reduces connection setup latency compared to earlier HTTP versions",
        ],
    ),
    EvalCase(
        topic="What is Rust's ownership model in programming?",
        key_facts=[
            "In Rust, each value has a single owner",
            "Rust achieves memory safety without a garbage collector",
            "Rust's borrowing allows references to a value without taking ownership of it",
        ],
    ),
]
