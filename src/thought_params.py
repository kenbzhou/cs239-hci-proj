from enum import Enum


# Defines the heuristics that the parser will categorize user prompts as, as well as the thinking parameter for each heuristic.
class ThoughtParameters(Enum):
    INSTANT = {
        "type": "disabled",
        "budget_tokens": 0,
    }  # TODO: thinking type cannot be 'disabled'; must neglect thinking block.
    QUICK = {"type": "enabled", "budget_tokens": 1024}  # min budget allowed
    BALANCED = {"type": "enabled", "budget_tokens": 4500}
    THOROUGH = {"type": "enabled", "budget_tokens": 8000}
    DEEP = {"type": "enabled", "budget_tokens": 16000}


def get_thinking_emoji(tokens):
    if tokens == 0:
        return "🤫"  # Silent/no thinking
    elif tokens <= 1024:
        return "💭"  # Quick thought
    elif tokens <= 4500:
        return "🤔"  # Moderate thinking
    elif tokens <= 8000:
        return "🧐"  # Detailed analysis
    else:
        return "🤯"  # Deep thinking
