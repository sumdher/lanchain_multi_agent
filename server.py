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
    """
    Streams the LLM's response to user_input, chunk by chunk.
    """
    try:
        async for chunk in graph.astream(
            {"messages": [HumanMessage(content=user_input)]},
            config,
            stream_mode="messages"
        ):
            if content := getattr(chunk[0], "content", ""):
                await websocket.send_text(content)
    except asyncio.CancelledError:
        # print("Stream cancelled normally.")
        # Re-raise so the caller knows it was cancelled
        raise
    except Exception as e:
        # print(f"Stream error: {str(e)}")
        await websocket.send_text(f"[ERROR] {str(e)}")
    finally:
        await websocket.send_text("[[END]]")

@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    Main websocket endpoint that receives user messages,
    streams LLM responses, and handles concurrency (stop, new prompt).
    """
    await websocket.accept()
    # print("WebSocket connection accepted.")

    # Create / configure your LLM graph
    thread_id = "websocket-client"
    graph = init_graph(thread_id)  # Synchronous initialization
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    # Set initial persona (synchronously)
    default_mode = modes.get("default", "default")
    if not isinstance(default_mode, str):
        default_mode = "default"
    graph.invoke({"messages": [HumanMessage(content=default_mode)]}, config)

    message_queue = asyncio.Queue()
    current_stream_task = None

    async def receive_messages():
        """
        Continuously receive messages from the client
        and put them into message_queue.
        """
        while True:
            try:
                message = await websocket.receive_text()
                await message_queue.put(message)
            except WebSocketDisconnect:
                # print("WebSocket disconnected (receive_messages).")
                break
            except Exception as e:
                # print(f"Receive error: {e}")
                break

    # Start a background task to read incoming messages from the socket
    receive_task = asyncio.create_task(receive_messages())

    try:
        while True:
            # Wait for next user input from the queue
            user_input = await message_queue.get()
            # print(f"Received message from client: {user_input}")

            # 1) Handle mode-change commands
            if user_input.startswith("/mode "):
                mode_key = user_input.removeprefix("/mode ").strip()
                if mode_prompt := modes.get(mode_key):
                    graph.invoke({"messages": [HumanMessage(content=mode_prompt)]}, config)
                    await websocket.send_text(f"[Mode changed to: {mode_key}]")
                else:
                    await websocket.send_text(f"[Error] Unknown mode: {mode_key}")
                continue

            # 2) Handle STOP commands
            if user_input == "__STOP__":
                # Only cancel if there's an active stream
                if current_stream_task and not current_stream_task.done():
                    # print("STOP command -> Canceling current_stream_task.")
                    current_stream_task.cancel()
                    try:
                        await current_stream_task
                    except asyncio.CancelledError:
                        pass
                    # After stopping, re-init the graph so the old prompt's context is thrown away
                    print("Re-initializing graph after STOP.")
                    graph = init_graph(thread_id)
                    graph.invoke({"messages": [HumanMessage(content=default_mode)]}, config)
                else:
                    # print("STOP command received but no active stream. Ignoring.")
                    pass
                continue

            # 3) If it's a normal user message, start streaming a response
            # print(f"Starting streaming response for: {user_input}")
            current_stream_task = asyncio.create_task(
                stream_response(graph, websocket, user_input, config)
            )

            # We'll wait for EITHER the stream to finish OR a new message
            message_get_task = asyncio.create_task(message_queue.get())
            done, pending = await asyncio.wait(
                [current_stream_task, message_get_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            if current_stream_task in done:
                # The streaming completed normally
                # print("Streaming finished for this user_input.")
                message_get_task.cancel()
                current_stream_task = None
            else:
                # A new user message arrived mid-stream
                # print("A new user message arrived mid-stream. Canceling old stream.")
                current_stream_task.cancel()
                try:
                    await current_stream_task
                except asyncio.CancelledError:
                    # print("Confirmed old stream was cancelled.")
                    pass
                
                # Re-init the graph so we discard partial context from the old generation
                # print("Re-initializing graph after mid-stream cancellation.")
                graph = init_graph(thread_id)
                graph.invoke({"messages": [HumanMessage(content=default_mode)]}, config)

                # The newly arrived message is the result from message_get_task
                new_msg = await message_get_task
                # print(f"New message that arrived mid-stream: {new_msg}")

                # If that new message was STOP, handle it
                if new_msg == "__STOP__":
                    # print("STOP arrived after a new prompt, so ignoring old prompt entirely.")
                    # Optionally send an END marker
                    await websocket.send_text("[[END]]")
                else:
                    # Put it back on the queue so the loop picks it up next
                    # print(f"Re-queueing new message for next loop iteration: {new_msg}")
                    await message_queue.put(new_msg)

                # IMPORTANT: continue to the next iteration
                continue

    except WebSocketDisconnect:
        print("Client disconnected (main loop).")
    except Exception as e:
        print(f"Error in main websocket loop: {e}")
    finally:
        # Clean up tasks
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
        print("WebSocket closed. Server finished.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4580)
