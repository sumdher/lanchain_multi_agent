# # server.py
# '''
# source ~/.venvs/langchain/.venv_langchain/bin/activate
# uvicorn server:app --reload --port 4580
# '''

# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# from chat.graph import init_graph
# from chat.modes import modes
# from langchain_core.messages import HumanMessage
# from langchain_core.runnables.config import RunnableConfig

# app = FastAPI()

# # Allow all origins for development (customize in prod!)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.websocket("/ws/chat")
# async def chat_websocket(websocket: WebSocket):
#     await websocket.accept()

#     thread_id = "websocket-client"
#     graph = init_graph(thread_id)
#     config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

#     # Set initial persona (mode)
#     default_mode: str = modes["default"] or "default"
#     graph.invoke({"messages": [HumanMessage(content=default_mode)]}, config)

#     try:
#         while True:
#             user_input = await websocket.receive_text()

#             # Optional: switch personality mode via special message
#             if user_input.startswith("/mode "):
#                 mode_key = user_input.removeprefix("/mode ").strip()
#                 mode_prompt = modes.get(mode_key)
#                 if not mode_prompt:
#                     await websocket.send_text(f"[Mode Error] Unknown mode: '{mode_key}'")
#                     continue
#                 graph.invoke({"messages": [HumanMessage(content=mode_prompt)]}, config)
#                 await websocket.send_text(f"[Mode changed to: {mode_key}]")
#                 continue

#             # Stream response from LangGraph
#             async for chunk in graph.astream(
#                 {"messages": [HumanMessage(content=user_input)]},
#                 config,
#                 stream_mode="messages"
#             ):
#                 msg = getattr(chunk[0], "content", "")
#                 if msg:
#                     await websocket.send_text(msg)

#             await websocket.send_text("[[END]]")  # end of one response

#     except WebSocketDisconnect:
#         print("WebSocket closed by client")



# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from chat.graph import init_graph
from chat.modes import modes
from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        print("Stream cancelled normally")
    except Exception as e:
        print(f"Stream error: {str(e)}")
        await websocket.send_text(f"[ERROR] {str(e)}")
    finally:
        await websocket.send_text("[[END]]")

@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    
    thread_id = "websocket-client"
    graph = init_graph(thread_id)  # Sync initialization
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    # Set initial persona (sync)
    default_mode = modes.get("default", "default")
    if not isinstance(default_mode, str):
        default_mode = "default"
    graph.invoke({"messages": [HumanMessage(content=default_mode)]}, config)

    message_queue = asyncio.Queue()
    current_stream_task = None
    receive_task = None

    async def receive_messages():
        while True:
            try:
                message = await websocket.receive_text()
                await message_queue.put(message)
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Receive error: {e}")
                break

    receive_task = asyncio.create_task(receive_messages())

    try:
        while True:
            user_input = await message_queue.get()

            # Handle mode changes (sync)
            if user_input.startswith("/mode "):
                mode_key = user_input.removeprefix("/mode ").strip()
                if mode_prompt := modes.get(mode_key):
                    graph.invoke(
                        {"messages": [HumanMessage(content=mode_prompt)]},
                        config
                    )
                    await websocket.send_text(f"[Mode changed to: {mode_key}]")
                else:
                    await websocket.send_text(f"[Error] Unknown mode: {mode_key}")
                continue

            # Handle stop command
            if user_input == "__STOP__":
                if current_stream_task and not current_stream_task.done():
                    current_stream_task.cancel()
                    try:
                        await current_stream_task
                    except asyncio.CancelledError:
                        pass
                continue

            # Start streaming response (async)
            current_stream_task = asyncio.create_task(
                stream_response(graph, websocket, user_input, config)
            )

            # Wait for either stream completion or new message
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
                if new_msg == "__STOP__":
                    await websocket.send_text("[[END]]")
                else:
                    await message_queue.put(new_msg)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup tasks
        if receive_task and not receive_task.done():
            receive_task.cancel()
        
        if current_stream_task and not current_stream_task.done():
            current_stream_task.cancel()
        
        await asyncio.gather(
            receive_task,
            current_stream_task,
            return_exceptions=True
        )
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4580)
