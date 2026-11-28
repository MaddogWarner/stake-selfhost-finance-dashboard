import unittest
from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.api import holdings
from app.scheduler import jobs
from app.schemas.holding import HoldingUpdate
from app.services.yfinance_service import _safe_url


class FakeSession:
    def __init__(self, get_result=None, scalars=()):
        self.statements = []
        self.added = []
        self.get_result = get_result
        self._scalars = list(scalars)

    async def execute(self, stmt):
        self.statements.append(stmt)
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: self._scalars)
        )

    async def get(self, model, ident):
        return self.get_result

    def add(self, row):
        self.added.append(row)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


def fake_session_factory(session):
    @asynccontextmanager
    async def factory():
        yield session

    return factory


class ReviewFixTests(unittest.IsolatedAsyncioTestCase):
    def test_news_urls_must_be_http(self):
        self.assertEqual(_safe_url("https://example.com/a"), "https://example.com/a")
        self.assertEqual(_safe_url("HTTP://example.com"), "HTTP://example.com")
        self.assertIsNone(_safe_url("javascript:alert(1)"))
        self.assertIsNone(_safe_url("data:text/html,<p>x</p>"))
        self.assertIsNone(_safe_url(None))

    async def test_sync_does_not_overwrite_manual_holdings(self):
        session = FakeSession()
        row = {
            "ticker": "CBA",
            "exchange": "ASX",
            "quantity": Decimal("1"),
            "avg_cost": Decimal("2"),
        }
        with (
            patch.object(
                holdings.stake_client, "get_holdings", AsyncMock(return_value=[row])
            ),
            patch.object(
                holdings.stake_client, "get_watchlist", AsyncMock(return_value=[])
            ),
        ):
            await holdings.sync_stake_data(session)
        sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
        self.assertIn("ON CONFLICT (ticker, exchange) DO UPDATE", sql)
        self.assertIn("WHERE holdings.source =", sql)

    async def test_patch_can_clear_avg_cost_but_omission_keeps_it(self):
        holding = SimpleNamespace(quantity=Decimal("5"), avg_cost=Decimal("10"))
        session = FakeSession(get_result=holding)

        await holdings.update_holding(1, HoldingUpdate(quantity=Decimal("6")), session)
        self.assertEqual(holding.avg_cost, Decimal("10"))

        await holdings.update_holding(1, HoldingUpdate(avg_cost=None), session)
        self.assertIsNone(holding.avg_cost)
        self.assertEqual(holding.quantity, Decimal("6"))

    async def test_fundamentals_job_falls_back_to_yahoo_when_fmp_fails(self):
        session = FakeSession(scalars=[])
        fmp_down = AsyncMock(side_effect=HTTPException(status_code=503))
        yahoo = AsyncMock(return_value={"name": "Commonwealth Bank"})
        with (
            patch.object(jobs, "AsyncSessionLocal", fake_session_factory(session)),
            patch.object(
                jobs,
                "_unique_tickers",
                AsyncMock(return_value=[("CBA", "ASX"), ("AAPL", "NYSE")]),
            ),
            patch.object(jobs, "get_data_source", AsyncMock(return_value="both")),
            patch.object(jobs.fmp_service, "get_company_profile", fmp_down),
            patch.object(jobs.yfinance_service, "get_fundamentals", yahoo),
        ):
            await jobs.refresh_fundamentals()
        self.assertEqual([row.ticker for row in session.added], ["CBA", "AAPL"])
        self.assertEqual(session.added[0].name, "Commonwealth Bank")

    async def test_stake_sync_job_is_a_no_op_without_a_token(self):
        sync = AsyncMock()
        with (
            patch.object(jobs, "get_cached_token", return_value=None),
            patch.object(jobs.settings, "stake_session_token", None),
            patch.object(jobs, "sync_stake_data", sync),
        ):
            await jobs.sync_stake_holdings()
        sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
