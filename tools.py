from langchain_core.tools import tool
from config import llm
from langchain.prompts import ChatPromptTemplate
from state_manager import state_manager


@tool
def cancel_order(query: str) -> dict:
    """Cancel an order by order ID"""
    prompt = ChatPromptTemplate.from_template("""
        Extract the order_id from this text and return ONLY a valid JSON object.

        Text: {text}

        Rules:
        - The order_id should be a string
        - If you see a number or UUID after "order_id" or "order", that's the order_id
        - Return format must be exactly: {{"order_id": "EXTRACTED_ID"}}
        - Do not include markdown formatting, backticks, or any other text
    """)

    try:
        # Get LLM response
        result = llm.invoke(prompt.format(text=query))

        # Clean the response
        content = result.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('\n', 1)[0]
        content = content.replace('json', '').strip()

        # Parse JSON
        import json
        data = json.loads(content)
        order_id = data.get("order_id")

        if not order_id:
            return {"error": "No order ID found in request"}

        # Check if order exists in state
        order_state = state_manager.get_state(order_id)
        if not order_state:
            return {"error": f"Order {order_id} not found"}

        # Cancel order by clearing its state
        state_manager.clear_state(order_id)
        return {
            "status": "success",
            "message": f"Order {order_id} has been cancelled",
            "order_id": order_id
        }

    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON format: {str(e)}"}
    except Exception as e:
        return {"error": f"Error cancelling order: {str(e)}"}