import json
import datetime
import uuid
from state_manager import state_manager
import uuid
from logger_config import logger
from typing import Dict, Any, Optional
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from config import llm
from typing import Literal
from langgraph.graph import END
import pandas as pd

from state import MessagesState
from tools import cancel_order

# Load data
inventory_df = pd.read_csv("data/inventory.csv")
customers_df = pd.read_csv("data/customers.csv")

# Convert to dictionaries
inventory = inventory_df.set_index("item_id").T.to_dict()
customers = customers_df.set_index("customer_id").T.to_dict()

# Add tools configuration
tools_2 = [cancel_order]
llm_with_tools_2 = llm.bind_tools(tools_2)


from logger_config import logger

# In nodes.py - Add these imports at the top (with existing imports)
from state_manager import state_manager
import uuid
from logger_config import logger


def categorize_query(state: MessagesState) -> MessagesState:
    """Categorize user query and validate basic input."""
    try:
        messages = state.get("messages", [])
        query = messages[0].content if messages else ""

        # Generate unique order ID
        order_id = str(uuid.uuid4())
        logger.debug(f"Generated new order_id: {order_id}")

        if not query:
            return {
                "messages": messages,
                "order_state": None,
                "error": "Empty query received"
            }

        prompt = ChatPromptTemplate.from_template("""
            Extract order information from this text and return ONLY a valid JSON object without any markdown formatting or backticks.

            Text: {text}

            The JSON must have these exact fields:
            - category: Either "PlaceOrder" for new orders or "CancelOrder" for cancellations
            - customer_id: (format: customer_XX) - Required for PlaceOrder
            - item_id: (format: item_XX) - Required for PlaceOrder
            - quantity: (number) - Required for PlaceOrder
            - location: "domestic" (default) - Optional

            Example format:
            {{
                "category": "PlaceOrder",
                "customer_id": "customer_14",
                "item_id": "item_51",
                "quantity": 2,
                "location": "domestic"
            }}

            Return ONLY the JSON object, no other text, no code blocks, no backticks.
        """)

        response = prompt.invoke({"text": query})
        result = llm.invoke(response)

        content = result.content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        parsed_data = json.loads(content)

        if parsed_data.get("category") == "PlaceOrder":
            required_fields = ["customer_id", "item_id", "quantity"]
            missing_fields = [field for field in required_fields if field not in parsed_data]
            if missing_fields:
                raise ValueError(f"Missing required fields for PlaceOrder: {', '.join(missing_fields)}")

        if parsed_data.get("category") == "PlaceOrder" and "location" not in parsed_data:
            parsed_data["location"] = "domestic"

        order_state = {
            "customer_id": parsed_data.get("customer_id"),
            "item_id": parsed_data.get("item_id"),
            "quantity": parsed_data.get("quantity"),
            "location": parsed_data.get("location", "domestic"),
            "category": parsed_data.get("category"),
            "shipping_cost": None,
            "payment_status": None,
            "order_id": order_id  # Include order_id in state
        }

        # Store in global state
        state_manager.set_state(order_id, {
            "order_state": order_state,
            "messages": messages
        })

        logger.debug(f"Initial state stored for order_id {order_id}: {order_state}")

        return {
            "messages": messages,
            "order_state": order_state,
            "error": None
        }

    except Exception as e:
        logger.exception(f"Error in categorize_query: {str(e)}")
        return {
            "messages": messages,
            "order_state": None,
            "error": f"Error processing query: {str(e)}"
        }


def check_inventory(state: MessagesState) -> MessagesState:
    """Check if the requested item is in stock."""
    try:
        messages = state.get("messages", [])
        order_state = state.get("order_state", {})
        order_id = order_state.get('order_id')

        logger.debug(f"Checking inventory for order_id: {order_id}")

        if order_id:
            stored_state = state_manager.get_state(order_id)
            if stored_state:
                order_state = stored_state.get("order_state", order_state)
                logger.debug(f"Retrieved stored state for order_id {order_id}: {order_state}")

        item_id = order_state.get("item_id")
        quantity = order_state.get("quantity")

        if not item_id or not quantity:
            return {
                "messages": messages,
                "order_state": order_state,
                "error": "Missing item_id or quantity in order state"
            }

        if item_id not in inventory:
            return {
                "messages": messages,
                "order_state": order_state,
                "error": f"Item {item_id} not found in inventory"
            }

        if inventory[item_id]["stock"] >= quantity:
            logger.debug(f"Item {item_id} is in stock. Requested: {quantity}, Available: {inventory[item_id]['stock']}")

            updated_order_state = {
                **order_state,
                "inventory_checked": True,
                "stock_available": inventory[item_id]["stock"]
            }

            # Update global state
            state_manager.update_state(order_id, {
                "order_state": updated_order_state
            })

            logger.debug(f"Updated state for order_id {order_id}: {updated_order_state}")

            return {
                "messages": messages,
                "order_state": updated_order_state,
                "error": None
            }
        else:
            return {
                "messages": messages,
                "order_state": order_state,
                "error": f"Insufficient stock. Requested: {quantity}, Available: {inventory[item_id]['stock']}"
            }

    except Exception as e:
        logger.exception(f"Error in check_inventory: {str(e)}")
        return {
            "messages": messages,
            "order_state": order_state,
            "error": f"Error checking inventory: {str(e)}"
        }


def compute_shipping(state: MessagesState) -> MessagesState:
    """Calculate shipping costs."""
    try:
        messages = state.get("messages", [])
        order_state = state.get("order_state", {})
        order_id = order_state.get('order_id')

        logger.debug(f"Computing shipping for order_id: {order_id}")

        if order_id:
            stored_state = state_manager.get_state(order_id)
            if stored_state:
                order_state = stored_state.get("order_state", order_state)
                logger.debug(f"Retrieved stored state for order_id {order_id}: {order_state}")

        customer_id = order_state.get("customer_id")
        item_id = order_state.get("item_id")
        quantity = order_state.get("quantity")
        location = order_state.get("location")

        if not all([customer_id, item_id, quantity, location]):
            return {
                "messages": messages,
                "order_state": order_state,
                "error": "Missing order details from previous step"
            }

        if customer_id not in customers:
            return {
                "messages": messages,
                "order_state": order_state,
                "error": f"Customer {customer_id} not found"
            }

        weight_per_item = inventory[item_id]["weight"]
        total_weight = weight_per_item * quantity

        rates = {"local": 5, "domestic": 10, "international": 20}
        shipping_rate = rates.get(location, rates["domestic"])
        cost = total_weight * shipping_rate

        logger.debug(f"Shipping calculation complete: Cost: ${cost:.2f}, Location: {location}")

        updated_order_state = {
            **order_state,
            "shipping_cost": f"${cost:.2f}",
            "total_weight": total_weight,
            "shipping_rate": shipping_rate
        }

        # Update global state
        state_manager.update_state(order_id, {
            "order_state": updated_order_state
        })

        logger.debug(f"Updated state for order_id {order_id}: {updated_order_state}")

        return {
            "messages": messages,
            "order_state": updated_order_state,
            "error": None
        }

    except Exception as e:
        logger.exception(f"Error in compute_shipping: {str(e)}")
        return {
            "messages": messages,
            "order_state": order_state,
            "error": f"Error computing shipping: {str(e)}"
        }


def process_payment(state: MessagesState) -> MessagesState:
    """Process payment and maintain order state."""
    try:
        messages = state.get("messages", [])
        order_state = state.get("order_state", {})
        order_id = order_state.get('order_id')

        logger.debug(f"Processing payment for order_id: {order_id}")

        if order_id:
            stored_state = state_manager.get_state(order_id)
            if stored_state:
                order_state = stored_state.get("order_state", order_state)
                logger.debug(f"Retrieved stored state for order_id {order_id}: {order_state}")

        customer_id = order_state.get("customer_id")
        item_id = order_state.get("item_id")
        quantity = order_state.get("quantity")
        shipping_cost = order_state.get("shipping_cost")
        location = order_state.get("location")

        if not all([customer_id, item_id, quantity, shipping_cost, location]):
            missing_fields = [field for field in ["customer_id", "item_id", "quantity", "shipping_cost", "location"]
                              if not order_state.get(field)]
            return {
                "messages": messages,
                "order_state": order_state,
                "error": f"Missing required order information: {', '.join(missing_fields)}"
            }

        logger.debug(f"Payment successful for amount: {shipping_cost}")

        updated_order_state = {
            **order_state,
            "payment_status": "Success"
        }

        # Update global state
        state_manager.update_state(order_id, {
            "order_state": updated_order_state
        })

        logger.debug(f"Updated state for order_id {order_id}: {updated_order_state}")

        return {
            "messages": messages,
            "order_state": updated_order_state,
            "error": None
        }

    except Exception as e:
        logger.exception(f"Error in process_payment: {str(e)}")
        return {
            "messages": messages,
            "order_state": order_state,
            "error": f"Payment processing failed: {str(e)}"
        }


# UPDATE the process_order_result function in nodes.py:

def process_order_result(state: MessagesState) -> MessagesState:
    """Format the final order result."""
    try:
        messages = state.get("messages", [])
        order_state = state.get("order_state", {})
        order_id = order_state.get('order_id')

        logger.debug(f"Processing final result for order_id: {order_id}")

        if order_id:
            stored_state = state_manager.get_state(order_id)
            if stored_state:
                order_state = stored_state.get("order_state", order_state)
                logger.debug(f"Retrieved stored state for order_id {order_id}: {order_state}")

        if "error" in state and state["error"]:
            return {
                "messages": messages + [AIMessage(content=f"Error: {state['error']}")],
                "order_state": order_state,
                "error": state["error"]
            }

        customer_id = order_state.get("customer_id")
        item_id = order_state.get("item_id")
        quantity = order_state.get("quantity")
        location = order_state.get("location")
        shipping_cost = order_state.get("shipping_cost")
        payment_status = order_state.get("payment_status")

        if not all([customer_id, item_id, quantity, location, shipping_cost, payment_status]):
            missing_fields = [field for field in
                              ["customer_id", "item_id", "quantity", "location", "shipping_cost", "payment_status"]
                              if not order_state.get(field)]
            return {
                "messages": messages + [
                    AIMessage(content=f"Error: Missing order details - {', '.join(missing_fields)}")
                ],
                "order_state": order_state,
                "error": f"Missing fields: {', '.join(missing_fields)}"
            }

        if payment_status == "Success":
            # Create response details
            response_details = {
                "status": "Order Successfully Placed",
                "order_id": order_id,
                "customer_id": customer_id,
                "item_id": item_id,
                "quantity": quantity,
                "location": location,
                "shipping_cost": shipping_cost,
                "payment_status": payment_status
            }

            # Store successful order in state manager for future reference
            state_manager.set_state(order_id, {
                "order_state": response_details,
                "messages": messages,
                "timestamp": datetime.datetime.now().isoformat()
            })

            logger.debug(f"Stored successful order in state manager: {order_id}")

            return {
                "messages": messages + [
                    AIMessage(content=f"Order Details:\n{json.dumps(response_details, indent=2)}")
                ],
                "order_state": order_state,
                "error": None
            }
        else:
            return {
                "messages": messages + [AIMessage(content="Payment failed. Please try again.")],
                "order_state": order_state,
                "error": "Payment failed"
            }

    except Exception as e:
        logger.exception(f"Error in process_order_result: {str(e)}")
        return {
            "messages": messages + [AIMessage(content=f"Error processing order: {str(e)}")],
            "order_state": order_state,
            "error": str(e)
        }

def route_query_1(state: MessagesState) -> Literal["PlaceOrder", "CancelOrder", "ProcessOrderResult"]:
    """Route the query based on its category."""
    try:
        messages = state.get("messages", [])
        order_state = state.get("order_state", {})

        if "error" in state and state["error"]:
            logger.debug("Error found in state, routing to ProcessOrderResult")
            return "ProcessOrderResult"

        category = order_state.get("category")
        logger.debug(f"Routing based on category: {category}")

        if category == "PlaceOrder":
            logger.debug("Routing to PlaceOrder")
            return "PlaceOrder"
        elif category == "CancelOrder":
            logger.debug("Routing to CancelOrder")
            return "CancelOrder"
        else:
            logger.debug("Unknown category, routing to ProcessOrderResult")
            return "ProcessOrderResult"

    except Exception as e:
        logger.exception(f"Error in routing: {str(e)}")
        return "ProcessOrderResult"


def call_model_2(state: MessagesState) -> MessagesState:
    """Use the LLM to process cancellation."""
    try:
        messages = state.get("messages", [])
        response = llm_with_tools_2.invoke(str(messages))
        return {
            "messages": messages + [response],
            "order_state": state.get("order_state"),
            "error": None
        }
    except Exception as e:
        return {
            "messages": messages,
            "order_state": state.get("order_state"),
            "error": f"Error in model call: {str(e)}"
        }


def call_tools_2(state: MessagesState) -> Literal["tools_2", "end"]:
    """Route workflow based on tool calls."""
    try:
        messages = state.get("messages", [])
        last_message = messages[-1]
        return "tools_2" if last_message.tool_calls else "end"
    except Exception as e:
        print(f"Error in tool routing: {str(e)}")
        return "end"