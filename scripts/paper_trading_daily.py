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
from models.rules.circuit_breaker import (
    check_circuit_breaker,
    get_drawdown_throttle,
    get_paper_equity_drawdown,
)
from models.rules.event_filter import is_event_day
from models.rules.dual_momentum import check_absolute_momentum


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


def run_daily_decision(
    symbol: str = "AAPL",
    end_date: str | None = None,
    stat_only: bool = False,
    *,
    circuit_breaker_pct: float | None = None,
    drawdown_throttle: bool = False,
    use_event_filter: bool = True,
    prior_decisions: list | None = None,
    dual_momentum: bool = False,
    short_term_reversal: bool = False,
    low_vol_tilt: bool = False,
) -> dict:
    """
    Run full prediction logic for one day (point-in-time).
    Returns decision record for paper_decisions.json.
    stat_only=True: skip LSTM (match best_combo / Stat Core backtest).

    Circuit Breaker: block new positions when drawdown >= circuit_breaker_pct (e.g. 0.15).
    Drawdown Throttle: scale position when dd>=10% (0.75x) or dd>=15% (0.5x).
    Event Filter: skip trade on event days (earnings, FOMC, etc.).
    prior_decisions: for batch mode — accumulated decisions before today.
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
    if not stat_only:
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

    # Short-Term Reversal: in mean_reverting, only enter when oversold (1m return < 0)
    if short_term_reversal and has_edge_final and regime_name == "mean_reverting":
        returns_ser = returns.dropna()
        if len(returns_ser) >= 22:
            ret_1m = float((1 + returns_ser.iloc[-22:]).prod() - 1.0)
            if ret_1m >= 0:  # not oversold
                has_edge_final = False

    # Dual Momentum: if SP500 12m < risk-free, go to cash
    if dual_momentum and has_edge_final and prediction_date is not None:
        pred_str = prediction_date.strftime("%Y-%m-%d")
        go_cash, _ = check_absolute_momentum(pred_str, lookback_months=12, risk_free_annual=0.04)
        if go_cash:
            has_edge_final = False

    # best_combo position sizing hint: trend=50%, mean_reverting=200%, else 100%
    position_pct = 100
    if has_edge_final and regime_name == "trend":
        position_pct = 50
    elif has_edge_final and regime_name == "mean_reverting":
        position_pct = 200  # MR x2

    # Low-Vol Tilt: when vol in top quartile (60d), scale down
    if low_vol_tilt and has_edge_final and "volatility" in df.columns:
        vol = df["volatility"].dropna()
        if len(vol) >= 60:
            vol_75 = vol.iloc[-60:].quantile(0.75)
            if float(vol.iloc[-1]) >= float(vol_75):
                position_pct = max(0, int(position_pct * 0.5))

    # Circuit Breaker & Drawdown Throttle
    circuit_breaker_tripped = False
    current_drawdown_pct = 0.0
    drawdown_throttle_mult = 1.0
    if (circuit_breaker_pct is not None or drawdown_throttle) and prediction_date is not None:
        pred_str = prediction_date.strftime("%Y-%m-%d")
        if prior_decisions is not None:
            prior = [d for d in prior_decisions if d.get("date") and d.get("date") < pred_str]
        else:
            path = Path(__file__).parent.parent / "storage" / "paper_decisions.json"
            all_d = []
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as f:
                        all_d = json.load(f)
                except json.JSONDecodeError:
                    pass
            prior = [d for d in all_d if d.get("date") and d.get("date") < pred_str]
        _, current_drawdown_pct, _ = get_paper_equity_drawdown(
            prior, returns, symbol.upper()
        )
        if circuit_breaker_pct is not None and current_drawdown_pct >= circuit_breaker_pct:
            circuit_breaker_tripped = True
            has_edge_final = False
            position_pct = 0
        elif drawdown_throttle and has_edge_final:
            drawdown_throttle_mult = get_drawdown_throttle(current_drawdown_pct)
            position_pct = max(0, int(position_pct * drawdown_throttle_mult))

    # Event Calendar filter
    event_day = False
    if use_event_filter and prediction_date is not None and has_edge_final:
        pred_str = prediction_date.strftime("%Y-%m-%d")
        if is_event_day(pred_str, symbol.upper()):
            event_day = True
            has_edge_final = False
            position_pct = 0

    record = {
        "date": prediction_date.strftime("%Y-%m-%d") if prediction_date else None,
        "symbol": symbol.upper(),
        "stat_only": stat_only,
        "has_edge_stat": has_edge_stat,
        "has_edge_final": has_edge_final,
        "ml_blocked": ml_blocked,
        "regime": regime_name,
        "position_pct": position_pct,
        "direction": arima_out["direction"],
        "stat_confidence": conf,
        "confidence_factors": _factors_to_dict(factors),
        "ml_probs": {k: round(v, 4) for k, v in (ml_probs or {}).items()},
        "model_version": "stat_only" if stat_only else _model_version(),
        "circuit_breaker_tripped": circuit_breaker_tripped,
        "current_drawdown_pct": round(current_drawdown_pct, 4),
        "drawdown_throttle_mult": drawdown_throttle_mult,
        "event_day": event_day,
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
    ap.add_argument("--no-ml", action="store_true", help="Stat Only — skip LSTM (match best_combo backtest)")
    ap.add_argument("--circuit-breaker", type=float, default=None, metavar="PCT", help="Block when drawdown >= PCT (e.g. 0.15). Default: off")
    ap.add_argument("--drawdown-throttle", action="store_true", help="Scale position when in drawdown (10%%->0.75x, 15%%->0.5x)")
    ap.add_argument("--no-event-filter", action="store_true", help="Disable event calendar filter (earnings, FOMC, etc.)")
    ap.add_argument("--dual-momentum", action="store_true", help="Absolute momentum: if SP500 12m < 4%%, go to cash")
    ap.add_argument("--short-term-reversal", action="store_true", help="Mean-reverting: only enter when oversold (1m < 0)")
    ap.add_argument("--low-vol-tilt", action="store_true", help="Scale down when vol in top quartile")
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
                record = run_daily_decision(
                    symbol=args.symbol,
                    end_date=end_date,
                    stat_only=args.no_ml,
                    circuit_breaker_pct=args.circuit_breaker,
                    drawdown_throttle=args.drawdown_throttle,
                    use_event_filter=not args.no_event_filter,
                    prior_decisions=decisions,
                    dual_momentum=args.dual_momentum,
                    short_term_reversal=args.short_term_reversal,
                    low_vol_tilt=args.low_vol_tilt,
                )
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

    flags = ["Stat Only"] if args.no_ml else []
    if args.circuit_breaker is not None:
        flags.append(f"CircuitBreaker>={args.circuit_breaker:.0%}")
    if args.drawdown_throttle:
        flags.append("DD-Throttle")
    if not args.no_event_filter:
        flags.append("EventFilter")
    if args.dual_momentum:
        flags.append("DualMom")
    if args.short_term_reversal:
        flags.append("STR-Reversal")
    if args.low_vol_tilt:
        flags.append("LowVol-Tilt")
    print("SignalFlow — Paper Trading Daily Logger")
    print(f"  Symbol: {args.symbol}  End date: {end_date}" + ("  [" + ", ".join(flags) + "]" if flags else ""))

    try:
        record = run_daily_decision(
            symbol=args.symbol,
            end_date=end_date,
            stat_only=args.no_ml,
            circuit_breaker_pct=args.circuit_breaker,
            drawdown_throttle=args.drawdown_throttle,
            use_event_filter=not args.no_event_filter,
            dual_momentum=args.dual_momentum,
            short_term_reversal=args.short_term_reversal,
            low_vol_tilt=args.low_vol_tilt,
        )
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
