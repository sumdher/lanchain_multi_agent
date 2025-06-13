# server.py
import asyncio
from contextlib import suppress
from fastapi import UploadFile, File, FastAPI, WebSocket, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from typing import List
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
import time
import shutil

from chat.graph import init_graph
from chat.modes import modes


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_store: dict = {}  # In-memory store of reusable memory per thread_id
UPLOAD_DIR = "user_files"

try:
    shutil.rmtree(UPLOAD_DIR)
except FileNotFoundError:
    pass
os.makedirs(UPLOAD_DIR, exist_ok=True)

loaded_files_set = set()
file_map_backend = {}

async def stream_response(graph, websocket, user_input, config):
    try:
        async for chunk in graph.astream(
            {"messages": [HumanMessage(content=user_input)]},
            config,
            stream_mode="messages"
        ):
            if content := getattr(chunk[0], "content", ""):
                await websocket.send_text(content)
    except asyncio.CancelledError:
        print("Stream response task was cancelled.")
    except Exception as e:
        await websocket.send_text(f"[ERROR] {str(e)}")
    finally:
        await websocket.send_text("[[END]]")

@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()

    thread_id = "websocket-client"
    memory = memory_store.setdefault(thread_id, MemorySaver())

    graph = init_graph(thread_id, memory)
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    default_mode = modes.get("default", "default")
    if not isinstance(default_mode, str):
        default_mode = "default"
    graph.invoke({"messages": [HumanMessage(content=default_mode)]}, config)

    message_queue = asyncio.Queue()
    receive_task = None
    consumer_task = None

    async def receive_messages():
        try:
            while True:
                message = await websocket.receive_text()
                await message_queue.put(message)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as e:
            print(f"Error in receive_messages: {e}")

    async def consumer():
        current_stream_task = None
        try:
            while True:
                user_input = await message_queue.get()

                if user_input.startswith("/mode "):
                    mode_key = user_input.removeprefix("/mode ").strip()
                    if mode_prompt := modes.get(mode_key):
                        graph.invoke({"messages": [HumanMessage(content=mode_prompt)]}, config)
                        await websocket.send_text(f"[Mode changed to: {mode_key}]")
                    else:
                        await websocket.send_text(f"[Error] Unknown mode: {mode_key}")
                    await websocket.send_text("[[END]]")
                    continue

                if user_input == "__CONTEXT__":
                    readable = []
                    unreadable = []
                    loaded_texts = []

                    for filename, original_name in file_map_backend.items():
                        if filename in loaded_files_set:
                            continue
                        file_path = os.path.join(UPLOAD_DIR, filename)
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                text = f.read().strip()
                                if text:
                                    loaded_texts.append(text)
                                    readable.append(original_name)
                                else:
                                    unreadable.append(original_name)
                                loaded_files_set.add(filename)
                        except Exception as e:
                            print(f"Error reading {file_path}: {e}")
                            unreadable.append(original_name)

                    if loaded_texts:
                        context_block = ""
                        for filename, content in zip(readable, loaded_texts):
                            context_block += f"[FILE: {filename}]\n{content}\n\n"

                        await graph.ainvoke({"messages": [SystemMessage(content=context_block)]}, config)

                    summary_prompt = """
                        Please confirm that you have successfully loaded the uploaded files in context.

                        Instructions:
                        1. Acknowledge that you can access the files.
                        2. List all filenames currently loaded.
                        3. Do not provide summaries or content from the files.

                        If any files are unreadable or in a binary format, please indicate which ones and disregard them.
                        """
                    if readable:
                        summary_prompt += "All good."
                    if unreadable and not readable:
                        summary_prompt = "The files I uploaded seem to be binary or unreadable. Disregard them."

                    if summary_prompt:
                        response = await graph.ainvoke({"messages": [HumanMessage(content=summary_prompt)]}, config)
                        reply_text = response["messages"][-1].content
                        # Send filenames that were loaded (for frontend to update UI)
                        await websocket.send_text(f"[[LOADED::{','.join(readable)}]]")

                        # Then send the LLM response
                        await websocket.send_text(reply_text + "\n")
                        await websocket.send_text("[[END]]")

                    else:
                        await websocket.send_text("No new files were added to context.")
                        
                    await websocket.send_text("[[END]]")
                    continue

                if user_input == "__STOP__":
                    if current_stream_task and not current_stream_task.done():
                        current_stream_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await current_stream_task
                    await websocket.send_text("[[END]]")
                    continue

                current_stream_task = asyncio.create_task(
                    stream_response(graph, websocket, user_input, config)
                )

                next_input_task = asyncio.create_task(message_queue.get())
                done, _ = await asyncio.wait(
                    [current_stream_task, next_input_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                if next_input_task in done:
                    new_msg = next_input_task.result()
                    current_stream_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await current_stream_task
                    await websocket.send_text("[[END]]")
                    await message_queue.put(new_msg)
                else:
                    next_input_task.cancel()
                    current_stream_task = None

        except asyncio.CancelledError:
            print("Consumer task cancelled — exiting cleanly.")
        finally:
            if current_stream_task and not current_stream_task.done():
                current_stream_task.cancel()
                with suppress(asyncio.CancelledError):
                    await current_stream_task


    try:
        receive_task = asyncio.create_task(receive_messages())
        consumer_task = asyncio.create_task(consumer())
        await asyncio.gather(receive_task, consumer_task)
    except asyncio.CancelledError:
        print("WebSocket handler cancelled.")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        for task in (receive_task, consumer_task):
            if task and not task.done():
                task.cancel()
        await asyncio.gather(*(t for t in (receive_task, consumer_task) if t), return_exceptions=True)
        try:
            if os.path.exists(UPLOAD_DIR):
                shutil.rmtree(UPLOAD_DIR)
                os.makedirs(UPLOAD_DIR, exist_ok=True)
        except Exception as e:
            print(f"Error cleaning up user_files: {e}")
        print("Server cleanup done.")

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    saved_files = []
    key_map = {}
    for file in files:
        key = f"{int(time.time() * 1000)}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, key)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        file_map_backend[key] = file.filename
        key_map[key] = file.filename
        saved_files.append(file.filename)
    return {"status": "success", "uploaded": saved_files, "file_map": key_map}

@app.post("/delete-file")
async def delete_file(file_key: str = Form(...)):
    filename = file_map_backend.get(file_key)
    if not filename:
        return JSONResponse(status_code=404, content={"error": "File not found"})
    file_path = os.path.join(UPLOAD_DIR, file_key)
    try:
        os.remove(file_path)
        del file_map_backend[file_key]
        return {"status": "deleted"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4580, timeout_keep_alive=5)
