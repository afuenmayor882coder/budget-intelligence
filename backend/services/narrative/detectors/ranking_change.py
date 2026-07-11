"""Ranking change detector: category/account position shifts."""
from datetime import datetime
from services.narrative.insight import Insight


def detect_ranking_changes(conn) -> list[Insight]:
    """Detect when spending categories change their rank positions."""
    insights = []
    now = datetime.now()

    def get_cat_ranking(year, month):
        start = f"{year:04d}-{month:02d}-01"
        end = f"{year+1:04d}-01-01" if month == 12 else f"{year:04d}-{month+1:02d}-01"
        rows = conn.execute(
            """SELECT categoria, SUM(ABS(monto_usd)) as total
               FROM transactions
               WHERE tipo='Gasto' AND categoria IS NOT NULL AND fecha >= ? AND fecha < ?
               GROUP BY categoria
               ORDER BY total DESC""",
            (start, end),
        ).fetchall()
        return {r["categoria"]: i+1 for i, r in enumerate(rows)}

    year, month = now.year, now.month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    curr_ranks = get_cat_ranking(year, month)
    prev_ranks = get_cat_ranking(prev_year, prev_month)

    big_moves = []
    for cat, curr_rank in curr_ranks.items():
        prev_rank = prev_ranks.get(cat)
        if prev_rank is not None:
            rank_change = prev_rank - curr_rank  # Positive = moved up (worse)
            if abs(rank_change) >= 2:
                big_moves.append({
                    "category": cat,
                    "previous_rank": prev_rank,
                    "current_rank": curr_rank,
                    "rank_change": rank_change,
                })

    big_moves.sort(key=lambda x: abs(x["rank_change"]), reverse=True)

    if big_moves:
        top = big_moves[0]
        direction = "up" if top["rank_change"] > 0 else "down"
        i = Insight(
            id=f"ranking_{top['category'].lower().replace(' ', '_')}_moved",
            detector="ranking_change",
            subject=f"{top['category']} Rank",
            type="ranking",
            direction=direction,
            magnitude="moderate" if abs(top["rank_change"]) >= 3 else "small",
            severity="notice",
            evidence={
                "category": top["category"],
                "previous_rank": top["previous_rank"],
                "current_rank": top["current_rank"],
                "all_changes": big_moves[:3],
            },
            time_window="month_over_month",
            tags=["spending"],
        )
        i.compute_priority(magnitude_zscore=min(1.0, abs(top["rank_change"]) / 4))
        insights.append(i)

    return insights
