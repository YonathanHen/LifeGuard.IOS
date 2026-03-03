#!/usr/bin/env python
"""
SignalFlow — Paper Trading Daily Decision Logger
Records daily decision (before outcome) to storage/paper_decisions.json.
Run daily after market close (cron / Task Scheduler).
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from data.pipeline import DataPipeline
from models.regime import RegimeDetector
from models.ml.lstm_model import LSTMPredictor
from models.ml.ensemble import ensemble_decision_negative_filter
from models.stat import ARIMAModel, GARCHModel
from models.rules.engine import (
    has_statistical_edge,
    liquidity_gate,
    confidence_factors,
    overall_confidence,
    system_assessment,
)
from models.rules.cross_asset import check_cross_asset_alignment
from models.rules.cooldown import check_cooldown


def _disaster_threshold() -> float:
    return float(
        os.environ.get("ML_NEGATIVE_FILTER_THRESHOLD")
        or os.environ.get("ML_DISASTER_THRESHOLD", "0.80")
    )


def _model_version() -> str:
    """Model version for paper_decisions metadata."""
    threshold = _disaster_threshold()
    version = f"safeguard_{threshold:.2f}".replace(".", "")
    try:
        from models.ml.train_info import get_lstm_train_info
        info = get_lstm_train_info()
        if info:
            train_date = info.get("train_date") or info.get("data_end_date", "")
            if train_date:
                short = train_date[:10] if len(train_date) >= 10 else train_date
                version = f"{version}_{short}"
    except Exception:
        pass
    return version


def _factors_to_dict(factors) -> dict:
    """Serialize confidence_factors for JSON."""
    return {name: passed for name, passed in factors}


def run_daily_decision(symbol: str = "AAPL", end_date: str | None = None) -> dict:
    """
    Run full prediction logic for one day (point-in-time).
    Returns decision record for paper_decisions.json.
    """
    horizon = "daily"
    disaster_threshold = _disaster_threshold()

    pipeline = DataPipeline(
        symbol=symbol.upper(),
        horizon=horizon,
        period="2y",
        end_date=end_date,
    )
    df = pipeline.run()
    returns = df["returns"]
    data_stable = df["_stable"].iloc[-1] if "_stable" in df.columns else True
    prediction_date = returns.index[-1] if len(returns) > 0 else None

    regime_detector = RegimeDetector(horizon=horizon).fit(returns)
    regime_name, regime_stable, regime_max_prob = regime_detector.predict_with_proba(returns)

    in_cooldown = False
    if prediction_date is not None:
        in_cooldown, _, _ = check_cooldown(
            symbol.upper(), horizon, prediction_date, regime_name, regime_max_prob
        )

    arima = ARIMAModel().fit(returns)
    arima_out = arima.predict_next()
    garch = GARCHModel().fit(returns)
    garch_out = garch.predict_next(horizon=horizon)

    has_edge_stat = has_statistical_edge(arima_out, garch_out)
    cross_asset_ok, _ = check_cross_asset_alignment(horizon=horizon)
    liq_ok = liquidity_gate(pipeline.get_dollar_volume_20d_avg())
    if not liq_ok:
        has_edge_stat = False
    if not regime_stable:
        has_edge_stat = False
    if in_cooldown:
        has_edge_stat = False

    factors = confidence_factors(
        arima_out, garch_out, cross_asset_ok, liq_ok, regime_stable, bool(data_stable),
        cooldown_ok=not in_cooldown,
    )
    conf = overall_confidence(factors)

    ml_probs = None
    ml_blocked = False
    # We only trade Long when direction=up; direction=down/flat → no trade
    has_edge_final = has_edge_stat and arima_out["direction"] == "up"
    lstm = LSTMPredictor()
    if lstm.load():
        ml_probs = lstm.predict_proba(df)
        if ml_probs is not None and has_edge_stat and arima_out["direction"] == "up":
            should_trade, _ = ensemble_decision_negative_filter(
                has_edge_stat, arima_out["direction"], ml_probs,
                disaster_threshold=disaster_threshold,
            )
            if not should_trade:
                ml_blocked = True
                has_edge_final = False

    record = {
        "date": prediction_date.strftime("%Y-%m-%d") if prediction_date else None,
        "symbol": symbol.upper(),
        "has_edge_stat": has_edge_stat,
        "has_edge_final": has_edge_final,
        "ml_blocked": ml_blocked,
        "regime": regime_name,
        "direction": arima_out["direction"],
        "stat_confidence": conf,
        "confidence_factors": _factors_to_dict(factors),
        "ml_probs": {k: round(v, 4) for k, v in (ml_probs or {}).items()},
        "model_version": _model_version(),
    }
    return record


def main():
    import argparse
    import pandas as pd

    ap = argparse.ArgumentParser(description="Paper Trading — daily decision logger")
    ap.add_argument("--symbol", default="AAPL", help="Symbol (default AAPL)")
    ap.add_argument("--date", default=None, help="End date YYYY-MM-DD (default: yesterday)")
    ap.add_argument("--batch-start", default=None, help="Batch: start date YYYY-MM-DD")
    ap.add_argument("--batch-end", default=None, help="Batch: end date YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true", help="Print only, do not save")
    args = ap.parse_args()

    # Batch mode: populate many dates
    if args.batch_start and args.batch_end:
        dates = pd.bdate_range(args.batch_start, args.batch_end)
        dates = [d.strftime("%Y-%m-%d") for d in dates]
        print("SignalFlow — Paper Trading Batch Logger")
        print(f"  Symbol: {args.symbol}  Dates: {len(dates)} ({args.batch_start} -> {args.batch_end})")

        storage = Path(__file__).parent.parent / "storage"
        storage.mkdir(exist_ok=True)
        path = storage / "paper_decisions.json"
        decisions = []
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    decisions = json.load(f)
            except json.JSONDecodeError:
                decisions = []

        existing = {(d.get("date"), d.get("symbol")) for d in decisions if d.get("date") and d.get("symbol")}
        added = 0
        skipped = 0
        errors = 0
        for i, end_date in enumerate(dates):
            if (end_date, args.symbol) in existing:
                skipped += 1
                continue
            try:
                record = run_daily_decision(symbol=args.symbol, end_date=end_date)
            except Exception as e:
                print(f"  ERROR {end_date}: {e}")
                errors += 1
                continue
            date_str = record.get("date")
            if date_str and (date_str, args.symbol) in existing:
                skipped += 1
                continue
            decisions.append(record)
            existing.add((date_str or end_date, args.symbol))
            added += 1
            if (i + 1) % 20 == 0 or added % 50 == 1:
                print(f"  Progress: {i+1}/{len(dates)} | added={added} skipped={skipped}")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(decisions, f, indent=2, ensure_ascii=False)
        print(f"  Done: added={added} skipped={skipped} errors={errors} | {path}")
        return 0 if errors == 0 else 1

    # Single-date mode
    end_date = args.date
    if not end_date:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = yesterday

    print("SignalFlow — Paper Trading Daily Logger")
    print(f"  Symbol: {args.symbol}  End date: {end_date}")

    try:
        record = run_daily_decision(symbol=args.symbol, end_date=end_date)
    except Exception as e:
        print(f"\n*** ERROR: {e}")
        print("יום חסר ב-Logger = יום אבוד ב-Paper Trading. Yahoo/FRED נכשל?")
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(record, indent=2))
        return 0

    storage = Path(__file__).parent.parent / "storage"
    storage.mkdir(exist_ok=True)
    path = storage / "paper_decisions.json"

    decisions = []
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                decisions = json.load(f)
        except json.JSONDecodeError:
            decisions = []

    date_str = record.get("date")
    if date_str and any(d.get("date") == date_str and d.get("symbol") == args.symbol for d in decisions):
        print(f"  כבר קיים רשומה ל-{date_str} — מדלג (השתמש --dry-run לבדיקה)")
        return 0

    decisions.append(record)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2, ensure_ascii=False)

    print(f"  נשמר: {record['date']} | has_edge={record['has_edge_final']} ml_blocked={record['ml_blocked']}")
    print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
