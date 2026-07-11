"""Transition phrase library for connecting narrative sentences."""
import random

ADDITIVE = [
    "Additionally,", "Furthermore,", "On top of that,", "Also,",
    "Beyond that,", "What's more,",
]

CONTRAST = [
    "However,", "On the other hand,", "In contrast,", "That said,",
    "Despite this,", "At the same time,",
]

CAUSAL = [
    "As a result,", "Consequently,", "This means", "Which explains why",
    "Because of this,", "This drives",
]

TEMPORAL = [
    "Meanwhile,", "Over this period,", "During the same time,",
    "Looking ahead,", "In the coming months,",
]

EMPHASIS = [
    "Notably,", "Importantly,", "Worth highlighting,",
    "In particular,", "Crucially,",
]

SUMMARY = [
    "Overall,", "Taken together,", "In summary,", "On balance,",
    "All things considered,", "The net picture is",
]

CONDITION = [
    "If this trend continues,", "Should spending stay flat,",
    "At the current pace,", "Assuming no change,",
]


def pick_transition(category: str = "additive", seed: int | None = None) -> str:
    rng = random.Random(seed)
    mapping = {
        "additive": ADDITIVE, "contrast": CONTRAST, "causal": CAUSAL,
        "temporal": TEMPORAL, "emphasis": EMPHASIS, "summary": SUMMARY,
        "condition": CONDITION,
    }
    pool = mapping.get(category, ADDITIVE)
    return rng.choice(pool)
