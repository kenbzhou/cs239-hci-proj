import time
from pathlib import Path

import anthropic
import streamlit as st
import streamlit.components.v1 as components
from st_keyup import st_keyup
from streamlit_extras.bottom_container import bottom
from streamlit_extras.stylable_container import stylable_container

from complexity_analyzer import analyze_complexity
from thought_params import ThoughtParameters
from helpers import get_thinking_limit, custom_metric, process_stream

build_dir = (
    Path(__file__).parent.absolute()
    / "streamlit-keyup"
    / "src"
    / "st_keyup"
    / "frontend"
)
st_keyup_chat = components.declare_component("st_keyup_chat", path=str(build_dir))

# Set page config
st.set_page_config(page_title="CS Dubz", page_icon="🧠", layout="wide")

# Set up session states.

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

# Evil rerendering hack to automatically clear input field.
if "render_inc" not in st.session_state:
    st.session_state.render_inc = 0
if "keyup_key" not in st.session_state:
    st.session_state.keyup_key = f"ku{st.session_state.render_inc}"

# Slider var
if "slider_complexity" not in st.session_state:
    st.session_state.slider_complexity = "Automatic"

if "manual_thinking" not in st.session_state:
    st.session_state.manual_thinking = False

### Functions unable to be moved to helper due to dependency on streamlit state.
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

def send_data():
    st.session_state["prompt"] = st.session_state["value_dynamic"]
    st.session_state.render_inc += 1
    st.session_state.keyup_key = f"ku{st.session_state.render_inc}"

    # Clear the input value
    st.session_state["value_dynamic"] = ""

@st.fragment
def slider_impl():
    st.session_state.slider_complexity = st.slider(
        "Select a thought budget:",
        min_value=0.0,
        max_value=1.0,
        value=0.5,  # Default value
        step=0.01,
        format="%.2f",  # Ensures two decimal places
        #label_visibility="hidden"
    )


# Display chat history and thinking details
st.title("Claude Sonnet 3.7+: Wholly Spearmint Edition")
# Replace the existing message display loop
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "thinking_content" in message:
            with st.expander("Thinking Process", expanded=False):
                st.write(message["thinking_content"])
                # Ensure complexity metrics are displayed correctly
                with st.container():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Query Complexity", f"{message['complexity_score']:.2f}"
                        )
                    with col2:
                        st.metric(
                            "Thinking Limit", f"{message['thinking_limit']} tokens"
                        )
                    with col3:
                        st.metric(
                            "Latency", f"{round(message['latency'],1)} secs"
                        )

# Chat input container (with keyup to provide custom funcitonality)
with bottom():
    value = st_keyup_chat(
        label="What would you like to discuss today?",
        debounce=250,
        key=st.session_state.keyup_key,
    )
    st.session_state["value_dynamic"] = value
    st.button("Submit", on_click=send_data)

prompt = ""
if st.session_state["prompt"] != "":
    prompt = st.session_state["prompt"]

# Update session state
st.session_state.last_query = prompt

# Calculate complexity for the new prompt
curr_complexity = (
    analyze_complexity(value)
    if not st.session_state.manual_thinking
    else st.session_state.slider_complexity
)
curr_thinking_limit = get_thinking_limit(curr_complexity)

if prompt:
    complexity_score = (
        analyze_complexity(prompt)
        if not st.session_state.manual_thinking
        else st.session_state.slider_complexity
    )
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
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                custom_metric("Thinking Limit", f"{curr_thinking_limit} tokens"),
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                custom_metric(
                    "Last Query Complexity", f"{st.session_state.live_complexity:.2f}"
                ),
                unsafe_allow_html=True,
            )

        with col4:
            st.markdown(
                custom_metric(
                    "Last Thinking Limit",
                    f"{st.session_state.live_thinking_limit} tokens",
                ),
                unsafe_allow_html=True,
            )


if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.write(prompt)

    # In the if prompt: block, modify the streaming section
    with st.chat_message("assistant"):
        thinking_expander = st.expander("Assistant is thinking...", expanded=True)
        thinking_container = thinking_expander.empty()
        response_container = st.empty()

        client = get_claude_client()
        start_time = time.time()

        with client.messages.stream(
            model="claude-3-7-sonnet-20250219",
            max_tokens=20092,
            temperature=1,
            system = f"""You are an AI assistant with a thinking token limit of {st.session_state.live_thinking_limit} that is heuristically assigned based on the complexity of the user's query, which has been determined to be {st.session_state.live_complexity}.
                        For low complexity queries (where thinking limit < 1200):
                        - Ideally use minimal thinking tokens, unless required.
                        - Provide concise, direct responses
                        - Avoid unnecessary elaboration
                        - Focus on answering exactly what was asked

                        For medium complexity queries (where thinking limit is 1200-6000, complexity > 0.3):
                        - Ideally use a moderate portion of your thinking budget, unless a deviation is required.
                        - Balance depth with efficiency
                        - Provide supporting details where valuable
                        - Show clear reasoning for your conclusions

                        For high complexity queries (where thinking limit > 6000, complexity > 0.7):
                        - Utilize most of your thinking budget
                        - Demonstrate sophisticated analysis and insight
                        - Consider multiple perspectives and edge cases
                        - Provide comprehensive, nuanced responses
                        - Show depth of reasoning that reflects your extended thinking

                        Your response quality and depth should scale proportionally with your thinking budget. As the thinking limit increases, users expect to see increasingly insightful, thorough, and intelligent responses that clearly reflect the additional cognitive resources applied to their query.

                        Never explicitly mention the complexity score of the query. Feel free to mention the high-level complexity of the query, however.

                        Always prioritize being informative and helpful at all complexity levels, while adjusting your response depth to match the assigned thinking resources. If users indicate a desire for more depth, be responsive by using more of your thinking budget.""",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            thinking={"type": "enabled", "budget_tokens": thinking_limit},
        ) as stream:
            response, thinking_content = process_stream(
                stream, thinking_container, response_container
            )
        elapsed = time.time() - start_time
        # Combine all thinking content
        # Add assistant response to chat history with metadata
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response,
                "thinking_content": thinking_content,
                "complexity_score": st.session_state.live_complexity,
                "thinking_limit": st.session_state.live_thinking_limit,
                "latency": elapsed
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
    st.title("Manual Settings")
    slider_impl()
    st.session_state.manual_thinking = st.toggle("Manually set Thought Budget?", value=False)


