"""Adaptive symbol prioritization for ingestion."""

from datetime import datetime, timedelta
from typing import List, Tuple
import random
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database.models import Stock, StockPrice, IngestionState
from config import get_settings


class SymbolPrioritizer:
    """Computes priority and selects symbols to process next."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def compute_priority(self, stock: Stock) -> float:
        """Compute priority score for a stock.

        Factors:
        - Data freshness (older price data -> higher priority)
        - Liquidity (higher volume -> higher priority)
        - Volatility (higher ATR/variance -> higher priority)
        - Failure streak penalization
        """
        # Freshness
        latest = (
            self.db.query(StockPrice.timestamp, StockPrice.volume)
            .filter(StockPrice.stock_id == stock.id)
            .order_by(StockPrice.timestamp.desc())
            .first()
        )
        now = datetime.utcnow()
        days_stale = 999.0
        avg_vol = 0.0
        if latest:
            days_stale = max(0.0, (now - latest[0]).total_seconds() / 86400.0)
            avg_vol = float(latest[1] or 0)

        # Existing state
        state = self.db.query(IngestionState).filter(IngestionState.stock_id == stock.id).first()
        failure_penalty = (state.failure_streak if state else 0) * 2.0

        # Simple heuristic
        score = days_stale * 2.0 + (avg_vol / 1e7) * 1.0 - failure_penalty
        return float(score)

    def ensure_state(self, stock_ids: List[int]):
        existing = {s.stock_id for s in self.db.query(IngestionState).filter(IngestionState.stock_id.in_(stock_ids)).all()}
        for sid in stock_ids:
            if sid not in existing:
                self.db.add(IngestionState(stock_id=sid))
        self.db.commit()

    def get_symbols_for_run(self) -> List[Stock]:
        """Select symbols to process this run with cap."""
        limit = self.settings.MAX_SYMBOLS_PER_RUN
        window_days = self.settings.COVERAGE_WINDOW_DAYS
        cutoff = datetime.utcnow() - timedelta(days=window_days)

        # Candidates: active stocks, prioritize stale or never processed
        q = self.db.query(Stock).filter(Stock.active == True)
        stocks = q.all()
        self.ensure_state([s.id for s in stocks])

        # Due list (time-based revisit)
        now = datetime.utcnow()
        states = {st.stock_id: st for st in self.db.query(IngestionState).filter(IngestionState.stock_id.in_([s.id for s in stocks])).all()}
        due = [s for s in stocks if (states.get(s.id) is None) or (states[s.id].next_run_at is None) or (states[s.id].next_run_at <= now)]

        # Score and sort all
        scored = [(self.compute_priority(s), s) for s in stocks]
        scored.sort(key=lambda x: x[0], reverse=True)
        score_order = [s for _, s in scored]

        main_quota = max(1, int(limit * (1.0 - self.settings.EXPLORATION_RATE)))
        explore_quota = max(1, limit - main_quota)

        # Pick from due first, then top scored
        selected = []
        for s in due:
            if len(selected) >= main_quota:
                break
            selected.append(s)
        if len(selected) < main_quota:
            for s in score_order:
                if s in selected:
                    continue
                selected.append(s)
                if len(selected) >= main_quota:
                    break

        # Exploration: random unseen/low-priority symbols
        remaining = [s for s in stocks if s not in selected]
        if remaining and explore_quota > 0:
            random.shuffle(remaining)
            selected.extend(remaining[:explore_quota])

        return selected[:limit]

    def update_state(
        self,
        stock_id: int,
        ok: bool,
        price_updated: bool,
        fundamentals_updated: bool,
        runtime_ms: int,
    ) -> None:
        state = self.db.query(IngestionState).filter(IngestionState.stock_id == stock_id).first()
        if not state:
            state = IngestionState(stock_id=stock_id)
            self.db.add(state)
        now = datetime.utcnow()
        state.last_run_at = now
        state.avg_runtime_ms = runtime_ms if state.avg_runtime_ms is None else int((state.avg_runtime_ms * 0.7) + (runtime_ms * 0.3))
        if ok:
            state.success_streak = (state.success_streak or 0) + 1
            state.failure_streak = 0
        else:
            state.failure_streak = (state.failure_streak or 0) + 1
        if price_updated:
            state.last_price_update = now
        if fundamentals_updated:
            state.last_fundamental_update = now
        # Recompute priority
        stock = self.db.query(Stock).get(stock_id)
        if stock:
            state.priority_score = self.compute_priority(stock)
        # Next run time: priority-driven between min/max revisit
        min_d = max(1, self.settings.MIN_REVISIT_DAYS)
        max_d = max(min_d, self.settings.MAX_REVISIT_DAYS)
        # Normalize priority roughly by ranking
        # Higher priority -> sooner revisit
        pr = float(state.priority_score or 0.0)
        # Clamp and map to [0,1]
        pr_norm = 1.0 / (1.0 + max(0.0, pr)) if pr >= 0 else 1.0
        days_next = min_d + (max_d - min_d) * pr_norm
        state.next_run_at = now + timedelta(days=days_next)
        self.db.commit()


