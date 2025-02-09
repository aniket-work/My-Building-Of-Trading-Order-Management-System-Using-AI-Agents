# Replace entire state.py content
from typing import TypedDict, Optional, List, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class OrderState(TypedDict):
    customer_id: Optional[str]
    item_id: Optional[str]
    quantity: Optional[int]
    location: str
    shipping_cost: Optional[str]
    payment_status: Optional[str]
    category: Optional[str]

class MessagesState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # Ensures message history persistence
    order_state: Optional[OrderState]
    error: Optional[str]