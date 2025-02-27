import time

import anthropic
import streamlit as st

from complexity_analyzer import analyze_complexity

# Set page config
st.set_page_config(page_title="Claude 3.7 Thinking Demo", page_icon="🧠")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm Claude. How can I help you today?"}
    ]

if "current_query" not in st.session_state:
    st.session_state.current_query = ""

if "last_calculation_time" not in st.session_state:
    st.session_state.last_calculation_time = 0

if "live_complexity" not in st.session_state:
    st.session_state.live_complexity = 0.0

if "live_thinking_limit" not in st.session_state:
    st.session_state.live_thinking_limit = 1000


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


# Function to calculate thinking limit based on complexity
def get_thinking_limit(complexity):
    if complexity < 0.3:
        return 1000  # Simple queries
    elif complexity < 0.6:
        return 2000  # Moderate complexity
    else:
        return 4000  # Complex queries


# Display chat history
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
live_metrics = st.container()

# Query input with live complexity analysis
query = st.text_area(
    "Type your query:",
    value=st.session_state.current_query,
    height=100,
    key="query_input",
)

# Update live complexity with debouncing (only recalculate after 0.5 seconds of no changes)
current_time = time.time()
if query != st.session_state.current_query:
    st.session_state.current_query = query
    # Debounce by checking if enough time has passed since last calculation
    if current_time - st.session_state.last_calculation_time > 0.5 and query.strip():
        st.session_state.live_complexity = analyze_complexity(query)
        st.session_state.live_thinking_limit = get_thinking_limit(
            st.session_state.live_complexity
        )
        st.session_state.last_calculation_time = current_time

# Display live complexity metrics
with live_metrics:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Live Complexity Score", f"{st.session_state.live_complexity:.2f}")
    with col2:
        st.metric(
            "Estimated Thinking Limit", f"{st.session_state.live_thinking_limit} tokens"
        )

# Submit button for the query
if st.button("Submit Query") and query.strip():
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": query})

    # Display user message
    with st.chat_message("user"):
        st.write(query)

    # We've already calculated the complexity, so use that
    complexity_score = st.session_state.live_complexity
    thinking_limit = st.session_state.live_thinking_limit

    # Display response with a spinner
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            client = get_claude_client()
            import time

            start_time = time.time()

            # Call Claude API with the determined thinking limit
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1000,
                temperature=0.7,
                system=f"""You are an AI assistant with a specific thinking token limit of {thinking_limit}.
                           Carefully consider the user's request but optimize for efficient responses.""",
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
            )

            thinking_time = time.time() - start_time
            assistant_response = response.content[0].text

            # Display the response
            st.write(assistant_response)

    # Add assistant response to chat history with metadata
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_response,
            "complexity_score": complexity_score,
            "thinking_limit": thinking_limit,
            "thinking_time": thinking_time,
        }
    )

    # Clear current query after sending
    st.session_state.current_query = ""
    # Trigger rerun to reset the text area
    st.rerun()

    # Display complexity metrics in the sidebar
    with st.sidebar:
        st.subheader("Last Query Stats")
        st.write(f"Complexity Score: {complexity_score:.2f}")
        st.write(f"Thinking Limit: {thinking_limit} tokens")
        st.write(f"Response Time: {thinking_time:.2f} seconds")

# Add sidebar information
with st.sidebar:
    st.title("About")
    st.info("""
    This demo showcases dynamic thinking limits for Claude 3.7.
    
    The app uses a basic NLP heuristic to evaluate query complexity
    and sets the thinking limit accordingly. Watch the live complexity
    score change as you type your query!
    """)
