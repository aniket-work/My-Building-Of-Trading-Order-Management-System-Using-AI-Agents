# Replace entire workflow.py
from typing import List
from langchain_core.messages import BaseMessage
from nodes import (
    categorize_query, check_inventory, compute_shipping,
    process_payment, call_model_2, call_tools_2, route_query_1,
    process_order_result
)
from tools import cancel_order
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from state import MessagesState
from logger_config import logger


def create_workflow():
    # Create workflow with proper state definition
    workflow = StateGraph(MessagesState)

    # Add nodes that maintain state
    workflow.add_node("RouteQuery", categorize_query)
    workflow.add_node("CheckInventory", check_inventory)
    workflow.add_node("ComputeShipping", compute_shipping)
    workflow.add_node("ProcessPayment", process_payment)
    workflow.add_node("ProcessOrderResult", process_order_result)

    # Add tool nodes
    tools_2 = [cancel_order]
    tool_node_2 = ToolNode(tools_2)

    # Define edges with state propagation
    workflow.add_edge(START, "RouteQuery")

    # Add conditional edges that pass state
    workflow.add_conditional_edges(
        "RouteQuery",
        route_query_1,
        {
            "PlaceOrder": "CheckInventory",
            "CancelOrder": "CancelOrder",
            "ProcessOrderResult": "ProcessOrderResult"
        }
    )

    # Sequential edges
    workflow.add_edge("CheckInventory", "ComputeShipping")
    workflow.add_edge("ComputeShipping", "ProcessPayment")
    workflow.add_edge("ProcessPayment", "ProcessOrderResult")
    workflow.add_edge("ProcessOrderResult", END)

    # Cancel order flow
    workflow.add_node("CancelOrder", call_model_2)
    workflow.add_node("tools_2", tool_node_2)

    workflow.add_conditional_edges(
        "CancelOrder",
        call_tools_2,
        {
            "tools_2": "tools_2",
            "end": END
        }
    )
    workflow.add_edge("tools_2", "CancelOrder")

    logger.info("Workflow created with proper state management")
    return workflow.compile()