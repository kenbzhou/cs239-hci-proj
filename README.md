# Claude 3.7 Thinking Demo

This Streamlit application demonstrates how to optimize Claude 3.7's thinking limit based on the complexity of user queries.

## Features

- Chat interface for interacting with Claude 3.7
- Live complexity analysis with debounced updates as you type
- Dynamic thinking limits based on query complexity analysis
- Real-time metrics on query complexity and response time
- Visualization of thinking parameters

## Setup

1. Clone this repository
2. Install `uv` if you don't have it: [instructions](https://docs.astral.sh/uv/getting-started/installation/)
3. Create a venv
   ```
   uv venv
   ```
4. Install dependencies:
   ```
   uv sync
   ```
5. Install custom component into src directory
   ```
   cd src
   git clone https://github.com/kenbzhou/streamlit-keyup
   ```

6. Set up your Claude API key:
   - Create a `.streamlit/secrets.toml` file with:
     ```
     ANTHROPIC_API_KEY = "your-api-key-here"
     ```

7. Run the application:
   ```
   streamlit run src/app.py
   ```

## How It Works

The application uses a basic NLP heuristic to evaluate the complexity of user queries based on several factors:

- Text length
- Lexical diversity
- Sentence complexity
- Number of questions
- Presence of commands/directives
- Complex word usage

Based on the calculated complexity score (0-1), the app sets one of three thinking limits:
- Simple queries (< 0.3): 1000 tokens
- Moderate complexity (0.3-0.6): 2000 tokens
- Complex queries (> 0.6): 4000 tokens

### Live Complexity Analysis

As you type your query, the app provides real-time feedback on the complexity score and the corresponding thinking limit. This analysis is debounced to ensure smooth performance, updating approximately 0.5 seconds after you stop typing.

## Research Purpose

This demo is part of a research project exploring the balance between response quality and latency in large language models. By dynamically adjusting thinking limits, we aim to optimize the user experience by providing appropriately detailed responses while maintaining reasonable response times.
