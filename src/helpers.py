import plotly.graph_objects as go

from thought_params import ThoughtParameters


# Function to calculate thinking limit based on complexity
def get_thinking_limit(complexity):
    if complexity < 0.3:
        return ThoughtParameters.QUICK.value["budget_tokens"]  # Simple queries
    elif complexity < 0.6:
        return ThoughtParameters.BALANCED.value["budget_tokens"]  # Moderate complexity
    else:
        return int(complexity * 16000)  # Complex queries


def map_manual_thinking(complexity: str):
    """
    Maps a manual thinking setting from the UI to a complexity score

    Args:
        complexity (str): Manual thinking setting, one of
            ["Quick", "Speedy", "Balanced", "Thorough", "Deep"]

    Returns:
        float: Complexity score between 0.0 and 1.0
    """

    mappings = {
        "Quick": 0.05,
        "Speedy": 0.25,
        "Balanced": 0.50,
        "Thorough": 0.75,
        "Deep": 1.00,
    }
    return mappings[complexity]


# Custom metric for stats display
def custom_metric(label, emoji, value):
    html = f"""
        <div style="text-align: center; padding: 10px;">
            <div style="color: #5e5e5e; font-size: 0.9rem; margin-bottom: 5px;">{label}</div>
            <div style="font-size: 2rem;">{emoji}</div>
            <div style="color: #8a8787; font-size: 0.8rem;">{value}</div>
        </div>
        """
    return html


# Process thought and response stream
def process_stream(stream, thinking_container, response_container):
    response_chunks = []
    thinking_chunks = []

    for event in stream:
        if event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                thinking_chunks.append(event.delta.thinking)
                # Update thinking container in real-time
                thinking_container.markdown("".join(thinking_chunks))
            elif event.delta.type == "text_delta":
                response_chunks.append(event.delta.text)
                # Update response container in real-time
                response_container.markdown("".join(response_chunks))

    return "".join(response_chunks), "".join(thinking_chunks)


# Custom metric outputter.
def create_radial_gauge(complexity_score, title="Complexity Score"):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            title=title,
            value=round(complexity_score, 2),
            gauge={
                "axis": {"range": [0, 1], "tickwidth": 1},
                "bar": {"color": "darkgray"},
                "steps": [
                    {"range": [0, 0.3], "color": "lightgreen"},
                    {"range": [0.3, 0.6], "color": "yellow"},
                    {"range": [0.6, 0.8], "color": "orange"},
                    {"range": [0.8, 1], "color": "red"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.75,
                    "value": complexity_score,
                },
            },
        )
    )

    fig.update_layout(
        height=235,
    )
    return fig
