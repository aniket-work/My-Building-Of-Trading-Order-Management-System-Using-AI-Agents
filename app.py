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
        container.markdown(f"""
            <div style='
                padding: 1rem;
                margin: 0.5rem 0;
                border-radius: 8px;
                background: {'#f0f2f6' if role == "user" else '#fff'};
                border: 1px solid {'#d0d0d0' if role == "user" else '#e0e0e0'};
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            '>
                {content}
            </div>
        """, unsafe_allow_html=True)


def main():
    st.set_page_config(layout="wide", page_title="GlobalTrade Nexus AI", page_icon="🌐")

    # Professional CSS styling
    st.markdown("""
        <style>
        :root {
            --primary: #2a4a7c;
            --secondary: #3a6ea5;
            --background: #f8f9fa;
        }

        .main {
            background: var(--background);
            padding: 2rem 1rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            margin-bottom: 1.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 12px 24px;
            border-radius: 6px;
            background: #fff;
            border: 1px solid #e0e0e0;
            transition: all 0.2s;
        }

        .stTabs [aria-selected="true"] {
            background: var(--primary) !important;
            color: white !important;
        }

        .stTextArea textarea {
            border-radius: 8px !important;
            padding: 1rem !important;
        }

        .stButton button {
            background: var(--primary) !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 0.75rem 2rem !important;
            transition: all 0.2s;
        }

        .stButton button:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }

        .header-section {
            background: var(--primary);
            padding: 2rem;
            border-radius: 12px;
            color: white;
            margin-bottom: 2rem;
        }

        .company-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 1.5rem;
        }

        .status-indicator {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            background: #e8f4ff;
            display: inline-block;
            font-weight: 500;
        }
        </style>
    """, unsafe_allow_html=True)

    init_session_state()
    load_dotenv()
    agent = create_workflow()

    # Page Header
    with st.container():
        st.markdown("""
            <div class="header-section">
                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                    <h1 style="margin: 0; font-size: 2.5rem;">GlobalTrade Nexus AI</h1>
                    <div style="flex-grow: 1"></div>
                    <div style="display: flex; gap: 2rem; font-size: 1.1rem;">
                        <div>🔒 Secure Channel</div>
                        <div>🌍 GMT+0</div>
                    </div>
                </div>
                <div style="display: flex; gap: 2rem;">
                    <div>
                        <div style="font-size: 1.2rem;">🏭 Company 1</div>
                        <div style="font-size: 0.9rem; opacity: 0.9;">Buyer Partner</div>
                    </div>
                    <div style="border-left: 2px solid white; height: 40px;"></div>
                    <div>
                        <div style="font-size: 1.2rem;">🏦 Company 2</div>
                        <div style="font-size: 0.9rem; opacity: 0.9;">Distribution Partner</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        with st.container():
            st.markdown('<div class="company-card">', unsafe_allow_html=True)
            st.subheader("📥 Buyer Company - Order Management Console")
            st.markdown("""
                <div style="margin: 1rem 0; background: #f8f9fa; padding: 1rem; border-radius: 8px;">
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">📋 Order Format:</div>
                    <div style="font-size: 0.9rem;">
                        <code>I want to place an order for item_XX, quantity Y, my customer id is customer_ZZ</code>
                    </div>
                    <div style="font-size: 0.9rem; margin-top: 0.5rem;">
                        <code>Cancel order 223</code>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            with st.form("company1_order_form"):
                user_input = st.text_area(
                    "Enter your request:",
                    height=120,
                    placeholder="Enter order details or cancellation request...",
                    label_visibility="collapsed"
                )
                submitted = st.form_submit_button("Submit Transaction →", use_container_width=True)

                if submitted and not st.session_state.order_in_progress:
                    if user_input.strip():
                        st.session_state.order_in_progress = True
                        st.session_state.messages = []

                        human_message = HumanMessage(content=user_input)
                        logger.debug(f"Created HumanMessage: {human_message}")

                        try:
                            logger.info(f"Processing request: {user_input}")
                            messages_dict = {"messages": [human_message]}

                            response_received = False
                            seen_messages = set()  # Track unique messages

                            with col2:
                                with st.container():
                                    st.markdown('<div class="company-card">', unsafe_allow_html=True)
                                    st.subheader("📤 Supplier Company Console")
                                    response_container = st.container()


                                    with st.spinner("🔍 Validating transaction..."):
                                        response_received = False
                                        for chunk in agent.stream(messages_dict, stream_mode="values"):
                                            if 'messages' in chunk and chunk['messages']:
                                                last_message = chunk['messages'][-1]
                                                if hasattr(last_message, 'content'):
                                                    message_hash = hash(
                                                        f"{last_message.content}")  # Create unique hash for message
                                                    if message_hash not in seen_messages:  # Only process new messages
                                                        seen_messages.add(message_hash)
                                                        response_received = True
                                                        try:
                                                            import json
                                                            content = json.loads(last_message.content)
                                                            formatted_content = json.dumps(content, indent=2)
                                                        except:
                                                            formatted_content = last_message.content

                                                        st.session_state.messages.append(
                                                            ("assistant", formatted_content))
                                                        display_chat_message("assistant", formatted_content,
                                                                             response_container
                                                        )

                                        if not response_received:
                                            st.error("⚠️ Transaction validation failed")
                        except Exception as e:
                            logger.exception("Error processing request")
                            with col2:
                                st.error(f"🚨 System Error: {str(e)}")
                        finally:
                            st.session_state.order_in_progress = False
                    else:
                        st.error("❌ Please enter a valid request")
            st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        with st.container():
            if not st.session_state.messages:
                st.markdown('<div class="company-card">', unsafe_allow_html=True)
                st.subheader("📤 Supplier Company Console")
                st.markdown("""
                    <div style="text-align: center; padding: 2rem; color: #666;">
                        <div style="font-size: 2rem; margin-bottom: 1rem;">⏳</div>
                        Awaiting transaction requests from Buyer Company
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown('<div class="company-card">', unsafe_allow_html=True)
                st.subheader("📤 Supplier Company Console")
                for role, content in st.session_state.messages:
                    display_chat_message(role, content, st)


if __name__ == "__main__":
    logger.info("Starting B2B Trading Platform")
    main()