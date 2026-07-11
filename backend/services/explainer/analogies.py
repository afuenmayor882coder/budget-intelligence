"""Reusable analogy library for deep-dive explanations."""

ANALOGIES = {
    "stationarity": (
        "Imagine a rubber band. Stationary series are like a taut rubber band — they always "
        "return to a resting length. Non-stationary series are like a balloon drifting away — "
        "each new value can wander further from where it started."
    ),
    "cointegration": (
        "Two dogs on a leash. Each dog can wander individually, but the leash means they can't "
        "get too far apart. Cointegration is the leash between official and parallel rates — "
        "policy pressures keep pulling them toward each other."
    ),
    "granger": (
        "Granger causality is like asking: 'If I knew yesterday's weather, would I predict "
        "today's better?' It doesn't prove true causation, only useful predictive lead-lag."
    ),
    "irf": (
        "Imagine dropping a stone in a pond. The initial splash is the shock, and the ripples "
        "are how the shock spreads through the system over time. IRFs show these ripples."
    ),
    "garch": (
        "Volatility comes in clusters — calm periods and stormy periods. GARCH models detect "
        "which mode we're in right now."
    ),
    "forecast": (
        "A forecast is a educated guess based on patterns in the past. The confidence band shows "
        "how wrong we might reasonably be — wider bands mean more uncertainty."
    ),
    "dm_test": (
        "The Diebold-Mariano test is like a referee deciding if one model's edge over another "
        "is real skill or just luck from a small sample."
    ),
}
