from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.api_usage import ApiUsage  # noqa: E402,F401
from app.models.company_profile import CompanyProfile  # noqa: E402,F401
from app.models.holding import Holding  # noqa: E402,F401
from app.models.news import News  # noqa: E402,F401
from app.models.price_history import PriceHistory  # noqa: E402,F401
from app.models.watchlist import Watchlist  # noqa: E402,F401
