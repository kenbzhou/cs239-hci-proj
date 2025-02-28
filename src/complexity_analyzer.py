import nltk
from nltk.corpus import stopwords

# Download necessary NLTK data
try:
    nltk.data.find("tokenizers/punkt")
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("punkt")
    nltk.download("stopwords")

# Cache stopwords for better performance
STOP_WORDS = set(stopwords.words("english"))
COMMAND_INDICATORS = [
    "explain",
    "describe",
    "analyze",
    "compare",
    "list",
    "summarize",
    "evaluate",
    "create",
    "design",
    "implement",
]


def analyze_complexity(text):
    """
    Analyze the complexity of a user query and return a score between 0 and 1.

    Parameters:
    text (str): The user's query text

    Returns:
    float: Complexity score between 0 and 1
    """
    if not text or len(text.strip()) == 0:
        return 0.0

    # Convert to lowercase for analysis
    text = text.lower()

    # Tokenize
    words = nltk.word_tokenize(text)
    sentences = nltk.sent_tokenize(text)

    # Filter out stopwords
    content_words = [
        word for word in words if word.isalnum() and word not in STOP_WORDS
    ]

    # Calculate metrics

    # 1. Length-based metrics
    length_score = min(len(words) / 100, 1.0)  # Normalize by 100 words

    # 2. Lexical diversity (unique words / total words)
    unique_words = set(content_words)
    lexical_diversity = len(unique_words) / max(len(words), 1)

    # 3. Sentence complexity
    avg_sentence_length = len(words) / max(len(sentences), 1)
    sentence_complexity = min(
        avg_sentence_length / 20, 1.0
    )  # Normalize by 20 words per sentence

    # 4. Question complexity
    question_count = text.count("?")
    question_score = min(question_count / 3, 1.0)  # Normalize by 3 questions

    # 5. Command/directive indicators
    command_count = sum(1 for word in words if word in COMMAND_INDICATORS)
    command_score = min(command_count / 2, 1.0)  # Normalize by 2 commands

    # 6. Complex word indicators (longer words tend to be more complex)
    complex_word_count = sum(1 for word in content_words if len(word) > 8)
    complex_word_score = min(
        complex_word_count / 5, 1.0
    )  # Normalize by 5 complex words

    # Calculate weighted average
    weights = {
        "length": 0.3,
        "lexical_diversity": 0.2,
        "sentence_complexity": 0.15,
        "question": 0.15,
        "command": 0.1,
        "complex_word": 0.1,
    }

    complexity_score = (
        weights["length"] * length_score
        + weights["lexical_diversity"] * lexical_diversity
        + weights["sentence_complexity"] * sentence_complexity
        + weights["question"] * question_score
        + weights["command"] * command_score
        + weights["complex_word"] * complex_word_score
    )

    return complexity_score
