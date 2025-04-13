# main.py

import sys
import os
import ast

from chat.graph import init_graph
from chat.modes import modes
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langchain_core.runnables.config import RunnableConfig

# Terminal color codes
AI_PROMPT_COLOR = "\033[0;36m"
AI_COLOR = "\033[1;4;36m"
USER_PROMPT_COLOR = "\033[0;32m"
USER_COLOR = "\033[1;4;32m"
RESET_COLOR = "\033[0m"

def stream_graph_updates(graph: CompiledStateGraph, tid: str, user_input: str):
    config: RunnableConfig = {"configurable": {"thread_id": tid}}
    tool_block_accumulator = ""

    print(f"\n🤖 {AI_COLOR} AI Chat Bot{"\033[1;34m"}{AI_PROMPT_COLOR}:")

    for chunk in graph.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config,
        stream_mode="messages"
    ):
        message_obj, metadata = chunk[0], chunk[1]
        text = getattr(message_obj, "content", "")

        if not text:
            continue

        combined_text = tool_block_accumulator + text
        tool_block_accumulator = ""
        output_buffer = ""
        remaining = combined_text

        while True:
            start_index = remaining.find("[{")
            if start_index == -1:
                output_buffer += remaining
                break

            output_buffer += remaining[:start_index]
            end_index = remaining.find("}]", start_index)

            if end_index == -1:
                tool_block_accumulator = remaining[start_index:]
                break

            bracketed_str = remaining[start_index:end_index + 2]
            remaining = remaining[end_index + 2:]
            neat_str = _neatify(bracketed_str)
            output_buffer += neat_str

        if output_buffer.strip():
            print(f"{AI_PROMPT_COLOR}" + output_buffer, end="", flush=True)
    print("\n")

def _neatify(bracketed_str: str) -> str:
    try:
        data = ast.literal_eval(bracketed_str)
    except Exception as e:
        return ""

    lines = []
    if isinstance(data, list):
        for item in data:
            title = item.get("title", "(No Title)")
            url = item.get("url", "")
            snippet = item.get("content", "")
            snippet = (snippet[:100] + "...") if len(snippet) > 100 else snippet
            lines.append(f"• **{title}**\n  URL: {url}\n  snippet: {snippet}\n")
    return "\n".join(lines)

def cli_chat():
    if len(sys.argv) >= 2:
        mode_key = sys.argv[1]
        if mode_key not in modes:
            print(f"Invalid mode key: {mode_key}")
            print(f"Available keys: {list(modes.keys())}")
            sys.exit(1)
    else:
        mode_key = "default"

    mode_prompt = modes.get(mode_key, None) or "default"
    tid = "cli-thread"
    graph = init_graph(tid, sys_msg=None, human_msg=mode_prompt)

    print(f"{RESET_COLOR}\n🧠 LangGraph CLI Chat — Mode: {mode_key}\n(Press Ctrl+C or type 'quit' to exit)\n")

    try:
        while True:
            user_input = input(f"🖋️  {USER_COLOR}User{"\033[1;32m"}{USER_PROMPT_COLOR}: ")
            if user_input.lower() in ["quit", "exit", "bye", "q"]:
                print(f"{RESET_COLOR}👋 Goodbye!")
                break
            elif user_input.lower() in ["quit -ai", "exit -ai", "bye -ai"]:
                stream_graph_updates("Okay, I gotta go! See you later! 👋")
                break
            stream_graph_updates(graph, tid, user_input)
    except KeyboardInterrupt:
        print(f"{RESET_COLOR}\n👋 Goodbye!")

if __name__ == "__main__":
    cli_chat()
