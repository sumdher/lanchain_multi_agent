# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# from chat.graph import init_graph
# from chat.modes import modes
# from langchain_core.messages import HumanMessage
# from langchain_core.runnables.config import RunnableConfig
# from langgraph.checkpoint.memory import MemorySaver
# import asyncio

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # In-memory store of reusable memory per thread_id
# memory_store = {}

# async def stream_response(graph, websocket, user_input, config):
#     try:
#         async for chunk in graph.astream(
#             {"messages": [HumanMessage(content=user_input)]},
#             config,
#             stream_mode="messages"
#         ):
#             if content := getattr(chunk[0], "content", ""):
#                 await websocket.send_text(content)
#     except asyncio.CancelledError:
#         raise
#     except Exception as e:
#         await websocket.send_text(f"[ERROR] {str(e)}")
#     finally:
#         await websocket.send_text("[[END]]")

# @app.websocket("/ws/chat")
# async def chat_websocket(websocket: WebSocket):
#     await websocket.accept()

#     thread_id = "websocket-client"
#     memory = memory_store.get(thread_id)
#     if not memory:
#         memory = MemorySaver()
#         memory_store[thread_id] = memory

#     graph = init_graph(thread_id, memory)
#     config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

#     default_mode = modes.get("default", "default")
#     if not isinstance(default_mode, str):
#         default_mode = "default"
#     graph.invoke({"messages": [HumanMessage(content=default_mode)]}, config)

#     message_queue = asyncio.Queue()
#     current_stream_task = None

#     async def receive_messages():
#         while True:
#             try:
#                 message = await websocket.receive_text()
#                 await message_queue.put(message)
#             except (WebSocketDisconnect, asyncio.CancelledError):
#                 break
#             except Exception:
#                 break

#     receive_task = asyncio.create_task(receive_messages())

#     try:
#         while True:
#             user_input = await message_queue.get()

#             if user_input.startswith("/mode "):
#                 mode_key = user_input.removeprefix("/mode ").strip()
#                 if mode_prompt := modes.get(mode_key):
#                     graph.invoke({"messages": [HumanMessage(content=mode_prompt)]}, config)
#                     await websocket.send_text(f"[Mode changed to: {mode_key}]")
#                 else:
#                     await websocket.send_text(f"[Error] Unknown mode: {mode_key}")
#                 continue

#             if user_input == "__STOP__":
#                 if current_stream_task and not current_stream_task.done():
#                     current_stream_task.cancel()
#                     try:
#                         await current_stream_task
#                     except asyncio.CancelledError:
#                         pass
#                 await websocket.send_text("[[END]]")
#                 continue

#             current_stream_task = asyncio.create_task(
#                 stream_response(graph, websocket, user_input, config)
#             )

#             message_get_task = asyncio.create_task(message_queue.get())
#             done, pending = await asyncio.wait(
#                 [current_stream_task, message_get_task],
#                 return_when=asyncio.FIRST_COMPLETED
#             )

#             if current_stream_task in done:
#                 message_get_task.cancel()
#                 current_stream_task = None
#             else:
#                 current_stream_task.cancel()
#                 try:
#                     await current_stream_task
#                 except asyncio.CancelledError:
#                     pass

#                 new_msg = await message_get_task
#                 await websocket.send_text("[[END]]")
#                 await message_queue.put(new_msg)
#                 continue

#     except WebSocketDisconnect:
#         print("Client disconnected.")
#     except Exception as e:
#         print(f"Main loop error: {e}")
#     finally:
#         await websocket.close()
#         print("WebSocket closed.")

#         if receive_task and not receive_task.done():
#             receive_task.cancel()

#         if current_stream_task and not current_stream_task.done():
#             current_stream_task.cancel()

#         await asyncio.gather(
#             receive_task,
#             current_stream_task,
#             return_exceptions=True
#         )
#         print("Server cleanup done.")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=4580, timeout_keep_alive=5)


from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from chat.graph import init_graph
from chat.modes import modes
from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
import asyncio
import pdfplumber

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memory and upload storage
memory_store = {}
uploaded_text_store = {}

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
        raise
    except Exception as e:
        await websocket.send_text(f"[ERROR] {str(e)}")
    finally:
        await websocket.send_text("[[END]]")


@app.post("/upload")
async def upload_file(
    thread_id: str = Form(...),
    file: UploadFile = File(...)
):
    if file.filename.endswith(".txt"):
        content = (await file.read()).decode("utf-8")
    elif file.filename.endswith(".pdf"):
        content = ""
        with pdfplumber.open(file.file) as pdf:
            for page in pdf.pages:
                content += page.extract_text() + "\n"
    else:
        return {"error": "Unsupported file type. Only .txt and .pdf are allowed."}

    uploaded_text_store[thread_id] = content.strip()
    return {"status": "success", "chars": len(content.strip())}


@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()

    thread_id = "websocket-client"

    # Get or create memory and graph
    memory = memory_store.get(thread_id)
    if not memory:
        memory = MemorySaver()
        memory_store[thread_id] = memory

    graph = init_graph(thread_id, memory)
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    default_mode = modes.get("default", "default")
    if not isinstance(default_mode, str):
        default_mode = "default"
    graph.invoke({"messages": [HumanMessage(content=default_mode)]}, config)

    # Inject uploaded file content (once)
    uploaded_context = uploaded_text_store.pop(thread_id, None)
    if uploaded_context:
        context_intro = (
            "You have received the following document. Use it to answer future questions.\n\n"
            f"{uploaded_context}"
        )
        graph.invoke({"messages": [HumanMessage(content=context_intro)]}, config)

    message_queue = asyncio.Queue()
    current_stream_task = None

    async def receive_messages():
        while True:
            try:
                message = await websocket.receive_text()
                await message_queue.put(message)
            except (WebSocketDisconnect, asyncio.CancelledError):
                break
            except Exception:
                break

    receive_task = asyncio.create_task(receive_messages())

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
                continue

            if user_input == "__STOP__":
                if current_stream_task and not current_stream_task.done():
                    current_stream_task.cancel()
                    try:
                        await current_stream_task
                    except asyncio.CancelledError:
                        pass
                await websocket.send_text("[[END]]")
                continue

            current_stream_task = asyncio.create_task(
                stream_response(graph, websocket, user_input, config)
            )

            message_get_task = asyncio.create_task(message_queue.get())
            done, pending = await asyncio.wait(
                [current_stream_task, message_get_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            if current_stream_task in done:
                message_get_task.cancel()
                current_stream_task = None
            else:
                current_stream_task.cancel()
                try:
                    await current_stream_task
                except asyncio.CancelledError:
                    pass

                new_msg = await message_get_task
                await websocket.send_text("[[END]]")
                await message_queue.put(new_msg)
                continue

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"Main loop error: {e}")
    finally:
        await websocket.close()
        print("WebSocket closed.")

        if receive_task and not receive_task.done():
            receive_task.cancel()

        if current_stream_task and not current_stream_task.done():
            current_stream_task.cancel()

        await asyncio.gather(
            receive_task,
            current_stream_task,
            return_exceptions=True
        )
        print("Server cleanup done.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4580, timeout_keep_alive=5)
