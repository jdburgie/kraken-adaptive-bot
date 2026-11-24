import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backtest.backtest import filter_date_range, run_backtest
from bot.market_data import load_ohlcv_csv


DETAIL_FIELDS = [
    "strategy",
    "asset",
    "csv",
    "window",
    "start_date",
    "end_date",
    "status",
    "rows",
    "trades",
    "wins",
    "losses",
    "win_rate",
    "net_pnl",
    "ending_balance",
    "return_pct",
    "profit_factor",
    "max_drawdown_pct",
    "expectancy",
    "score",
]

RANKING_FIELDS = [
    "strategy",
    "runs",
    "passing_runs",
    "pass_rate",
    "total_trades",
    "avg_return_pct",
    "worst_return_pct",
    "avg_profit_factor",
    "max_drawdown_pct",
    "avg_score",
    "aggregate_score",
]


def load_config(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def selected(name, selections):
    return not selections or name in selections


def finite_profit_factor(value):
    if value == float("inf") or math.isinf(value):
        return 10.0
    return value


def result_score(metrics, min_trades):
    trades = metrics["trades"]
    return_pct = metrics["return_pct"] * 100
    drawdown_pct = metrics["max_drawdown_pct"] * 100
    profit_factor = finite_profit_factor(metrics["profit_factor"])

    score = return_pct * 2.0
    score += (min(profit_factor, 3.0) - 1.0) * 10.0
    score -= drawdown_pct * 1.5

    if trades < min_trades:
        score -= (min_trades - trades) * 3.0

    if metrics["expectancy"] <= 0:
        score -= 5.0

    return round(score, 2)


def write_csv(path, rows, fields):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def format_metric(value, pct=False):
    if value == float("inf") or (isinstance(value, float) and math.isinf(value)):
        return "inf"
    if pct:
        value = value * 100
    return round(value, 4)


def run_detail(config, asset_filter, window_filter, strategy_filter):
    ranking_config = config.get("ranking", {})
    min_trades = ranking_config.get("min_trades", 8)
    assets = config.get("assets", [])
    windows = config.get("windows") or [{"name": "full", "start_date": None, "end_date": None}]
    strategies = config.get("strategies", [])

    rows = []
    data_cache = {}

    for asset in assets:
        asset_name = asset["name"]
        csv_path = asset["csv"]

        if not selected(asset_name, asset_filter):
            continue

        if not os.path.exists(csv_path):
            for strategy in strategies:
                if not selected(strategy["name"], strategy_filter):
                    continue
                if not selected(asset_name, strategy.get("assets")):
                    continue
                for window in windows:
                    if not selected(window["name"], window_filter):
                        continue
                    if not selected(window["name"], strategy.get("windows")):
                        continue
                    rows.append(
                        {
                            "strategy": strategy["name"],
                            "asset": asset_name,
                            "csv": csv_path,
                            "window": window["name"],
                            "start_date": window.get("start_date") or "",
                            "end_date": window.get("end_date") or "",
                            "status": "missing_csv",
                            "rows": 0,
                            "trades": 0,
                            "wins": 0,
                            "losses": 0,
                            "win_rate": 0,
                            "net_pnl": 0,
                            "ending_balance": 0,
                            "return_pct": 0,
                            "profit_factor": 0,
                            "max_drawdown_pct": 0,
                            "expectancy": 0,
                            "score": 0,
                        }
                    )
            continue

        if csv_path not in data_cache:
            data_cache[csv_path] = load_ohlcv_csv(csv_path)

        for window in windows:
            window_name = window["name"]
            if not selected(window_name, window_filter):
                continue

            window_df = filter_date_range(
                data_cache[csv_path],
                window.get("start_date"),
                window.get("end_date"),
            )

            for strategy in strategies:
                strategy_name = strategy["name"]
                if not selected(strategy_name, strategy_filter):
                    continue
                if not selected(asset_name, strategy.get("assets")):
                    continue
                if not selected(window_name, strategy.get("windows")):
                    continue

                params = dict(strategy.get("params", {}))
                benchmark_csv = params.pop("benchmark_csv", None)
                benchmark_df = None

                if benchmark_csv:
                    if not os.path.exists(benchmark_csv):
                        rows.append(
                            {
                                "strategy": strategy_name,
                                "asset": asset_name,
                                "csv": csv_path,
                                "window": window_name,
                                "start_date": window.get("start_date") or "",
                                "end_date": window.get("end_date") or "",
                                "status": "missing_benchmark_csv",
                                "rows": len(window_df),
                                "trades": 0,
                                "wins": 0,
                                "losses": 0,
                                "win_rate": 0,
                                "net_pnl": 0,
                                "ending_balance": 0,
                                "return_pct": 0,
                                "profit_factor": 0,
                                "max_drawdown_pct": 0,
                                "expectancy": 0,
                                "score": 0,
                            }
                        )
                        continue

                    if benchmark_csv not in data_cache:
                        data_cache[benchmark_csv] = load_ohlcv_csv(benchmark_csv)

                    benchmark_df = filter_date_range(
                        data_cache[benchmark_csv],
                        window.get("start_date"),
                        window.get("end_date"),
                    )

                if benchmark_df is not None:
                    params["benchmark_df"] = benchmark_df

                trades, metrics, _ = run_backtest(window_df, **params)

                rows.append(
                    {
                        "strategy": strategy_name,
                        "asset": asset_name,
                        "csv": csv_path,
                        "window": window_name,
                        "start_date": window.get("start_date") or "",
                        "end_date": window.get("end_date") or "",
                        "status": "ok",
                        "rows": len(window_df),
                        "trades": metrics["trades"],
                        "wins": metrics["wins"],
                        "losses": metrics["losses"],
                        "win_rate": format_metric(metrics["win_rate"], pct=True),
                        "net_pnl": format_metric(metrics["net_pnl"]),
                        "ending_balance": format_metric(metrics["ending_balance"]),
                        "return_pct": format_metric(metrics["return_pct"], pct=True),
                        "profit_factor": format_metric(metrics["profit_factor"]),
                        "max_drawdown_pct": format_metric(metrics["max_drawdown_pct"], pct=True),
                        "expectancy": format_metric(metrics["expectancy"]),
                        "score": result_score(metrics, min_trades),
                    }
                )

    return rows


def summarize_rankings(detail_rows, config):
    ranking_config = config.get("ranking", {})
    min_trades = ranking_config.get("min_trades", 8)
    min_profit_factor = ranking_config.get("min_profit_factor", 1.0)
    grouped = defaultdict(list)

    for row in detail_rows:
        if row["status"] == "ok":
            grouped[row["strategy"]].append(row)

    summaries = []
    for strategy, rows in grouped.items():
        if not rows:
            continue

        passing = [
            row
            for row in rows
            if int(row["trades"]) >= min_trades
            and float(row["return_pct"]) > 0
            and float(row["profit_factor"]) >= min_profit_factor
            and float(row["expectancy"]) > 0
        ]

        avg_return = sum(float(row["return_pct"]) for row in rows) / len(rows)
        worst_return = min(float(row["return_pct"]) for row in rows)
        avg_pf = sum(float(row["profit_factor"]) if row["profit_factor"] != "inf" else 10.0 for row in rows) / len(rows)
        max_dd = max(float(row["max_drawdown_pct"]) for row in rows)
        avg_score = sum(float(row["score"]) for row in rows) / len(rows)
        pass_rate = len(passing) / len(rows)
        aggregate_score = avg_score + pass_rate * 20 + min(worst_return, 0) * 2 - max_dd

        summaries.append(
            {
                "strategy": strategy,
                "runs": len(rows),
                "passing_runs": len(passing),
                "pass_rate": round(pass_rate * 100, 4),
                "total_trades": sum(int(row["trades"]) for row in rows),
                "avg_return_pct": round(avg_return, 4),
                "worst_return_pct": round(worst_return, 4),
                "avg_profit_factor": round(avg_pf, 4),
                "max_drawdown_pct": round(max_dd, 4),
                "avg_score": round(avg_score, 4),
                "aggregate_score": round(aggregate_score, 4),
            }
        )

    return sorted(summaries, key=lambda row: row["aggregate_score"], reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Run a backtest matrix from a JSON config.")
    parser.add_argument("--config", default="configs/shared_baseline.json")
    parser.add_argument("--output")
    parser.add_argument("--ranking-output")
    parser.add_argument("--asset", action="append", help="Limit to one asset name. Can be repeated.")
    parser.add_argument("--window", action="append", help="Limit to one window name. Can be repeated.")
    parser.add_argument("--strategy", action="append", help="Limit to one strategy name. Can be repeated.")
    args = parser.parse_args()

    config = load_config(args.config)
    output = args.output or config.get("output", "matrix-results.csv")
    ranking_output = args.ranking_output or config.get("ranking_output", "matrix-ranking-results.csv")

    detail_rows = run_detail(config, args.asset, args.window, args.strategy)
    ranking_rows = summarize_rankings(detail_rows, config)

    write_csv(output, detail_rows, DETAIL_FIELDS)
    write_csv(ranking_output, ranking_rows, RANKING_FIELDS)

    print(f"Wrote {len(detail_rows)} detail rows to {output}")
    print(f"Wrote {len(ranking_rows)} ranking rows to {ranking_output}")

    for row in ranking_rows[:5]:
        print(
            f"{row['strategy']}: aggregate_score={row['aggregate_score']} "
            f"pass_rate={row['pass_rate']}% avg_return={row['avg_return_pct']}% "
            f"max_dd={row['max_drawdown_pct']}%"
        )


if __name__ == "__main__":
    main()
