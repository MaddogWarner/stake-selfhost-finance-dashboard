from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.api_usage import ApiUsage  # noqa: F401
from app.models.app_setting import AppSetting  # noqa: F401
from app.models.company_profile import CompanyProfile  # noqa: F401
from app.models.holding import Holding  # noqa: F401
from app.models.news import News  # noqa: F401
from app.models.price_history import PriceHistory  # noqa: F401
from app.models.watchlist import Watchlist  # noqa: F401
