import time
from pathlib import Path

import anthropic
import streamlit as st
import streamlit.components.v1 as components

# from st_keyup import st_keyup
from streamlit_extras.bottom_container import bottom

# from streamlit_extras.stylable_container import stylable_container
from complexity_analyzer import analyze_complexity
from helpers import (
    create_radial_gauge,
    custom_metric,
    get_thinking_limit,
    map_manual_thinking,
    process_stream,
)
from thought_params import ThoughtParameters, get_thinking_emoji

build_dir = Path(__file__).parent.absolute() / "components" / "keyup"
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

# Landing page
if "show_landing" not in st.session_state:
    st.session_state.show_landing = True

# Client Key
if "client_key" not in st.session_state:
    st.session_state.client_key = None


### Functions unable to be moved to helper due to dependency on streamlit state.
# Initialize Claude client (you'll need an API key)
@st.cache_resource
def get_claude_client():
    if st.session_state.client_key is None:
        st.warning("Please enter an API key to continue")
        st.stop()
    key = st.session_state.client_key
    if not key:
        st.warning("API key cannot be empty")
        st.stop()

    return anthropic.Anthropic(api_key=key)


def send_data():
    st.session_state["prompt"] = st.session_state["value_dynamic"]
    st.session_state.render_inc += 1
    st.session_state.keyup_key = f"ku{st.session_state.render_inc}"

    # Clear the input value
    st.session_state["value_dynamic"] = ""


@st.fragment
def slider_impl(enabled: bool):
    st.session_state.slider_complexity = st.select_slider(
        "Select a thought budget:",
        options=[
            "Quick",
            "Speedy",
            "Balanced",
            "Thorough",
            "Deep",
        ],
        value="Balanced",
        disabled=not enabled,
    )


def render_landing():
    landing = st.container()

    st.session_state.client_key = st.secrets.get("ANTHROPIC_API_KEY", None)

    with landing:
        st.title("Welcome to Claude Sonnet 3.7++: Wholly Spearmint Edition!")
        st.write("""
                 Thank you for trying our product! 
                 
                 The Wholly Spearmint edition of Claude 3.7 hopes to provide to you a FRESH experience tailored to your querying needs, where we optimize the latency and depth of our answers to the complexity of your queries!
                 
                 """)
        st.write("## Our key features:")
        st.info(
            """### Query Complexity Scoring:  \n   - Based on the structure and content of your questions, we will automatically determine how complex your queries are.  \n   - This will be reflected as a 'Complexity Score' from 0.00 to 1.00, and will help inform the model how much it is allowed to think about your question."""
        )
        st.info(
            """### Thinking Limit Settings:  \n   - Based on how complex your question is, our chatbot will automatically determine how much it is allowed to 'think' about your questions.  \n   - Higher levels of thinking may result in better answers, but will also mean higher wait-times that are not always compatible with less complex queries. \n   -  We will communicate a raw 'thinking limit' score that corresponds to the maximum amount a model is allowed to think about the question; keep in mind that the model may not always hit this limit."""
        )
        st.info(
            """### Thinking Limit Manual Configuration:  \n   - Should you desire a higher thinking level for your queries, our sidebar allows you to manually tune the complexity score of your question.  \n   - Simply tick the toggle on the sidebar and slide the complexity score to the level you desire. \n   -  Our app will automatically map your configured complexity score to a thinking limit; keep in mind that the model will still understand that simpler queries require less thinking."""
        )
        st.info(
            """### Statistical History:  \n   - For each question you send: its query complexity, thinking limit, and the time it took for the full response will automatically be shown in the thinking response.  \n   - As the complexity scores and thinking limits ebb and flow, we hope that you see differences in response quality, detail, and latency that are tailored to your experience!"""
        )
        # fetch_client_key_field()
        if st.session_state.client_key is None:
            with st.form("my_form"):
                st.write("### Ready to get started?")
                st.write("Input your Anthropic Claude API Key below!")
                key_val = st.text_input("Enter your Anthropic Key...")

                # Every form must have a submit button.
                submitted = st.form_submit_button("Submit")
                if submitted:
                    st.session_state.client_key = key_val
                    st.session_state.show_landing = False
                    time.sleep(0.5)
                    st.rerun()
        else:
            st.write("### Ready to get started?")
            if st.button("## Get Started"):
                st.session_state.show_landing = False
                st.rerun()


def render_app():
    # Display chat history and thinking details
    st.title("Claude Sonnet 3.7+: Wholly Spearmint Edition")
    # Replace the existing message display loop
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "thinking_content" in message:
                # Inline chat complexity in "thought" container
                with st.expander("Thinking Process", expanded=False):
                    st.write(message["thinking_content"])
                    # Ensure complexity metrics are displayed correctly
                    with st.container():
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            emoji = get_thinking_emoji(message["thinking_limit"])

                            st.metric(
                                "Complexity Score",
                                f"{emoji}: {message['complexity_score'] * 100:.2f}/100",
                            )
                        with col2:
                            st.metric(
                                "Thinking Limit", f"{message['thinking_limit']} tokens"
                            )
                        with col3:
                            st.metric("Latency", f"{round(message['latency'], 1)} secs")

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
        else map_manual_thinking(st.session_state.slider_complexity)
    )
    curr_thinking_limit = get_thinking_limit(curr_complexity)

    if prompt:
        complexity_score = (
            analyze_complexity(prompt)
            if not st.session_state.manual_thinking
            else map_manual_thinking(st.session_state.slider_complexity)
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
                st.plotly_chart(
                    create_radial_gauge(
                        curr_complexity, title="Current Query Complexity"
                    ),
                    use_container_width=True,
                    key="bottom_gauge",
                )

            with col2:
                emoji = get_thinking_emoji(curr_thinking_limit)
                st.markdown(
                    custom_metric(
                        "Thinking Budget", emoji, f"{curr_thinking_limit} tokens"
                    ),
                    unsafe_allow_html=True,
                )

            with col3:
                st.plotly_chart(
                    create_radial_gauge(
                        st.session_state.live_complexity, title="Last Query Complexity"
                    ),
                    use_container_width=True,
                    key="bottom_gauge2",
                )

            with col4:
                emoji = get_thinking_emoji(st.session_state.live_thinking_limit)
                st.markdown(
                    custom_metric(
                        "Previous Thinking Budget",
                        emoji,
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
                system=f"""You are an AI assistant with a thinking token limit of {st.session_state.live_thinking_limit} that is heuristically assigned based on the complexity of the user's query, which has been determined to be {st.session_state.live_complexity}.
                            For low complexity queries (where thinking limit < 1200):
                            - Ideally use minimal thinking tokens, unless required.
                            - Provide concise, direct responses
                            - Avoid unnecessary elaboration
                            - Focus on answering exactly what was asked

                            For medium complexity queries (where thinking limit is 1200-6000, complexity > 0.3):
                            - Ideally use at least a moderate portion of your thinking budget, unless a deviation is required.
                            - Balance depth with efficiency
                            - Provide supporting details where valuable
                            - Show clear reasoning for your conclusions

                            For high complexity queries (where thinking limit > 6000, complexity > 0.7):
                            - Utilize most of your thinking budget
                            - Demonstrate sophisticated analysis and insight
                            - Consider multiple perspectives and edge cases
                            - Provide comprehensive, nuanced responses
                            - Show depth of reasoning that reflects your extended thinking

                            In all queries that are at least 'medium complexity', your thinking should uphold and include:
                            - extensive insight into your thought process, such that a human can understand and work through how you are arriving to your conclusions.
                            - mentions of examples that inform your thought processes, though not so much as to clutter your thoughts with information generally unrelated to the user's query.
                            - extensive consideration of the human's query, such that the true meaning and purpose behind the query is understood.
                            - a lack of 'explicit mentions' of complexity score. Higher level references, such as 'this is a high complexity prompt', are ok; but explicit mentions of numbers are not.

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
                    "latency": elapsed,
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
        st.title("Need Help?")
        st.info("""
                For a refresh on the various aspects of our product, press the button below to go back to the landing page! 
                
                (Don't worry, your progress is saved.)
                """)
        if st.button("## Back to Landing"):
            st.session_state.show_landing = True
            st.rerun()

        st.title("Manual Settings")

        st.session_state.manual_thinking = st.toggle(
            "Override Thinking Depth?", value=False
        )
        slider_impl(enabled=st.session_state.manual_thinking)


if st.session_state.show_landing:
    render_landing()
else:
    render_app()
