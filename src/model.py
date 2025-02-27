import os

import anthropic
from dotenv import load_dotenv

from message_parser import parse_message
from thought_params import ThoughtParameters

# ToImplement:
#   Message log/history/caching; message sending should maybe not just be singular messages in order to enable
#       a conversational implementation.
#   Heuristic
#   Response Streaming
#   Caching


# Core class behind interaction with Claude
class AnthropicModel:
    # Initialize model and client
    # https://docs.anthropic.com/en/api/getting-started#examples
    def __init__(self):
        load_dotenv()
        self.client = anthropic.Anthropic()
        self.model = "claude-3-7-sonnet-20250219"

    # Public API for interaction with client after user sends message.
    def handle_message(self, message: str):
        thought_params = parse_message(message)
        self._stream_message_response(message, thought_params)

    # Sends message to model + returns output.
    # https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking#streaming-extended-thinking
    def _stream_message_response(self, message: str, thought_params: ThoughtParameters):
        max_token_ct = (
            self._count_message_tokens(message) + thought_params.value["budget_tokens"]
        )
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_token_ct,
            thinking={
                "type": thought_params.value["type"],
                "budget_tokens": thought_params.value["budget_tokens"],
            },
            messages=[{"role": "user", "content": message}],
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    print(f"\nStarting {event.content_block.type} block...")
                elif event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        print(f"Thinking: {event.delta.thinking}", end="", flush=True)
                    elif event.delta.type == "text_delta":
                        print(f"Response: {event.delta.text}", end="", flush=True)
                elif event.type == "content_block_stop":
                    print("\nBlock complete.")

    # Count tokens of input message.
    # https://docs.anthropic.com/en/docs/build-with-claude/token-counting#count-tokens-in-basic-messages
    def _count_message_tokens(self, message: str):
        response = self.client.messages.count_tokens(
            model="claude-3-7-sonnet-20250219",
            messages=[{"role": "user", "content": message}],
        )
        return response.input_tokens
