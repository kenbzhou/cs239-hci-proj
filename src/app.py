import time
from dataclasses import dataclass
from typing import Literal

import anthropic
import streamlit as st

from complexity_analyzer import analyze_complexity
from thought_params import ThoughtParameters

# Set page config
st.set_page_config(page_title="Claude 3.7 Thinking Demo", page_icon="🧠")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm Claude. How can I help you today?"}
    ]

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

if "live_complexity" not in st.session_state:
    st.session_state.live_complexity = 0.0

if "live_thinking_limit" not in st.session_state:
    st.session_state.live_thinking_limit = ThoughtParameters.QUICK.value[
        "budget_tokens"
    ]


# Initialize Claude client (you'll need an API key)
@st.cache_resource
def get_claude_client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    if api_key is None:
        api_key = st.sidebar.text_input("Claude API Key", type="password")
        if not api_key:
            st.warning("Please enter an API key to continue")
            st.stop()
    return anthropic.Anthropic(api_key=api_key)


@dataclass
class Block:
    type: Literal["thinking", "text"]
    content: str


# stream wrapper for the thinking Claude API
def stream_handler(stream):
    for event in stream:
        if event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                # print(f"Thinking: {event.delta.thinking}", end="", flush=True)
                yield Block(type="thinking", content=event.delta.thinking)
            elif event.delta.type == "text_delta":
                # print(f"Response: {event.delta.text}", end="", flush=True)
                # print("GOT HERE1")
                yield event.delta.text


# Function to calculate thinking limit based on complexity
def get_thinking_limit(complexity):
    if complexity < 0.3:
        return ThoughtParameters.QUICK.value["budget_tokens"]  # Simple queries
    elif complexity < 0.6:
        return ThoughtParameters.BALANCED.value["budget_tokens"]  # Moderate complexity
    else:
        return ThoughtParameters.THOROUGH.value["budget_tokens"]  # Complex queries


# Display chat history and thinking details
st.title("Claude 3.7 Thinking Demo")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
    if "thinking_time" in message:
        with st.expander("Thinking Details"):
            st.write(f"Complexity Score: {message.get('complexity_score', 'N/A')}")
            st.write(f"Thinking Limit: {message.get('thinking_limit', 'N/A')} tokens")
            st.write(f"Response Time: {message['thinking_time']:.2f} seconds")

# Create a container for the live complexity metrics
metrics_container = st.container()

# Display current complexity metrics before chat input
with metrics_container:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Query Complexity", f"{st.session_state.live_complexity:.2f}")
    with col2:
        st.metric("Thinking Limit", f"{st.session_state.live_thinking_limit} tokens")

# Chat input that submits on Enter
prompt = st.chat_input("What would you like to know?", key="draft_input")

# Calculate complexity for the new prompt
complexity_score = analyze_complexity(prompt)
thinking_limit = get_thinking_limit(complexity_score)

# Update session state
st.session_state.live_complexity = complexity_score
st.session_state.live_thinking_limit = thinking_limit
st.session_state.last_query = prompt

if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.write(prompt)

    # Display response with a spinner
    with st.chat_message("assistant"):
        expander = st.expander("Assistant is thinking...", expanded=True)

        client = get_claude_client()
        start_time = time.time()

        # Call Claude API with the determined thinking limit
        with client.messages.stream(
            model="claude-3-7-sonnet-20250219",
            max_tokens=8192,
            temperature=1,
            system=f"""You are an AI assistant with a specific thinking token limit of {thinking_limit}.
                        Carefully consider the user's request but optimize for efficient responses.""",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            thinking={"type": "enabled", "budget_tokens": thinking_limit},
        ) as raw_stream:
            stream = stream_handler(raw_stream)
            print("stream.__next__()", stream.__next__())

            # thinking will be first
            for block in stream:
                if type(block) is Block:
                    expander.write(block.content)
                else:
                    st.write(block)
                    response = block + st.write_stream(stream)
                    break

    # Add assistant response to chat history with metadata
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "complexity_score": complexity_score,
            "thinking_limit": thinking_limit,
            # "thinking_time": thinking_time,
        }
    )

    # Update the metrics display after processing
    # st.rerun()

# Add sidebar information and show last query stats
with st.sidebar:
    st.title("About")
    st.info("""
    This demo showcases dynamic thinking limits for Claude 3.7.
    
    The app uses a basic NLP heuristic to evaluate query complexity
    and sets the thinking limit accordingly.
    """)

    if st.session_state.last_query:
        st.subheader("Last Query Stats")
        st.write(
            f'Query: "{st.session_state.last_query[:50]}{"..." if len(st.session_state.last_query) > 50 else ""}"'
        )
        st.write(f"Complexity Score: {st.session_state.live_complexity:.2f}")
        st.write(f"Thinking Limit: {st.session_state.live_thinking_limit} tokens")
