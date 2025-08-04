# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from langgraph.graph import StateGraph, END
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langchain_mcp_adapters import ToolNode
# from langchain_core.runnables import RunnableLambda
# import asyncio

# app = FastAPI()

# # Enable CORS for frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Global variable to store the compiled graph
# graph = None

# # ----------- TOOL WRAPPER LOGIC ------------
# def make_tool_node(tool):
#     async def wrapped_tool(state):
#         input_data = state.get("data", {})
#         response = await tool.ainvoke(input_data)
#         state[tool.name] = response
#         state["messages"].append({"tool": tool.name, "output": response})

#         # Pass structured outputs if from Gemini
#         if tool.name == "call_gemini_api" and response.get("status"):
#             for key in ["style", "title", "description", "keywords"]:
#                 if key in response:
#                     state["data"][key] = response[key]
#         return state
#     return RunnableLambda(wrapped_tool)

# # ----------- LangGraph Builder ------------
# # def build_graph(tools):
# #     builder = StateGraph(dict)

# #     builder.add_node("download_random_meme", make_tool_node(tools["download_random_meme"]))
# #     builder.add_node("call_gemini_api", make_tool_node(tools["call_gemini_api"]))
# #     builder.add_node("createVideo", make_tool_node(tools["createVideo"]))
# #     builder.add_node("upload_video_to_youtube", make_tool_node(tools["upload_video_to_youtube"]))

# #     # Flow: each state modifies context and passes forward
# #     builder.set_entry_point("download_random_meme")
# #     builder.add_edge("download_random_meme", "call_gemini_api")
# #     builder.add_edge("call_gemini_api", "createVideo")
# #     builder.add_edge("createVideo", "upload_video_to_youtube")
# #     builder.add_edge("upload_video_to_youtube", END)

# #     return builder.compile()

# def build_graph(tools):
#     builder = StateGraph(dict)

#     builder.add_node("download_random_meme", make_tool_node(tools["download_random_meme"]))
#     builder.add_node("call_gemini_api", make_tool_node(tools["call_gemini_api"]))
#     builder.add_node("createVideo", make_tool_node(tools["createVideo"]))

#     # Node that just waits for human input
#     async def wait_for_human(state):
#         state["messages"].append({"tool": "wait_for_human", "output": "Awaiting human input for title/desc/keywords."})
#         return state
#     builder.add_node("wait_for_human", RunnableLambda(wait_for_human))

#     builder.add_node("upload_video_to_youtube", make_tool_node(tools["upload_video_to_youtube"]))

#     builder.set_entry_point("download_random_meme")
#     builder.add_edge("download_random_meme", "call_gemini_api")
#     builder.add_edge("call_gemini_api", "createVideo")
#     builder.add_edge("createVideo", "wait_for_human")
#     builder.add_edge("wait_for_human", "upload_video_to_youtube")
#     builder.add_edge("upload_video_to_youtube", END)

#     return builder.compile()

# # ----------- LangGraph Initialization -----------
# @app.on_event("startup")
# async def startup_event():
#     global graph
#     client = MultiServerMCPClient(
#         {
#             "meme_pipeline": {
#                 "transport": "streamable_http",
#                 "url": "http://localhost:8000/mcp/"
#             },
#         }
#     )
#     tools = await client.get_tools(namespace="meme_pipeline")
#     graph = build_graph(tools)

# # ----------- Trigger Graph from API -----------
# @app.post("/run-pipeline")
# async def run_pipeline():
#     global graph
#     if graph is None:
#         return {"error": "LangGraph not initialized."}
#     initial_state = {
#         "messages": [],
#         "data": {}  # Starting state
#     }
#     result = await graph.ainvoke(initial_state)
#     return result










# import uuid, json
# from contextlib import asynccontextmanager

# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware

# from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import InMemorySaver
# from langgraph.types import interrupt, Command
# from langchain_mcp_adapters.client import MultiServerMCPClient

# from typing import TypedDict


# MCP_URL     = "http://127.0.0.1:8000/mcp/"
# SERVER_NAME = "meme_pipeline"

# graph = None
# THREAD_ID = "meme-pipeline-thread"

# class MemeState(TypedDict, total=False):
#     data: dict
#     messages: list
#     download_random_meme: dict
#     call_gemini_api: dict
#     createVideo: dict
#     upload_video_to_youtube: dict

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     global graph
#     client     = MultiServerMCPClient({SERVER_NAME: {"transport":"streamable_http","url":MCP_URL}})
#     tools_list = await client.get_tools(server_name=SERVER_NAME)
#     tools      = {t.name: t for t in tools_list}

#     def wrap(name, tool, extractor):
#         async def node(state):
#             sec = extractor(state)
#             resp = await tool.ainvoke(sec)
#             if isinstance(resp, str):
#                 try: resp = json.loads(resp)
#                 except: resp = {"output": resp}
#             state.setdefault("messages", []).append({"tool": name, "output": resp})
#             state[name] = resp
#             if name == "call_gemini_api" and resp.get("status"):
#                 for k in ("audio_type","title","description","keywords"):
#                     if k in resp: state.setdefault("data", {})[k] = resp[k]
#             if name == "createVideo" and resp.get("status"):
#                 # for k in ("video_bytes",):
#                 if "video_bytes" in resp:
#                     state.setdefault("data", {})["video_bytes"] = resp["video_bytes"]
#             return state
#         return node

#     def human_pause(state):
#         info = {
#             "audio_type": state["data"]["audio_type"],
#             "title":      state["data"]["title"],
#             "description": state["data"]["description"],
#             "keywords":    state["data"]["keywords"],
#             # "video_file": state["data"]["video_file"],
#         }
#         # human_input = interrupt(info)
#         # # store into shared data
#         # return {"data": human_input}
#         return interrupt(info)

#     builder = StateGraph(MemeState)
#     builder.add_node("download_random_meme", wrap("download_random_meme", tools["download_random_meme"], lambda s: {}))
#     builder.add_node("call_gemini_api", wrap("call_gemini_api", tools["call_gemini_api"], lambda s: {}))
#     builder.add_node("createVideo", wrap("createVideo", tools["createVideo"], lambda s: {
#         "meme_image_name": None,
#         "audio_type": s["data"]["audio_type"]
#     }))
#     builder.add_node("human_pause", human_pause)
#     builder.add_node("upload_video_to_youtube", wrap("upload_video_to_youtube", tools["upload_video_to_youtube"], lambda s: {
#         "title":       s["data"]["title"],
#         "description": s["data"]["description"],
#         "keywords":    s["data"]["keywords"]
#     }))

#     builder.set_entry_point("download_random_meme")
#     builder.add_edge("download_random_meme","call_gemini_api")
#     builder.add_edge("call_gemini_api","createVideo")
#     builder.add_edge("createVideo","human_pause")
#     builder.add_edge("human_pause","upload_video_to_youtube")
#     builder.add_edge("upload_video_to_youtube", END)

#     graph = builder.compile(checkpointer=InMemorySaver())
#     yield

# app = FastAPI(lifespan=lifespan)
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# @app.post("/start")
# async def start():
#     init = {"data": {}, "messages": []}
#     res = await graph.ainvoke(init, config={"configurable":{"thread_id":THREAD_ID}})
#     if "__interrupt__" in res:
#         return {"interrupt": res["__interrupt__"], "state": res}
#     return {"result": res}

# @app.post("/resume")
# async def resume(req: Request):
#     body = await req.json()
#     print(f"Received body: {body}")
#     updated_data = body.get("updated", {})
#     print(f"Resuming with data: {updated_data}")
#     print(f"type of updated_data: {type(updated_data)}")
#     cmd = Command(resume=body["interrupt"]["resume"],update={"data": updated_data})
#     res = await graph.ainvoke(cmd, config={"configurable":{"thread_id":THREAD_ID}})
#     return {"result": res}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8001)




import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import TypedDict, Optional
from typing_extensions import Annotated
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.environ.get("MCP_URL",)
SERVER_NAME = "meme_pipeline"
THREAD_ID = "meme-pipeline-thread"

def dict_reducer(a: dict, b: any) -> dict:
    if not isinstance(b, dict):
        # Ignore non-dict values (like resume tokens)
        return a or {}
    return {**(a or {}), **b}

class MemeState(TypedDict, total=False):
    data: Annotated[dict, dict_reducer]
    messages: list
    download_random_meme: dict
    call_gemini_api: dict
    createVideo: dict
    upload_video_to_youtube: dict

from typing import Optional
class StartInput(BaseModel):
    access_token: Optional[str]
    refresh_token: Optional[str]

graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    client = MultiServerMCPClient({SERVER_NAME: {"transport": "streamable_http", "url": MCP_URL}})
    tools_list = await client.get_tools(server_name=SERVER_NAME)
    tools = {t.name: t for t in tools_list}

    def wrap(name, tool, extractor):
        async def node(state):
            sec = extractor(state)
            resp = await tool.ainvoke(sec)
            if isinstance(resp, str):
                try:
                    resp = json.loads(resp)
                except:
                    resp = {"output": resp}
            state.setdefault("messages", []).append({"tool": name, "output": resp})
            state[name] = resp
            if name == "call_gemini_api" and resp.get("status"):
                for k in ("audio_type", "title", "description", "keywords"):
                    if k in resp:
                        state.setdefault("data", {})[k] = resp[k]
            if name == "createVideo" and resp.get("status") and "video_bytes" in resp:
                state.setdefault("data", {})["video_bytes"] = resp["video_bytes"]
            return state
        return node

    def prepare_create(state):
        # This is called AFTER video creation, ready for user verify
        info = {
            "audio_type": state["data"]["audio_type"],
            "title": state["data"]["title"],
            "description": state["data"]["description"],
            "keywords": state["data"]["keywords"],
        }
        # return interrupt(info)
        human_input = interrupt(info)  # would be payload on pause, or return value on resume

        # After resume, human_input is the updated dict from frontend.
        # Wrap it to return a dict updating `data`.
        return {"data": human_input}

    builder = StateGraph(MemeState)
    builder.add_node("download_random_meme", wrap("download_random_meme", tools["download_random_meme"], lambda s: {}))
    builder.add_node("call_gemini_api", wrap("call_gemini_api", tools["call_gemini_api"], lambda s: {}))
    builder.add_node("createVideo", wrap("createVideo", tools["createVideo"], lambda s: {
        "meme_image_name": None,
        "audio_type": s["data"]["audio_type"]
    }))
    builder.add_node("prepare_create", prepare_create)
    builder.add_node("upload_video_to_youtube", wrap("upload_video_to_youtube", tools["upload_video_to_youtube"], lambda s: {
        "title": s["data"]["title"],
        "description": s["data"]["description"],
        "keywords": s["data"]["keywords"],
        "access_token": s["data"]["access_token"],
        "refresh_token": s["data"]["refresh_token"],
    }))

    builder.set_entry_point("download_random_meme")
    builder.add_edge("download_random_meme", "call_gemini_api")
    builder.add_edge("call_gemini_api", "createVideo")
    builder.add_edge("createVideo", "prepare_create")
    builder.add_edge("prepare_create", "upload_video_to_youtube")
    builder.add_edge("upload_video_to_youtube", END)

    graph = builder.compile(checkpointer=InMemorySaver())
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health")
async def health():
    print("Healthy app!")
    return {"status": "healthy"}

@app.post("/start")
async def start(payload: StartInput):
    print("Payload is: ",payload)
    init = {
        "data": {
            "access_token": payload.access_token,
            "refresh_token": payload.refresh_token
        },
        "messages": []
    }
    res = await graph.ainvoke(init, config={"configurable": {"thread_id": THREAD_ID}})
    if "__interrupt__" in res:
        return {"interrupt": res["__interrupt__"], "state": res}
    return {"result": res}

@app.post("/resume")
async def resume(req: Request):
    body = await req.json()
    updated = body.get("updated", {})
    cmd = Command(resume=body["interrupt"]["resume"], update={"data": updated})
    res = await graph.ainvoke(cmd, config={"configurable": {"thread_id": THREAD_ID}})
    return {"result": res}

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="127.0.0.1", port=8001)
    uvicorn.run(app, host="0.0.0.0", port=8001)


