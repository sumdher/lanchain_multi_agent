from typing import Annotated

from langchain_deepseek import ChatDeepSeek
from langchain_community.tools.tavily_search import TavilySearchResults
# from langchain_core.messages import BaseMessage
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, field_validator, ValidationError
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig

load_dotenv()

class PydanticState(BaseModel):
    messages: Annotated[list, add_messages]

    # @field_validator('messages')
    # @classmethod
    # def validate_message(cls, value):
    #     # Ensure the mood is either "happy" or "sad"
    #     if value not in ["happy", "sad"]:
    #         raise ValueError("Each mood must be either 'happy' or 'sad'")
    #     return value

# try:
#     state = PydanticState(name="John Doe", mood="mad")
# except ValidationError as e:
#     print("Validation Error:", e)

class State(TypedDict):
    messages: Annotated[list, add_messages]

def init_graph(tid, sys_msg=None) -> CompiledStateGraph:
    memory = MemorySaver()

    graph_builder = StateGraph(PydanticState)

    tool = TavilySearchResults(max_results=2)
    tools = [tool]

    llm = ChatDeepSeek(
        model="deepseek-chat",
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(tools)

    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    graph_builder.add_node("chatbot", chatbot)

    tool_node = ToolNode(tools=[tool])
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    # Any time a tool is called, we return to the chatbot to decide the next step
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.set_entry_point("chatbot")
    graph = graph_builder.compile(checkpointer=memory)

    config: RunnableConfig = {"configurable": {"thread_id": tid}}
    
    if sys_msg is not None:
        messages = [SystemMessage(content=sys_msg)]
        graph.invoke({"messages": messages}, config)
    
    return graph

graph_1: CompiledStateGraph = init_graph(
    tid="1",
    sys_msg="You are a sassy litle chatbot💅, a fiesty & zesty one 💃. Rawrrr!😼"
    )

def init_chat(graph: CompiledStateGraph, tid):    
    graph = graph
    config: RunnableConfig = {"configurable": {"thread_id": tid}}
    
    def _stream_graph_updates(user_input: str):
        for event in graph.stream(
            {
                # "messages": [{"role": "user", "content": user_input}],
                "messages": [HumanMessage(content=user_input)]
            },
            config,
            # stream_mode="values"
            ):
            for value in event.values():
                print("🤖 AI:", value["messages"][-1].content)   
    while True:
        try:
            user_input = input("🖋️  User: ")
            
            if user_input.lower() in ["quit", "exit", "q", "bye"]:
                print("👋 Goodbye!")
            
            elif user_input.lower() in ["quit -ai", "exit -ai", "bye -ai"]:
                _stream_graph_updates("Okay, I gotta go! See you later! 👋")
                break

            _stream_graph_updates(user_input)
        except Exception as e:
            print(e)
            break
        
init_chat(graph_1, tid="1")