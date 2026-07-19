from langgraph.graph import StateGraph, END
from graphs.states import AgentState
from graphs.nodes import (
    plan_node, tool_selector, local_search_node, web_search_node,
    graph_search_node, parallel_search_node, prepare_documents,
    generate_answer, reflection_node
)

def build_agentic_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("plan", plan_node)
    workflow.add_node("local_search", local_search_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("graph_search", graph_search_node)
    workflow.add_node("parallel_search", parallel_search_node)
    workflow.add_node("prepare_docs", prepare_documents)
    workflow.add_node("generate", generate_answer)
    workflow.add_node("reflection", reflection_node)

    workflow.set_entry_point("plan")

    workflow.add_conditional_edges(
        "plan",
        tool_selector,
        {
            "local_search": "local_search",
            "web_search": "web_search",
            "graph_search": "graph_search",
            "parallel_search": "parallel_search",
            "prepare_docs": "prepare_docs",
            "end": END
        }
    )

    workflow.add_edge("local_search", "plan")
    workflow.add_edge("web_search", "plan")
    workflow.add_edge("graph_search", "plan")
    workflow.add_edge("parallel_search", "plan")

    workflow.add_edge("prepare_docs", "generate")
    workflow.add_edge("generate", "reflection")

    workflow.add_conditional_edges(
        "reflection",
        lambda s: "plan" if s.get("need_retry") else "end",
        {"plan": "plan", "end": END}
    )

    return workflow.compile()

agentic_graph = build_agentic_graph()