# AutoStream AI Sales Agent 🎬

A **Conversational AI Agent** built for **AutoStream** — a fictional SaaS company providing AI-powered automated video editing tools for content creators.

The agent handles **intent detection**, **RAG-based Q&A**, and **lead capture** via tool execution, powered by **LangGraph** and **Google Gemini 2.5 Flash**.

---

## Features

- 🧠 **Intent Detection** — Classifies user messages into `greeting`, `inquiry`, or `high_intent` using LLM-based classification
- 📚 **RAG-based Q&A** — Retrieves relevant product information from a local JSON knowledge base to answer pricing, feature, and policy questions
- 📋 **Lead Capture** — Multi-turn conversational flow to collect name, email, and creator platform before triggering lead capture
- 💬 **Conversation Memory** — Maintains full conversation history across turns for contextual responses
- 🔀 **LangGraph Workflow** — Stateful graph-based agent with conditional routing

---

## Architecture

```
┌──────────┐
│  START    │
└────┬─────┘
     │
┌────▼──────────┐
│ detect_intent  │
└────┬──────────┘
     │
     ├── greeting ──────────► generate_response ──► END
     │
     ├── inquiry ───► retrieve_knowledge ──► generate_response ──► END
     │
     └── high_intent ──► collect_lead
                              │
                    ┌─────────┴──────────┐
                    │                    │
              (all fields?)      (fields missing?)
                    │                    │
              capture_lead      generate_response
                    │                    │
                   END                  END
```

### Nodes

| Node | Purpose |
|------|---------|
| `detect_intent` | Classifies user message into one of 3 intents using LLM |
| `retrieve_knowledge` | Fetches relevant info from JSON knowledge base via keyword matching |
| `generate_response` | Generates natural response using LLM + conversation history + RAG context |
| `collect_lead` | Extracts lead fields (name, email, platform) from user messages |
| `capture_lead` | Calls `mock_lead_capture()` tool and sends confirmation |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.9+ |
| Framework | LangGraph |
| LLM | Google Gemini 2.5 Flash |
| RAG | Local JSON knowledge base |
| Memory | LangGraph state (conversation history) |

---

## Project Structure

```
autostream-agent/
├── agent.py                  # Main agent logic (LangGraph graph)
├── rag.py                    # RAG pipeline (load KB + retrieval)
├── tools.py                  # mock_lead_capture tool
├── knowledge_base.json       # Product knowledge base
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── README.md                 # This file
```

---

## How to Run

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd autostream-agent
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Your API Key

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:

```
GOOGLE_API_KEY=your_actual_api_key_here
```

> 🔑 Get your free API key at: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

### 5. Run the Agent

```bash
python agent.py
```

---

## Usage Examples

### Greeting
```
You: Hi there!
Assistant: Hey! 👋 Welcome to AutoStream! I'm here to help you with any 
questions about our AI-powered video editing tools. What can I help you with?
```

### Product Inquiry (RAG)
```
You: What are your pricing plans?
Assistant: We have two plans:
  • Basic — $29/month: 10 videos/month, 720p export, basic editing
  • Pro — $79/month: Unlimited videos, 4K resolution, AI captions, 24/7 support
```

### Lead Capture (High Intent)
```
You: I'd like to sign up for the Pro plan!
Assistant: That's great! I'd love to get you started. What's your name?

You: John Smith
Assistant: Nice to meet you, John! What's your email address?

You: john@example.com
Assistant: Perfect! And which platform do you primarily create content for?

You: YouTube
Assistant: 🎉 Awesome, John Smith! You're all set! I've registered your interest...
```

---

## Knowledge Base

The agent uses `knowledge_base.json` as its source of truth for:

- **Pricing**: Basic ($29/mo) and Pro ($79/mo) plan details
- **Features**: Video editing capabilities per plan tier
- **Policies**: Refund policy and support availability

> ⚠️ The agent will **never fabricate** pricing or policy information — it only responds with what's in the knowledge base.

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google AI Studio API key for Gemini | ✅ Yes |

---

## Architecture Explanation

This agent is built using **LangGraph** because it provides explicit control over the conversational state and routing logic. Unlike standard chain-based approaches, LangGraph allows for cycles and persistent memory across conversational turns, which is essential for multi-turn lead capture. 

**State Management:**
The state is defined using a `TypedDict` (`AgentState`), which tracks the full `messages` history, the current `intent`, the retrieved RAG context, and the lead fields (`lead_name`, `lead_email`, `lead_platform`, `lead_captured`). As the user converses, the state is passed sequentially through nodes. If a user is missing lead fields, the graph loops back to the user via the `generate_response` node, preserving the collected fields in the state until the tool is ready to be executed.

---

## WhatsApp Deployment (Webhook Integration)

**How I would integrate this agent with WhatsApp:**
To deploy this agent on WhatsApp, I would use the **WhatsApp Cloud API** and set up a backend server (e.g., using FastAPI or Flask) to handle Webhooks.

1. **Webhook Endpoint:** Create a `POST /webhook` endpoint on the server to receive incoming messages from WhatsApp.
2. **Session Management:** Since WhatsApp messages are stateless HTTP requests, I would use a database (like Redis or PostgreSQL) to store the LangGraph `AgentState`, keyed by the user's WhatsApp phone number.
3. **Execution Flow:**
   - Receive message payload from WhatsApp Webhook.
   - Extract the sender's phone number and message text.
   - Load the user's previous LangGraph state from the database.
   - Append the new message and invoke the compiled LangGraph agent.
   - Save the updated state back to the database.
4. **Sending Responses:** Extract the `response` string from the new state and use the WhatsApp Cloud API (`POST /v1/messages`) to send the message back to the user's phone.
5. **Security:** Implement Webhook verification (using the `hub.challenge` token) and validate the `X-Hub-Signature` to ensure payloads genuinely come from Meta.

---

## License

This project was built as an assignment for the Machine Learning Intern position at ServiceHive / Inflx.
