"""Style variator: anti-repetition and tone consistency."""
import hashlib
import re
from collections import Counter

from services.narrative.synonyms import SYNONYMS


def vary_style(text: str, seed: int = 0, used_words: list[str] | None = None) -> str:
    """
    Apply synonym substitution to reduce word repetition.
    Returns varied text.
    """
    if not text:
        return text

    used_words = used_words or []
    words = text.split()

    # Track word frequency in this block
    word_freq = Counter(w.lower().strip(".,!?;:") for w in words)

    result_words = []
    for word in words:
        clean = word.lower().strip(".,!?;:")
        # If word is overused (appears 3+ times) and has synonyms, substitute
        if word_freq[clean] >= 2 and clean in SYNONYMS:
            synonyms = [s for s in SYNONYMS[clean] if s != clean and s not in used_words]
            if synonyms:
                h = int(hashlib.md5((clean + str(seed)).encode()).hexdigest(), 16)
                replacement = synonyms[h % len(synonyms)]
                # Preserve capitalization
                if word[0].isupper():
                    replacement = replacement.capitalize()
                # Preserve punctuation
                if word[-1] in ".,!?;:":
                    replacement = replacement + word[-1]
                result_words.append(replacement)
                word_freq[clean] -= 1
                continue
        result_words.append(word)

    return " ".join(result_words)


def ensure_tone(text: str, tone: str) -> str:
    """
    Adjust text phrasing to match a desired tone.
    Minimal transformation — mostly capitalization and hedging.
    """
    if tone == "concerned":
        # Add hedging words for warnings
        text = re.sub(r"\bshould\b", "must", text, count=1)
    elif tone == "celebratory":
        # No transformation needed
        pass
    return text
