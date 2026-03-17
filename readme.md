# Meme Generator Server

This project is the orchestration backend for an automated meme-to-video publishing pipeline. It uses FastAPI as the API layer, LangGraph as the workflow engine, MCP tools as the execution layer, and Redis-backed checkpointing to support a human-in-the-loop approval step before publishing.

## Objective

Build a backend service that can:

- fetch or generate meme content,
- use an LLM to create publishable metadata,
- generate a meme-based video,
- pause for human review,
- and then continue the flow to upload the final output to YouTube.

The core goal is not just meme generation, but building a reliable agentic workflow where automation and human control work together.

## Why This Project

Modern content pipelines are increasingly moving from single API calls to multi-step agent workflows. This project explores that shift in a practical way:

- how to orchestrate multiple tools safely,
- how to persist workflow state between steps,
- how to support interruption and resume,
- and how to expose the whole pipeline through a clean backend API.

Instead of a simple "generate once and return response" service, this backend models a real production-style pipeline with checkpoints, state passing, and approval gates.

## Need / Problem It Solves

Creating short-form content manually is repetitive:

- finding a meme or source asset,
- deciding the content style,
- writing a title and description,
- choosing keywords,
- generating a video version,
- and finally publishing it.

This server reduces that repeated effort by automating the pipeline while still letting a human review and modify important publishing details before upload.

## What The Server Does

The backend exposes API endpoints that trigger and resume a LangGraph workflow. Internally, it coordinates external MCP tools in sequence:

1. `download_random_meme`
2. `call_gemini_api`
3. `createVideo`
4. human approval via LangGraph `interrupt`
5. `upload_video_to_youtube`

The service also stores workflow progress in Redis so the graph can survive pauses and continue correctly after review.

## Tech Stack

- Python
- FastAPI
- LangGraph
- LangChain MCP Adapters
- MCP (Model Context Protocol) tool integration
- Redis checkpointer via `AsyncRedisSaver`
- Pydantic
- Uvicorn

## New Technologies Explored

This project was a hands-on exploration of several newer backend and agentic workflow ideas:

- **LangGraph** for defining stateful multi-step workflows instead of writing linear orchestration code manually.
- **Interrupt / resume execution** for human-in-the-loop systems.
- **MCP integration** to treat external capabilities as tools inside a graph.
- **Redis-based checkpointing** to persist graph state across requests.
- **Typed shared workflow state** using `TypedDict` and reducers.
- **LLM-assisted metadata generation** for titles, descriptions, keywords, and content style.

## Key Features

- API-first backend for triggering the content pipeline
- Human approval gate before final publishing
- Resume support after manual review
- Persistent workflow state using Redis
- CORS-enabled FastAPI service for frontend integration
- Modular tool-based orchestration through MCP

## System Design

### High-Level Components

- **Client / Frontend**
  Sends start and resume requests.

- **FastAPI Server**
  Receives requests and invokes the LangGraph workflow.

- **LangGraph Workflow**
  Controls execution order, state transitions, and interruption logic.

- **MCP Tool Server**
  Provides actual tools like meme download, LLM call, video creation, and YouTube upload.

- **Redis Checkpointer**
  Persists graph state so execution can resume safely after interruption.

### Flow Diagram

```text
User / Frontend
    |
    v
POST /start
    |
    v
FastAPI Backend
    |
    v
LangGraph StateGraph
    |
    +--> download_random_meme
    |
    +--> call_gemini_api
    |      |
    |      +--> generates audio_type, title, description, keywords
    |
    +--> createVideo
    |
    +--> interrupt for human review
    |      |
    |      +--> user edits title / description / keywords if needed
    |
    +--> POST /resume
    |
    +--> upload_video_to_youtube
    |
    v
Final Result Returned

State Persistence:
LangGraph <--> Redis Checkpointer

Tool Execution:
LangGraph <--> MCP Tool Server
```

## Workflow Logic

### `/start`

The client sends optional YouTube `access_token` and `refresh_token`.

The server:

- initializes the workflow state,
- starts the graph,
- executes the automation steps,
- and returns an interrupt payload when human review is required.

### Human Review Step

Before uploading, the workflow pauses and exposes:

- `audio_type`
- `title`
- `description`
- `keywords`

The frontend or operator can review and modify these values.

### `/resume`

The updated values are sent back to the backend, which resumes the interrupted graph and completes the upload step.

## Current API Surface

### `GET /health`

Simple health-check endpoint.

### `POST /start`

Starts the meme generation and publishing workflow.

Example request body:

```json
{
  "access_token": "optional-token",
  "refresh_token": "optional-refresh-token"
}
```

### `POST /resume`

Resumes the workflow after human review.

Expected body shape:

```json
{
  "interrupt": {
    "resume": "interrupt-token-from-start"
  },
  "updated": {
    "title": "updated title",
    "description": "updated description",
    "keywords": ["meme", "funny", "shorts"],
    "audio_type": "some-audio-type"
  }
}
```

## Project Structure

```text
.
├── app.py              # Main FastAPI app and LangGraph orchestration
├── models.py           # Pydantic models
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
└── readme.md           # Project documentation
```

## Environment Variables

The current code expects:

```env
MCP_URL=
REDIS_URL=
```

Note: `.env.example` currently includes `MCP_URL` but does not yet include `REDIS_URL`, even though the app uses it at runtime.

## Local Setup

### Prerequisites

- Python 3.12+
- Redis instance
- Running MCP server exposing the `meme_pipeline` tools

### Installation

```bash
git clone <your-repo-url>
cd meme_generator_server
pip install -r requirements.txt
```

### Configure Environment

Create a `.env` file with values like:

```env
MCP_URL=http://localhost:8000/mcp/
REDIS_URL=redis://localhost:6379
```

### Run The Server

```bash
python app.py
```

The API runs on:

```text
http://0.0.0.0:8001
```

## Challenges Faced

This kind of project introduces challenges beyond typical CRUD backend work:

- **State management across workflow steps**
  Each tool contributes partial state that must be merged carefully.

- **Interrupt and resume handling**
  Human review breaks linear execution, so the system must persist and restore context correctly.

- **Tool output normalization**
  External tools may return strings or JSON-like objects, so the server must normalize responses before storing them.

- **Cross-service coordination**
  The backend depends on an MCP server, Redis, LLM-backed tooling, and upload tooling working together reliably.

- **Balancing automation with control**
  Full automation is convenient, but publishing workflows usually still need a human checkpoint.

## Design Decisions

- **FastAPI** was chosen for a lightweight and frontend-friendly API layer.
- **LangGraph** was used because the workflow is stateful, multi-step, and interruptible.
- **Redis checkpointer** was chosen to persist workflow state across pauses and resumes.
- **MCP tools** keep the actual content-generation capabilities modular and swappable.
- **Human approval before upload** reduces the risk of publishing incorrect or low-quality metadata.

## What Makes This Project Interesting

This is more than a meme backend. It is a small but practical example of an agentic system with:

- workflow orchestration,
- state persistence,
- tool composition,
- LLM enrichment,
- and human supervision.

That makes it useful as both a portfolio project and an architecture experiment for more advanced AI-assisted automation systems.

## Possible Improvements

- generate unique thread IDs instead of using a shared static thread,
- improve error handling and retry logic,
- add structured logging and observability,
- include automated tests for start/resume flow,
- validate resume payloads with stricter models,

## Learning Outcomes

This project demonstrates practical understanding of:

- backend API design with FastAPI,
- graph-based orchestration using LangGraph,
- Redis-backed persistence,
- interruptible agent workflows,
- integrating LLM-driven steps into backend systems,
- and designing systems where humans remain part of the final decision loop.

## Conclusion

The Meme Generator Server is a workflow-oriented backend for automated content generation and publishing. Its strongest aspect is the combination of AI automation with human review, making it a useful prototype for real-world creator tools and agentic media pipelines.
