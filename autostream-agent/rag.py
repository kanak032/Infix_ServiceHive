import json
import os


def load_knowledge_base(path=None):
    """Load the knowledge base from a JSON file."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base.json")
    with open(path) as f:
        return json.load(f)


def retrieve(query: str) -> str:
    """
    Retrieve relevant sections from the knowledge base based on keyword matching.

    Args:
        query: The user's question or message.

    Returns:
        A formatted string containing the relevant knowledge base sections.
    """
    kb = load_knowledge_base()
    query = query.lower()
    results = []

    # Match pricing-related queries
    if any(w in query for w in ["price", "pricing", "plan", "cost", "basic", "pro", "enterprise", "month", "subscription", "pay", "fee", "tier"]):
        results.append("PRICING:\n" + json.dumps(kb["pricing"], indent=2))

    # Match policy-related queries
    if any(w in query for w in ["refund", "support", "policy", "policies", "cancel", "return", "help"]):
        results.append("POLICIES:\n" + json.dumps(kb["policies"], indent=2))

    # Match feature-related queries
    if any(w in query for w in ["feature", "edit", "video", "caption", "resolution", "4k", "720p", "export", "b-roll", "zoom", "language", "what can", "what does"]):
        results.append("GENERAL PLATFORM FEATURES:\n" + json.dumps(kb.get("general_features", []), indent=2))
        results.append("PRICING TIERS & LIMITS:\n" + json.dumps(kb["pricing"], indent=2))

    # Match FAQ-related queries (formats, limits)
    if any(w in query for w in ["format", "mp4", "mov", "size", "limit", "upload", "gb", "faq"]):
        results.append("FAQS:\n" + json.dumps(kb.get("faqs", {}), indent=2))

    # Deduplicate results
    seen = set()
    unique_results = []
    for r in results:
        if r not in seen:
            seen.add(r)
            unique_results.append(r)

    return "\n\n".join(unique_results) if unique_results else "No relevant information found in the knowledge base."
