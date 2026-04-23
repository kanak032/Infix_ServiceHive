"""
AutoStream Conversational AI Agent
===================================
A LangGraph-based conversational agent for AutoStream — an AI-powered 
automated video editing SaaS platform for content creators.

The agent handles:
- Intent detection (greeting / inquiry / high_intent)
- RAG-based Q&A using a local JSON knowledge base
- Lead capture via multi-turn conversation and tool execution
"""

import os
import re
from typing import TypedDict, Optional, List, Annotated
import operator

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END

from rag import retrieve
from tools import mock_lead_capture

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

import itertools

_llm_cycle = None


def get_llm():
    """Lazily initialize the LLMs and rotate through them (API Key Rotation) to bypass free-tier rate limits."""
    global _llm_cycle
    
    if _llm_cycle is None:
        # Check for multiple keys (comma-separated) or a single key
        keys_env = os.getenv("GOOGLE_API_KEYS")
        single_key = os.getenv("GOOGLE_API_KEY")
        
        keys = []
        if keys_env:
            keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        elif single_key:
            keys = [k.strip() for k in single_key.split(",") if k.strip()]
            
        if not keys:
            raise ValueError(
                "No API keys found. Please set GOOGLE_API_KEYS (comma-separated list of keys) "
                "or GOOGLE_API_KEY in your .env file.\n"
                "Get your keys at: https://aistudio.google.com/app/apikey"
            )
            
        # Create an LLM instance for each key
        llms = [
            ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=key,
                temperature=0.3,
                max_retries=1,
                timeout=15,
            )
            for key in keys
        ]
        
        # Create an infinite cycle iterator
        _llm_cycle = itertools.cycle(llms)
        
    # Return the next LLM instance in the cycle
    return next(_llm_cycle)

# ---------------------------------------------------------------------------
# System & Classification Prompts
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are AutoStream's friendly sales assistant. AutoStream provides AI-powered automated \
video editing tools for content creators.

Your goals:
1. Answer product/pricing/policy questions using ONLY the provided knowledge base context. Do not make up information.
2. If asked what AutoStream is, explain that it provides AI-powered automated video editing tools for content creators.
3. Detect when a user is ready to sign up (high intent).
4. Collect name, email, and creator platform (e.g., YouTube, Instagram) before triggering lead capture.
5. Never ask for all fields at once — collect them one at a time, naturally.

Always be concise, friendly, and helpful."""

INTENT_PROMPT_TEMPLATE = """Classify the following user message into exactly one of these intents:
- "greeting": casual hello, goodbye, thanks, or off-topic message
- "inquiry": asking about product features, pricing, or policies
- "high_intent": expressing desire to sign up, try, buy, get started, subscribe, or purchase

User message: {message}

Respond with ONLY one word: greeting, inquiry, or high_intent"""


# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: List[dict]                # Full conversation history
    intent: Optional[str]               # "greeting" | "inquiry" | "high_intent"
    retrieved_context: Optional[str]    # RAG context for the current turn
    lead_name: Optional[str]
    lead_email: Optional[str]
    lead_platform: Optional[str]
    lead_captured: bool
    response: Optional[str]             # Final response for the current turn


# ---------------------------------------------------------------------------
# Node Functions
# ---------------------------------------------------------------------------

def detect_intent(state: AgentState) -> dict:
    """
    Node 1: Classify the latest user message into one of three intents.
    Uses an LLM call with a strict classification prompt.
    """
    messages = state["messages"]
    latest_message = messages[-1]["content"] if messages else ""

    # If lead capture is already in progress (some fields collected but not all),
    # keep the intent as high_intent to continue the flow
    if (
        not state.get("lead_captured", False)
        and (state.get("lead_name") or state.get("lead_email") or state.get("lead_platform"))
    ):
        # Check if user is still providing lead info or switching topic
        classification_response = get_llm().invoke([
            HumanMessage(content=INTENT_PROMPT_TEMPLATE.format(message=latest_message))
        ])
        raw = classification_response.content.strip().lower()
        # If the user is providing info (not explicitly switching topics), stay in high_intent
        if raw != "inquiry":
            return {"intent": "high_intent"}
        else:
            return {"intent": "inquiry"}

    # Normal classification
    classification_response = get_llm().invoke([
        HumanMessage(content=INTENT_PROMPT_TEMPLATE.format(message=latest_message))
    ])

    raw = classification_response.content.strip().lower()

    # Parse out the intent — handle edge cases where LLM might add extra text
    if "high_intent" in raw:
        intent = "high_intent"
    elif "inquiry" in raw:
        intent = "inquiry"
    else:
        intent = "greeting"

    return {"intent": intent}


def retrieve_knowledge(state: AgentState) -> dict:
    """
    Node 2: Retrieve relevant knowledge from the knowledge base.
    Called when the intent is 'inquiry'.
    """
    messages = state["messages"]
    latest_message = messages[-1]["content"] if messages else ""

    context = retrieve(latest_message)
    return {"retrieved_context": context}


def generate_response(state: AgentState) -> dict:
    """
    Node 3: Generate a natural response using LLM with conversation history
    and any retrieved context.
    """
    messages = state["messages"]
    intent = state.get("intent", "greeting")
    retrieved_context = state.get("retrieved_context", "")

    # Build the LLM message list
    llm_messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Add conversation history (last 10 messages for context window management)
    for msg in messages[-10:]:
        if msg["role"] == "user":
            llm_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            llm_messages.append(AIMessage(content=msg["content"]))

    # If we have retrieved context, inject it before the last user message
    if retrieved_context and intent == "inquiry":
        context_msg = f"\n\n[Knowledge Base Context]\n{retrieved_context}\n\nPlease answer the user's question using ONLY the information provided above. Do not make up any information."
        # Insert context as a system-level instruction
        llm_messages.insert(-1, SystemMessage(content=context_msg))

    # If collecting lead info and some fields are still missing
    if intent == "high_intent":
        missing = []
        if not state.get("lead_name"):
            missing.append("name")
        if not state.get("lead_email"):
            missing.append("email")
        if not state.get("lead_platform"):
            missing.append("creator platform (e.g., YouTube, Instagram, TikTok)")

        if missing:
            next_field = missing[0]
            lead_instruction = (
                f"The user is interested in signing up. You still need to collect their {next_field}. "
                f"Ask for it naturally and conversationally. Do NOT ask for multiple fields at once."
            )
            llm_messages.append(SystemMessage(content=lead_instruction))

    response = get_llm().invoke(llm_messages)
    return {"response": response.content}


def collect_lead(state: AgentState) -> dict:
    """
    Node 4: Process lead information from the user's message.
    Extracts name, email, and platform from the conversation.
    """
    messages = state["messages"]
    latest_message = messages[-1]["content"] if messages else ""
    updates = {}

    # Try to extract email using regex
    if not state.get("lead_email"):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, latest_message)
        if email_match:
            updates["lead_email"] = email_match.group()

    # Try to extract platform
    if not state.get("lead_platform"):
        platforms = ["youtube", "instagram", "tiktok", "twitch", "twitter", "x", "facebook", "linkedin", "snapchat", "vimeo"]
        for platform in platforms:
            if platform in latest_message.lower():
                updates["lead_platform"] = platform.capitalize()
                break

    # Use LLM to extract name or platform if not found by rules
    if not state.get("lead_name") or (not state.get("lead_platform") and "lead_platform" not in updates):
        extraction_prompt = f"""From the following user message, extract any of these fields if present:
- name: the user's personal name (first name or full name)
- platform: a content creation platform (YouTube, Instagram, TikTok, etc.)

User message: "{latest_message}"

Conversation context (previous messages):
"""
        for msg in messages[-5:]:
            extraction_prompt += f"  {msg['role']}: {msg['content']}\n"

        extraction_prompt += """
Respond in this exact format (use "none" if not found):
name: <extracted name or none>
platform: <extracted platform or none>"""

        extraction_response = get_llm().invoke([HumanMessage(content=extraction_prompt)])
        extracted = extraction_response.content.strip().lower()

        for line in extracted.split("\n"):
            line = line.strip()
            if line.startswith("name:") and not state.get("lead_name"):
                val = line.split(":", 1)[1].strip()
                if val and val != "none":
                    updates["lead_name"] = val.title()
            if line.startswith("platform:") and not state.get("lead_platform") and "lead_platform" not in updates:
                val = line.split(":", 1)[1].strip()
                if val and val != "none":
                    updates["lead_platform"] = val.title()

    return updates


def capture_lead(state: AgentState) -> dict:
    """
    Node 5: Trigger the lead capture tool when all fields are collected.
    """
    name = state["lead_name"]
    email = state["lead_email"]
    platform = state["lead_platform"]

    result = mock_lead_capture(name, email, platform)

    confirmation = (
        f"🎉 Awesome, {name}! You're all set! I've registered your interest in AutoStream.\n\n"
        f"📋 Here's what I have:\n"
        f"   • Name: {name}\n"
        f"   • Email: {email}\n"
        f"   • Platform: {platform}\n\n"
        f"Our team will reach out to you shortly at {email} to help you get started. "
        f"Welcome to AutoStream! 🚀"
    )

    return {
        "lead_captured": True,
        "response": confirmation,
    }


# ---------------------------------------------------------------------------
# Routing Functions
# ---------------------------------------------------------------------------

def route_by_intent(state: AgentState) -> str:
    """Route from detect_intent to the appropriate next node."""
    intent = state.get("intent", "greeting")
    if intent == "high_intent":
        return "collect_lead"
    elif intent == "inquiry":
        return "retrieve_knowledge"
    else:
        return "generate_response"


def route_after_collect(state: AgentState) -> str:
    """Route after collect_lead — check if all fields are present."""
    if state.get("lead_name") and state.get("lead_email") and state.get("lead_platform"):
        return "capture_lead"
    else:
        return "generate_response"


# ---------------------------------------------------------------------------
# Build the LangGraph
# ---------------------------------------------------------------------------

def build_graph():
    """Construct and compile the LangGraph agent workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("detect_intent", detect_intent)
    workflow.add_node("retrieve_knowledge", retrieve_knowledge)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("collect_lead", collect_lead)
    workflow.add_node("capture_lead", capture_lead)

    # Define edges
    workflow.set_entry_point("detect_intent")

    # Conditional routing from detect_intent
    workflow.add_conditional_edges(
        "detect_intent",
        route_by_intent,
        {
            "collect_lead": "collect_lead",
            "retrieve_knowledge": "retrieve_knowledge",
            "generate_response": "generate_response",
        },
    )

    # retrieve_knowledge → generate_response
    workflow.add_edge("retrieve_knowledge", "generate_response")

    # generate_response → END
    workflow.add_edge("generate_response", END)

    # Conditional routing after collect_lead
    workflow.add_conditional_edges(
        "collect_lead",
        route_after_collect,
        {
            "capture_lead": "capture_lead",
            "generate_response": "generate_response",
        },
    )

    # capture_lead → END
    workflow.add_edge("capture_lead", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Conversation Loop
# ---------------------------------------------------------------------------

def run_agent():
    """Run the interactive conversation loop."""
    graph = build_graph()

    # Initialize persistent state across turns
    state = {
        "messages": [],
        "intent": None,
        "retrieved_context": None,
        "lead_name": None,
        "lead_email": None,
        "lead_platform": None,
        "lead_captured": False,
        "response": None,
    }

    print("=" * 60)
    print("  🎬 Welcome to AutoStream AI Assistant!")
    print("  AI-powered video editing for content creators")
    print("=" * 60)
    print("  Type 'quit' or 'exit' to end the conversation.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! Thanks for chatting with AutoStream. 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "bye", "q"]:
            print("\nAssistant: Goodbye! Thanks for your interest in AutoStream. Have a great day! 👋")
            break

        # Add user message to conversation history
        state["messages"].append({"role": "user", "content": user_input})

        # Clear per-turn fields
        state["retrieved_context"] = None
        state["response"] = None

        # Invoke the graph
        result = graph.invoke(state)

        # Update persistent state with graph output
        state["intent"] = result.get("intent", state["intent"])
        state["lead_name"] = result.get("lead_name", state.get("lead_name"))
        state["lead_email"] = result.get("lead_email", state.get("lead_email"))
        state["lead_platform"] = result.get("lead_platform", state.get("lead_platform"))
        state["lead_captured"] = result.get("lead_captured", state.get("lead_captured", False))
        state["retrieved_context"] = result.get("retrieved_context", state.get("retrieved_context"))

        # Get and display response
        response = result.get("response", "I'm sorry, I didn't understand that. Could you rephrase?")
        state["messages"].append({"role": "assistant", "content": response})

        print(f"\nAssistant: {response}\n")

        # If lead was captured, optionally reset for a new lead
        if state["lead_captured"]:
            print("-" * 40)
            print("  Lead capture complete! You can continue chatting or type 'quit' to exit.")
            print("-" * 40 + "\n")
            # Reset lead fields for potential new conversation
            state["lead_name"] = None
            state["lead_email"] = None
            state["lead_platform"] = None
            state["lead_captured"] = False


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_agent()
