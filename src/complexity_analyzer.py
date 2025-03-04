import re
import string
import textstat

# ---- Lexical Metrics ----
def type_token_ratio(text: str) -> float:
    """Returns the type-token ratio (lexical diversity)."""
    words = re.findall(r'\w+', text.lower())
    return len(set(words)) / len(words) if words else 0

# ---- Simple Readability Metric (Approximate Flesch-Kincaid) ----
def simple_flesch_kincaid(text: str) -> float:
    """
    Computes an approximate Flesch-Kincaid grade using:
      - Word count
      - Sentence count (based on punctuation)
      - A naive syllable count (by counting groups of vowels)
    """
    sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]
    words = re.findall(r'\w+', text)
    word_count = len(words)
    sentence_count = len(sentences) if sentences else 1

    vowels = "aeiouy"
    syllable_count = 0
    for word in words:
        word = word.lower()
        count = 0
        prev_vowel = False
        for char in word:
            if char in vowels:
                if not prev_vowel:
                    count += 1
                    prev_vowel = True
            else:
                prev_vowel = False
        syllable_count += count if count > 0 else 1

    # Simplified Flesch-Kincaid formula:
    if word_count != 0:
        grade = 0.39 * (word_count / sentence_count) + 11.8 * (syllable_count / word_count) - 15.59
    else:
        grade = 0
    return grade

# ---- Additional Metric: Punctuation Density ----
def punctuation_density(text: str) -> float:
    """
    Computes punctuation density as the ratio of punctuation marks to the number of words.
    A higher value can indicate more complex sentence structures.
    """
    punct_count = sum(1 for char in text if char in string.punctuation)
    words = re.findall(r'\w+', text)
    word_count = len(words)
    return punct_count / word_count if word_count else 0

# ---- Overall Complexity Heuristic with Additional Textstat Metrics ----
def analyze_complexity(question: str) -> float:
    """
    Computes a complexity score for a question using:
      - Lexical metrics: type-token ratio and average word length.
      - Readability metrics: a simple Flesch-Kincaid grade, Gunning Fog index, and SMOG index.
      - Punctuation density metric.
    
    Each component is normalized to a 0–1 scale (assuming typical ranges), and the overall score is the average.
    
    Returns a value between 0 and 1.
"""
    if not question:
        return 0.0
    question = question.strip()

    # --- Lexical Metrics ---
    words = re.findall(r'\w+', question.lower())
    word_count = len(words)
    avg_word_len = sum(len(word) for word in words) / word_count if word_count else 0
    ttr = type_token_ratio(question)
    
    # Normalize type-token ratio (typical range 0.3 to 1.0)
    norm_ttr = max(0, min(1, (ttr - 0.3) / 0.7))
    # Normalize average word length (assuming a range of 3 to 10 letters)
    norm_avg_word_len = max(0, min(1, (avg_word_len - 3) / 7))
    lexical_score = (norm_ttr + norm_avg_word_len) / 2.0

    # --- Readability Metrics ---
    # Simple Flesch-Kincaid Grade (custom)
    fk_grade = simple_flesch_kincaid(question)
    norm_fk = max(0, min(1, fk_grade / 20))  # Assuming grade level 0-20

    # Gunning Fog Index via textstat
    gf_grade = textstat.gunning_fog(question)
    norm_gf = max(0, min(1, gf_grade / 20))  # Normalized assuming a range of 0-20

    # SMOG Index via textstat
    smog_grade = textstat.smog_index(question)
    norm_smog = max(0, min(1, smog_grade / 20))  # Normalized assuming a range of 0-20

    # --- Punctuation Density Metric ---
    punc_density = punctuation_density(question)
    norm_punc = max(0, min(1, punc_density / 0.2))  # Assume 0.2 is a high density

    # --- Combine All Components ---
    #overall_complexity = (lexical_score + norm_fk + norm_gf + norm_smog + norm_punc) / 5.0
    overall_complexity = .15*lexical_score + .2*norm_fk + .3*norm_gf + .3*norm_smog + .05*norm_punc
    return max(0, min(1, overall_complexity))

# ---- Example Usage ----
if __name__ == "__main__":
    test = (
        "Given the integral of sin(x) over the interval from 0 to π/2, "
        "explain how this relates to the probability density function of a Beta distribution "
        "and provide a proof using both integration by parts and substitution methods."
    )

    test2 = "hello there!"

    
    
    score = analyze_complexity(test)
    print("Complexity Score 1:", score)

    score = analyze_complexity(test2)
    print("Complexity Score 1:", score)
