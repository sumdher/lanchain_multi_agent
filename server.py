# # server.py

# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# from chat.graph import init_graph
# from chat.modes import modes
# from langchain_core.messages import HumanMessage
# from langchain_core.runnables.config import RunnableConfig
# from langgraph.checkpoint.memory import MemorySaver
# import asyncio
# from contextlib import suppress

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # In-memory store of reusable memory per thread_id
# memory_store: dict = {}

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
#             try:
#                 user_input = await message_queue.get()
#             except asyncio.CancelledError:
#                 print("message_queue.get() was cancelled — graceful shutdown.")
#                 return  # or `break`, depending on your control flow


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
#         try:
#             await websocket.close()
#         except RuntimeError:
#             pass

#         tasks = []
#         if receive_task and not receive_task.done():
#             receive_task.cancel()
#             tasks.append(receive_task)

#         if current_stream_task and not current_stream_task.done():
#             current_stream_task.cancel()
#             tasks.append(current_stream_task)

#         # Gracefully wait on all tasks and handle any cancellations without crashing
#         results = await asyncio.gather(*tasks, return_exceptions=True)
#         for r in results:
#             if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError):
#                 print(f"Cleanup error: {r}")

#         print("Server cleanup done.")


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=4580, timeout_keep_alive=5)



# server.py

import asyncio
from contextlib import suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from chat.graph import init_graph
from chat.modes import modes
from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_store: dict = {}  # In-memory store of reusable memory per thread_id


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
            pass  # Normal disconnect/cancel
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
        print("Server cleanup done.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4580, timeout_keep_alive=5)
