"""Sentence stitcher: combines rendered sentences with transitions."""
import re
from services.narrative.transitions import pick_transition


def stitch(sentences: list[str], tone: str = "neutral", seed: int = 0) -> str:
    """
    Combine multiple sentences into a cohesive paragraph.
    tone: neutral | concerned | celebratory | cautionary
    """
    if not sentences:
        return ""
    if len(sentences) == 1:
        return sentences[0]

    # Clean each sentence
    cleaned = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if not s.endswith((".","!","?")):
            s += "."
        cleaned.append(s)

    if not cleaned:
        return ""

    result_parts = [cleaned[0]]

    transition_categories = {
        "neutral": ["additive", "temporal"],
        "concerned": ["causal", "emphasis", "contrast"],
        "celebratory": ["additive", "emphasis"],
        "cautionary": ["condition", "causal", "contrast"],
    }
    cats = transition_categories.get(tone, ["additive"])

    for i, sentence in enumerate(cleaned[1:], 1):
        cat = cats[(i - 1) % len(cats)]
        transition = pick_transition(cat, seed=seed + i)
        # Don't add transition if sentence already starts with a connector
        first_word = sentence.split()[0].lower() if sentence.split() else ""
        connectors = {"however", "additionally", "furthermore", "also", "meanwhile",
                      "notably", "importantly", "consequently", "overall", "that", "this",
                      "at", "in", "on", "as", "because", "since", "while", "although"}
        if first_word in connectors:
            result_parts.append(sentence)
        else:
            result_parts.append(f"{transition} {sentence[0].lower()}{sentence[1:]}")

    return " ".join(result_parts)


def split_into_sentences(text: str) -> list[str]:
    """Split text into individual sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]
