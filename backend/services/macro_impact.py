"""Macro-personal bridge: elasticities and category regressions."""
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def _load_monthly_spending(conn) -> pd.DataFrame:
    rows = conn.execute("""
        SELECT strftime('%Y', fecha) as year, strftime('%m', fecha) as month,
               categoria, SUM(ABS(monto_usd)) as total_usd
        FROM transactions
        WHERE tipo = 'Gasto'
        GROUP BY year, month, categoria
    """).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    return df


def _load_ipc(conn) -> pd.DataFrame:
    rows = conn.execute(
        "SELECT year, month, var_pct FROM macro_ipc ORDER BY year, month"
    ).fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])


def _load_fx_monthly(conn) -> pd.DataFrame:
    rows = conn.execute("""
        SELECT strftime('%Y', fecha) as year, strftime('%m', fecha) as month,
               AVG(tasa_binance) as avg_binance
        FROM exchange_rates
        WHERE tasa_binance IS NOT NULL
        GROUP BY year, month
    """).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    return df


def compute_macro_impact(conn) -> dict[str, Any]:
    """Category-level regressions and income exposure."""
    spending = _load_monthly_spending(conn)
    ipc = _load_ipc(conn)
    fx = _load_fx_monthly(conn)

    if spending.empty:
        return {"error": "No spending data for macro impact analysis"}

    macro = ipc.merge(fx, on=["year", "month"], how="outer").sort_values(["year", "month"])
    macro = macro.dropna(subset=["var_pct"])

    categories = spending["categoria"].unique()
    elasticities = []
    correlations = []

    for cat in categories:
        cat_data = spending[spending["categoria"] == cat].merge(macro, on=["year", "month"], how="inner")
        if len(cat_data) < 6:
            continue

        # Log-log elasticity vs IPC
        if cat_data["var_pct"].notna().all() and (cat_data["total_usd"] > 0).all():
            y = np.log(cat_data["total_usd"].values)
            x_ipc = np.log1p(cat_data["var_pct"].values / 100).reshape(-1, 1)
            reg = LinearRegression().fit(x_ipc, y)
            ipc_elasticity = float(reg.coef_[0])

            elasticities.append({
                "category": cat,
                "ipc_elasticity": ipc_elasticity,
                "interpretation": (
                    f"When national IPC rises 1%, your {cat} spending rises "
                    f"{abs(ipc_elasticity)*100:.1f}%"
                    f"{' — less exposed than average' if abs(ipc_elasticity) < 0.7 else ''}."
                ),
                "n_obs": len(cat_data),
            })

            corr_ipc = float(np.corrcoef(cat_data["var_pct"], cat_data["total_usd"])[0, 1])
            correlations.append({
                "category": cat,
                "macro_variable": "IPC",
                "correlation": corr_ipc,
                "strength": "strong" if abs(corr_ipc) > 0.7 else "moderate" if abs(corr_ipc) > 0.4 else "weak",
            })

        # FX exposure
        if "avg_binance" in cat_data.columns and cat_data["avg_binance"].notna().sum() >= 6:
            corr_fx = float(np.corrcoef(cat_data["avg_binance"], cat_data["total_usd"])[0, 1])
            correlations.append({
                "category": cat,
                "macro_variable": "Binance FX",
                "correlation": corr_fx,
                "strength": "strong" if abs(corr_fx) > 0.7 else "moderate" if abs(corr_fx) > 0.4 else "weak",
            })

    # Risk score: composite exposure
    risk_factors = []
    if elasticities:
        avg_elasticity = np.mean([abs(e["ipc_elasticity"]) for e in elasticities])
        risk_factors.append(min(avg_elasticity, 1.0))
    if not ipc.empty:
        recent_ipc = ipc.tail(3)["var_pct"].mean()
        if recent_ipc and recent_ipc > 8:
            risk_factors.append(0.8)
        elif recent_ipc and recent_ipc > 5:
            risk_factors.append(0.5)
        else:
            risk_factors.append(0.2)

    risk_score = round(np.mean(risk_factors) * 100, 1) if risk_factors else None
    risk_level = (
        "critical" if risk_score and risk_score > 70 else
        "high" if risk_score and risk_score > 50 else
        "moderate" if risk_score and risk_score > 30 else
        "low"
    )

    return {
        "elasticities": elasticities,
        "correlations": correlations,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "macro_series_months": len(macro),
        "categories_analyzed": len(elasticities),
    }
