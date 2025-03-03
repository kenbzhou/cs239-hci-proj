import itertools
import time

import anthropic
import streamlit as st

from pathlib import Path
from complexity_analyzer import analyze_complexity
from thought_params import ThoughtParameters
from streamlit_extras.bottom_container import bottom
from streamlit_extras.stylable_container import stylable_container
from st_keyup import st_keyup
import streamlit.components.v1 as components


build_dir = Path(__file__).parent.absolute() / "streamlit-keyup" / "src" / "st_keyup" / "frontend"
st_keyup_chat = components.declare_component("st_keyup_chat", path=str(build_dir))

# Set page config
st.set_page_config(page_title="Claude 3.7 Thinking Demo", page_icon="🧠")

if "prompt" not in st.session_state:
    st.session_state.prompt = ""

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

if "thinking_content" not in st.session_state:
    st.session_state.thinking_content = {}

# Add this variable to store thinking content during streaming
if "current_thinking" not in st.session_state:
    st.session_state.current_thinking = []

# Evil rerendering hack to automatically clear input field.
if "render_inc" not in st.session_state:
    st.session_state.render_inc = 0
if "keyup_key" not in st.session_state:
    st.session_state.keyup_key = f"ku{st.session_state.render_inc}"


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


# Modify the stream_thinking function
def stream_thinking(stream):
    for event in stream:
        if event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                st.session_state.current_thinking.append(event.delta.thinking)
                yield event.delta.thinking


def stream_text(stream):
    for event in stream:
        if event.type == "content_block_delta":
            if event.delta.type == "text_delta":
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
# Replace the existing message display loop
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "thinking_content" in message:
            with st.expander("Thinking Process", expanded=False):
                st.write(message["thinking_content"])
                # Ensure complexity metrics are displayed correctly
                with st.container():
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            "Query Complexity",
                            f"{message['complexity_score']:.2f}"
                        )
                    with col2:
                        st.metric(
                            "Thinking Limit",
                            f"{message['thinking_limit']} tokens"
                        )

# Custom metric outputter.
def custom_metric(label, value):
    html = f"""
    <div style="text-align: center; padding: 10px;">
        <div style="color: #5e5e5e; font-size: 0.9rem; margin-bottom: 5px;">{label}</div>
        <div style="color: #8a8787; font-size: 1.0rem; font-weight: bold;">{value}</div>
    </div>
    """
    return html

def send_data():
    st.session_state["prompt"] = st.session_state["value_dynamic"]
    st.session_state.render_inc += 1
    st.session_state.keyup_key = f"ku{st.session_state.render_inc}"
        
    # Clear the input value
    st.session_state["value_dynamic"] = ""

# Chat input container (with keyup to provide custom funcitonality)
with bottom():
    value = st_keyup_chat(label="What would you like to discuss today?", debounce=250, key=st.session_state.keyup_key)
    st.session_state["value_dynamic"] = value
    st.button("Submit", on_click = send_data)

prompt = ""
if st.session_state["prompt"] != "":
    prompt = st.session_state["prompt"]

# Update session state
st.session_state.last_query = prompt

# Calculate complexity for the new prompt
curr_complexity = analyze_complexity(value)
curr_thinking_limit = get_thinking_limit(curr_complexity)

if prompt:
    complexity_score = analyze_complexity(prompt)
    thinking_limit = get_thinking_limit(complexity_score)
    
    st.session_state.live_complexity = complexity_score
    st.session_state.live_thinking_limit = thinking_limit
else:
    # Use existing values if they exist, otherwise use defaults
    if "live_complexity" not in st.session_state:
        st.session_state.live_complexity = 0.0
    if "live_thinking_limit" not in st.session_state:
        st.session_state.live_thinking_limit = 1024


with bottom():
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                custom_metric("Complexity Rating", f"{curr_complexity:.2f}"), 
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                custom_metric("Thinking Limit", f"{curr_thinking_limit} tokens"), 
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                custom_metric("Last Query Complexity", f"{st.session_state.live_complexity:.2f}"), 
                unsafe_allow_html=True
            )

        with col4:
            st.markdown(
                custom_metric("Last Thinking Limit", f"{st.session_state.live_thinking_limit} tokens"), 
                unsafe_allow_html=True
            )

if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", 
                                      "content": prompt
                                      })

    # Display user message
    with st.chat_message("user"):
        st.write(prompt)

    # In the if prompt: block, modify the streaming section
    with st.chat_message("assistant"):
        expander = st.expander("Assistant is thinking...", expanded=True)
        st.session_state.current_thinking = []  # Reset thinking content

        client = get_claude_client()
        start_time = time.time()

        with client.messages.stream(
            model="claude-3-7-sonnet-20250219",
            max_tokens=8192,
            temperature=1,
            system=f"""You are an AI assistant with a specific thinking token limit of {st.session_state.live_thinking_limit}.
                        Carefully consider the user's request but optimize for efficient responses.""",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            thinking={"type": "enabled", "budget_tokens": st.session_state.live_thinking_limit},
        ) as raw_stream:
            raw_stream1, raw_stream2 = itertools.tee(raw_stream, 2)
            think_stream = stream_thinking(raw_stream1)
            text_stream = stream_text(raw_stream2)

            expander.write_stream(think_stream)
            response = st.write_stream(text_stream)

        # Combine all thinking content
        thinking_content = "\n".join(st.session_state.current_thinking)

        # Add assistant response to chat history with metadata
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
                "thinking_content": thinking_content,
                "complexity_score": st.session_state.live_complexity,
                "thinking_limit": st.session_state.live_thinking_limit
            }
        )
    st.session_state.prompt = ""

# Add sidebar information and show last query stats
with st.sidebar:
    st.title("About")
    st.info("""
    This demo showcases dynamic thinking limits for Claude 3.7.
    
    The app uses a basic NLP heuristic to evaluate query complexity
    and sets the thinking limit accordingly.
    """)
