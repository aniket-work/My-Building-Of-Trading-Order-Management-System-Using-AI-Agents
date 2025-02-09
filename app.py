import streamlit as st
from workflow import create_workflow
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from logger_config import logger


def init_session_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'order_in_progress' not in st.session_state:
        st.session_state.order_in_progress = False


def display_chat_message(role, content, container):
    with container.chat_message(role):
        container.write(content)


def main():
    st.set_page_config(layout="wide", page_title="B2B Trading Platform")

    # Custom CSS for styling
    st.markdown("""
        <style>
        .main {
            padding: 0rem 1rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 16px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    init_session_state()

    # Load environment variables
    load_dotenv()

    # Create the workflow
    agent = create_workflow()

    # Page Header
    st.title("B2B Trading Platform")
    st.markdown("---")

    # Create two columns for the companies
    col1, col2 = st.columns(2)

    with col1:
        st.header("Company 1 - Order Placement")
        st.markdown("""
        Place your order with the following format:
        - "I want to place an order for item_XX, quantity Y, my customer id is customer_ZZ"
        - "Cancel order 223"
        """)

        # Order form for Company 1
        with st.form("company1_order_form"):
            user_input = st.text_area(
                "Enter your order or cancellation request:",
                height=100,
                placeholder="Example: Cancel order 12345"
            )
            submitted = st.form_submit_button("Submit Request", use_container_width=True)

            if submitted and not st.session_state.order_in_progress:
                if user_input.strip():
                    st.session_state.order_in_progress = True
                    st.session_state.messages = []  # Clear previous messages

                    # Create message and log it
                    human_message = HumanMessage(content=user_input)
                    logger.debug(f"Created HumanMessage: {human_message}")

                    try:
                        # Process request
                        logger.info(f"Processing request: {user_input}")
                        messages_dict = {"messages": [human_message]}

                        # Create a placeholder for real-time updates
                        with col2:
                            st.header("Company 2 - Order Processing")
                            response_container = st.container()

                            with st.spinner("Processing your request..."):
                                response_received = False
                                for chunk in agent.stream(messages_dict, stream_mode="values"):
                                    if 'messages' in chunk and chunk['messages']:
                                        last_message = chunk['messages'][-1]
                                        if hasattr(last_message, 'content'):
                                            response_received = True

                                            # Try to parse JSON response for better formatting
                                            try:
                                                import json
                                                content = json.loads(last_message.content)
                                                formatted_content = json.dumps(content, indent=2)
                                            except:
                                                formatted_content = last_message.content

                                            st.session_state.messages.append(
                                                ("assistant", formatted_content)
                                            )
                                            display_chat_message(
                                                "assistant",
                                                formatted_content,
                                                response_container
                                            )

                                if not response_received:
                                    st.error("No response received from the processing system.")

                    except Exception as e:
                        logger.exception("Error processing request")
                        with col2:
                            st.error(f"Error processing request: {str(e)}")
                    finally:
                        st.session_state.order_in_progress = False
                else:
                    st.error("Please enter a request.")

    with col2:
        if not st.session_state.messages:
            st.header("Company 2 - Order Processing")
            st.info("Waiting for orders from Company 1...")

        # Display chat history
        for role, content in st.session_state.messages:
            display_chat_message(role, content, st)


if __name__ == "__main__":
    logger.info("Starting B2B Trading Platform")
    main()