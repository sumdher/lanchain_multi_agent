# chat/tools.py

from langchain_core.tools import tool
from chat.code_ass_graph import code_ass_help
from langchain_experimental.utilities import PythonREPL
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.riza.command import ExecPython

tavily_search_tool = TavilySearchResults(max_results=1)

@tool
def python_repl(code: str) -> str:
    """Executes small Python code snippets and returns the result. 
    Useful for math, string manipulation, datetime parsing, or exploring logic.
    """
    repl = PythonREPL()
    try:
        result = repl.run(code)
    except BaseException as e:
        print (f"Failed to execute. Error: {repr(e)}")
        # Rewrite the code and rerun it
    return f"{result}"

@tool
def lcel_codegen(question: str) -> str:
    """
    Generates LangChain Expression Language (LCEL) code solutions.
    Use this when the user requests LCEL-based chains, pipelines, or runnable examples.
    """
    result = code_ass_help(question)
    if not result:
        return "Failed to generate code. Try rephrasing your question."
    
    return (
        f"{result.prefix}\n\n"
        f"**IMPORTS:**\n```python\n{result.imports}\n```\n\n"
        f"**CODE:**\n```python\n{result.code}\n```\n"
    )
