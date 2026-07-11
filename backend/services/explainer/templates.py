"""Plain-language explainer templates for Phase 3 outputs."""
from services.explainer.analogies import ANALOGIES
from services.explainer.verdicts import mae_severity, pvalue_severity, coverage_severity, SEVERITY_COLORS


def explain_stationarity(result: dict) -> dict:
    name = result.get("name", "series")
    consensus = result.get("consensus", "unknown")
    adf = result.get("adf", {})
    kpss = result.get("kpss", {})

    if consensus == "stationary":
        verdict = f"The {name} series has a stable long-run mean — it tends to return to a fixed level."
        severity = "good"
    elif consensus == "non_stationary":
        verdict = f"The {name} series is drifting — it doesn't reliably return to a fixed level."
        severity = "concerning"
    else:
        verdict = f"Stationarity tests for {name} give mixed signals — treat with caution."
        severity = "moderate"

    because_parts = []
    if "p_value" in adf:
        adf_p = adf["p_value"]
        because_parts.append(
            f"The ADF test p-value is {adf_p:.3f} "
            f"({'below' if adf_p < 0.05 else 'above'} the 0.05 threshold)."
        )
    if "p_value" in kpss:
        kpss_p = kpss["p_value"]
        because_parts.append(
            f"The KPSS test p-value is {kpss_p:.3f} "
            f"({'consistent with' if kpss_p >= 0.05 else 'inconsistent with'} stationarity)."
        )

    return {
        "type": "stationarity",
        "verdict": verdict,
        "because": " ".join(because_parts) or "Insufficient test data.",
        "deep_dive": ANALOGIES["stationarity"],
        "severity": severity,
        "color": SEVERITY_COLORS[severity],
        "raw": result,
    }


def explain_cointegration(result: dict) -> dict:
    if "error" in result:
        return {"type": "cointegration", "verdict": result["error"], "severity": "informational", "color": "neutral", "raw": result}

    rank = result.get("cointegrating_rank_95", 0)
    vars_ = result.get("variables", ["series A", "series B"])
    if rank > 0:
        verdict = (
            f"{' and '.join(vars_)} move together in the long run — "
            "they can't drift apart forever."
        )
        severity = "good"
    else:
        verdict = "No strong long-run relationship detected between the rate series."
        severity = "informational"

    trace = result.get("trace_statistics", [0])
    crit = result.get("critical_95", [0])
    because = (
        f"The Johansen trace statistic ({trace[0]:.1f}) "
        f"{'exceeds' if trace[0] > crit[0] else 'does not exceed'} "
        f"the 5% critical value ({crit[0]:.1f}), suggesting "
        f"{rank} cointegrating relationship(s)."
    )

    return {
        "type": "cointegration",
        "verdict": verdict,
        "because": because,
        "deep_dive": ANALOGIES["cointegration"],
        "severity": severity,
        "color": SEVERITY_COLORS[severity],
        "raw": result,
    }


def explain_granger(result: dict) -> dict:
    if "error" in result:
        return {"type": "granger", "verdict": result["error"], "severity": "informational", "color": "neutral", "raw": result}

    direction = result.get("direction", "")
    causes = result.get("causes", False)
    p = result.get("best_p_value", 1.0)

    if causes:
        verdict = f"Movements in {result['cause']} help predict {result['effect']} — a useful lead-lag relationship."
        severity = "good"
    else:
        verdict = f"No useful predictive relationship found from {result['cause']} to {result['effect']}."
        severity = "informational"

    because = f"Best lag F-test p-value: {p:.3f} at lag {result.get('best_lag')}."

    return {
        "type": "granger",
        "verdict": verdict,
        "because": because,
        "deep_dive": ANALOGIES["granger"],
        "severity": severity,
        "color": SEVERITY_COLORS[severity],
        "raw": result,
    }


def explain_forecast(target: str, ensemble: dict, backtest: dict | None = None) -> dict:
    fc = ensemble.get("forecast", [])
    if not fc:
        return {"type": "forecast", "verdict": "No forecast available.", "severity": "informational", "color": "neutral"}

    point = fc[-1]
    weights = ensemble.get("weights", {})
    top_model = max(weights, key=weights.get) if weights else "ensemble"

    if backtest and backtest.get("best_mae"):
        mae = backtest["best_mae"]
        band = mae * 1.5
        verdict = (
            f"{target.capitalize()} rate will most likely be around {point:.1f} VES "
            f"(could realistically be {point - band:.0f} to {point + band:.0f})."
        )
        severity = mae_severity(mae, scale=point)
    else:
        verdict = f"{target.capitalize()} rate projected at {point:.1f} VES over the forecast horizon."
        severity = "informational"

    weight_str = ", ".join(f"{k} {v*100:.0f}%" for k, v in sorted(weights.items(), key=lambda x: -x[1])[:3])
    because = f"Ensemble weighted by recent accuracy. Top contributor: {top_model}. Weights: {weight_str}."

    return {
        "type": "forecast",
        "verdict": verdict,
        "because": because,
        "deep_dive": ANALOGIES["forecast"],
        "severity": severity,
        "color": SEVERITY_COLORS.get(severity, "neutral"),
        "raw": {"forecast": fc, "weights": weights},
    }


def explain_metrics(metrics: dict, scale: float = 100) -> dict:
    mae = metrics.get("mae")
    mape = metrics.get("mape")
    mase = metrics.get("mase")
    coverage = metrics.get("coverage_95")

    parts = []
    if mae is not None:
        parts.append(f"On average, forecasts are off by {mae:.1f} VES in either direction.")
    if mape is not None:
        parts.append(f"Typical percentage error: {mape:.1f}%.")
    if mase is not None:
        parts.append(
            f"The model is {mase:.2f}× the error of a naive 'tomorrow = today' forecast."
        )

    verdict = " ".join(parts) if parts else "No metrics available."
    severity = mae_severity(mae, scale) if mae else "informational"

    because = ""
    if coverage is not None:
        because = f"95% confidence bands contained reality {coverage:.0f}% of the time."
        severity = coverage_severity(coverage)

    return {
        "type": "metrics",
        "verdict": verdict,
        "because": because,
        "deep_dive": "Lower MAE and MAPE mean more accurate forecasts. MASE below 1.0 beats a naive baseline.",
        "severity": severity,
        "color": SEVERITY_COLORS.get(severity, "neutral"),
        "raw": metrics,
    }


def explain_diebold_mariano(result: dict) -> dict:
    if "error" in result:
        return {"type": "diebold_mariano", "verdict": result["error"], "severity": "informational", "color": "neutral", "raw": result}

    if result.get("significant"):
        winner = result["winner"]
        if winner == "model_a":
            verdict = "Model A is statistically better than Model B — not just by luck."
        elif winner == "model_b":
            verdict = "Model B is statistically better than Model A — not just by luck."
        else:
            verdict = "Models are statistically indistinguishable."
        severity = "good" if winner != "tie" else "informational"
    else:
        verdict = "No statistically significant difference between the two models."
        severity = "informational"

    because = f"DM statistic {result['dm_statistic']:.2f}, p-value {result['p_value']:.3f}."

    return {
        "type": "diebold_mariano",
        "verdict": verdict,
        "because": because,
        "deep_dive": ANALOGIES["dm_test"],
        "severity": severity,
        "color": SEVERITY_COLORS.get(severity, "neutral"),
        "raw": result,
    }


def explain_irf(result: dict) -> dict:
    if "error" in result:
        return {"type": "irf", "verdict": result["error"], "severity": "informational", "color": "neutral", "raw": result}

    shock = result.get("shock_variable", "")
    responses = result.get("responses", {})
    bcv_resp = responses.get("tasa_bcv", responses.get(list(responses.keys())[-1] if responses else ""))
    if bcv_resp:
        peak = max(bcv_resp, key=abs)
        peak_day = bcv_resp.index(peak)
        verdict = (
            f"A shock to {shock} peaks in the BCV response around day {peak_day} "
            f"({peak:+.2f} in differenced units)."
        )
    else:
        verdict = f"Impulse response computed for shock to {shock}."

    return {
        "type": "irf",
        "verdict": verdict,
        "because": f"VAR lag order: {result.get('lag_order')}, horizon: {result.get('periods')} periods.",
        "deep_dive": ANALOGIES["irf"],
        "severity": "informational",
        "color": "neutral",
        "raw": result,
    }


def explain_structural_break(result: dict) -> dict:
    best = result.get("best_break")
    if not best or "error" in best:
        return {"type": "structural_break", "verdict": "No structural break detected.", "severity": "good", "color": "green", "raw": result}

    if best.get("has_break"):
        verdict = f"Something changed around {best.get('break_date')} — the series behaves differently before and after."
        severity = "concerning"
    else:
        verdict = "No significant structural break detected in the series."
        severity = "good"

    because = f"Chow test p-value: {best.get('p_value', 1):.3f}."

    return {
        "type": "structural_break",
        "verdict": verdict,
        "because": because,
        "deep_dive": "Structural breaks often coincide with policy changes, sanctions, or regime shifts — common in Venezuelan FX.",
        "severity": severity,
        "color": SEVERITY_COLORS.get(severity, "neutral"),
        "raw": result,
    }


def explain_pipeline(pipeline: dict) -> dict:
    """Generate explainer output for entire forecast pipeline."""
    explanations = {}

    for key, val in pipeline.items():
        if key.startswith("stationarity_"):
            explanations[key] = explain_stationarity(val)
        elif key == "cointegration":
            explanations[key] = explain_cointegration(val)
        elif key == "irf":
            explanations[key] = explain_irf(val)
        elif key.startswith("breaks_"):
            explanations[key] = explain_structural_break(val)
        elif key.endswith("_ensemble"):
            target = key.replace("_ensemble", "")
            backtest = pipeline.get(f"{target}_backtest")
            explanations[key] = explain_forecast(target, val, backtest)
        elif key.endswith("_backtest"):
            target = key.replace("_backtest", "")
            best = val.get("best_model")
            if best:
                metrics = val["models"].get(best, {}).get("summary", {})
                explanations[f"{target}_metrics"] = explain_metrics(metrics, scale=500)

    if pipeline.get("granger"):
        explanations["granger"] = [explain_granger(g) for g in pipeline["granger"][:4]]

    comparisons = []
    for target in ["binance", "bcv"]:
        bt = pipeline.get(f"{target}_backtest", {})
        for comp in bt.get("comparisons", []):
            comparisons.append(explain_diebold_mariano(comp))
    if comparisons:
        explanations["model_comparisons"] = comparisons

    return explanations
