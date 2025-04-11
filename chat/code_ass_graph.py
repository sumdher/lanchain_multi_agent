from dotenv import load_dotenv
from bs4 import BeautifulSoup as Soup
from pydantic import BaseModel, Field
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, START, END
from typing import List
from typing_extensions import TypedDict

load_dotenv()

# -----------------------
# 1) Define the Data Model
# -----------------------
class CodeSolution(BaseModel):
    """Schema for code solutions to questions about LCEL."""
    prefix: str = Field(description="Description of the problem and approach")
    imports: str = Field(description="Code block import statements")
    code: str = Field(description="Code block not including import statements")

# -----------------------
# 2) Graph Node Functions
# -----------------------
class GraphState(TypedDict, total=False):
    """
    Represents the state of our graph.

    Attributes:
        error : Binary flag for control flow to indicate whether test error was tripped
        messages : With user question, error messages, reasoning
        generation : Code solution
        iterations : Number of tries
    """

    error: str
    messages: List
    generation: str
    iterations: int
    
    # The ones you actually store:
    context: str
    raw_llm_output: dict
    final_solution: CodeSolution
    
def read_docs(state: GraphState) -> GraphState:
    """
    Loads the LCEL documentation from a URL and stores it into the graph state.
    """
    url = "https://python.langchain.com/docs/concepts/lcel/"
    crawler = RecursiveUrlLoader(url=url, max_depth=20, extractor=lambda x: Soup(x, "html.parser").text)
    docs = crawler.load()
    print(f"\nRead: {len(docs)} docs")

    # Sort and reverse so we produce a single large text block
    d_sorted = sorted(docs, key=lambda x: x.metadata["source"])
    d_reversed = list(reversed(d_sorted))
    concatenated_content = "\n\n\n --- \n\n\n".join([doc.page_content for doc in d_reversed])

    # Store in state
    state["context"] = concatenated_content
    # Initialize iteration counter, error, and messages
    state["iterations"] = 0
    state["error"] = ""
    # The user prompt
    state.setdefault("messages", [])
    return state

def generate(state: GraphState) -> GraphState:
    """
    Build the prompt and call the LLM with structured output. If we had a prior parsing error,
    we nudge the assistant to re-invoke the code tool.
    """
    print("---GENERATING CODE SOLUTION---")

    # Pull items from state
    context = state["context"]
    messages = state["messages"]
    error_flag = state["error"]

    # If we got here after a parsing error, nudge the LLM to fix its response
    if error_flag == "yes":
        messages += [
            (
                "assistant",
                "Retry. You must invoke the code tool with prefix, imports, and code fields. Fix your parsing errors."
            )
        ]

    # Create the prompt
    code_gen_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """<instructions>
                You are a coding assistant with expertise in LCEL (LangChain Expression Language).
                Here is the LCEL documentation:
                -------
                {context}
                -------
                Answer the user question based on the above docs. Provide code that can be executed,
                including all imports and variables. Structure your output via the code tool with:
                1) prefix
                2) imports
                3) code
                </instructions>
                """,
            ),
            ("placeholder", "{messages}"),
        ]
    )

    # Create your LLM with structured output
    llm = ChatDeepSeek(temperature=0, model="deepseek-chat")
    structured_llm = llm.with_structured_output(CodeSolution, include_raw=True)
    prompt_to_llm = code_gen_prompt | structured_llm

    # Invoke LLM
    response = prompt_to_llm.invoke({"context": context, "messages": messages})

    # Store the raw LLM output to state (for debugging or further checks)
    state["raw_llm_output"] = response

    # Add the LLM's text to messages so the conversation is updated
    # NOTE: If you want to show partial “assistant” content, you can do so, but here we keep minimal
    assistant_text = response["raw"].content  # The raw text from the LLM
    messages += [("assistant", assistant_text)]

    # Update state
    state["messages"] = messages
    return state

def check_parsing(state: GraphState) -> GraphState:
    """
    Check if the LLM properly invoked the code tool (i.e., we have 'parsed' result).
    If not, set error='yes' so we can try again. Otherwise parse and store the final answer.
    """
    print("---CHECKING PARSING---")
    raw_llm_output = state["raw_llm_output"]
    parsed = raw_llm_output.get("parsed")
    parse_error = raw_llm_output.get("parsing_error")

    if parse_error:
        print("Parsing error!")
        state["error"] = "yes"
        # Insert the parse error into the conversation
        err_msg = f"Parse error: {parse_error}. You must fix your tool invocation."
        state["messages"] += [("assistant", err_msg)]
    elif not parsed:
        print("No 'parsed' object found. Must re-invoke the tool.")
        state["error"] = "yes"
        # Insert the tool-not-invoked error
        err_msg = "No parsed data found! You must properly invoke the code tool with prefix/imports/code."
        state["messages"] += [("assistant", err_msg)]
    else:
        print("---NO PARSING ERROR---")
        # Store the final structured solution
        state["error"] = "no"
        state["final_solution"] = parsed  # The Pydantic CodeSolution
    return state

def decide_to_finish(state: GraphState) -> str:
    """
    Decide whether to finish or retry. If 'error' == 'yes' and we haven't hit max_tries, we do another round.
    Otherwise, we end.
    """
    max_tries = 3
    state["iterations"] += 1
    if state["error"] == "no" or state["iterations"] >= max_tries:
        print("---DECISION: FINISH---")
        return "end"
    else:
        print("---DECISION: RETRY---")
        return "generate"

# -----------------------
# 3) Build the Graph
# -----------------------
workflow = StateGraph(GraphState)

# Nodes
workflow.add_node("read_docs", read_docs)
workflow.add_node("generate", generate)
workflow.add_node("check_parsing", check_parsing)

# Edges
workflow.add_edge(START, "read_docs")
workflow.add_edge("read_docs", "generate")
workflow.add_edge("generate", "check_parsing")
workflow.add_conditional_edges(
    "check_parsing",
    decide_to_finish,
    {
        "end": END,
        # If not ending, we go back to "generate"
        "generate": "generate",
    },
)

# Compile
app = workflow.compile()


# -----------------------
# 4) Provide a Helper
# -----------------------
def code_ass_help(question: str = "How do I build an RAG chain in LCEL?"):
    """
    Graph-based invocation that returns a code solution from the LLM.
    """
    # We start with minimal user "messages", just the question
    initial_state = {
        "messages": [("user", question)],
    }

    # Invoke the graph
    final_state = app.invoke(initial_state)

    if final_state.get("final_solution"):
        # Return the parsed code solution (prefix, imports, code)
        return final_state["final_solution"]
    else:
        # If no final solution, either we had too many errors or something else happened
        return None


# -----------------------
# 5) Example usage
# -----------------------
if __name__ == "__main__":
    solution = code_ass_help("How do I load text into LCEL and run a simple chain?")
    print("Solution:")
    print("PREFIX:\n", solution.prefix)
    print("\nIMPORTS:\n", solution.imports)
    print("\nCODE:\n", solution.code)