from thought_params import ThoughtParameters

# Function to calculate thinking limit based on complexity
def get_thinking_limit(complexity):
    if complexity < 0.3:
        return ThoughtParameters.QUICK.value["budget_tokens"]  # Simple queries
    elif complexity < 0.6:
        return ThoughtParameters.BALANCED.value["budget_tokens"]  # Moderate complexity
    else:
        return int(complexity * 16000)  # Complex queries

# Custom metric for stats display
def custom_metric(label, value):
    html = f"""
    <div style="text-align: center; padding: 10px;">
        <div style="color: #5e5e5e; font-size: 0.9rem; margin-bottom: 5px;">{label}</div>
        <div style="color: #8a8787; font-size: 1.0rem; font-weight: bold;">{value}</div>
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

