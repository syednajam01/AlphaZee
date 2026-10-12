"""Read-only local baseline. Never output connection strings or credentials."""
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.config import settings

url = make_url(settings.database_url)
report = {
    "python": platform.python_version(),
    "environment": settings.app_env,
    "database_target": {"host": url.host, "port": url.port, "database": url.database},
    "checkout_enabled": settings.checkout_enabled,
}
engine = create_engine(settings.database_url, connect_args={"connect_timeout": 3})
try:
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL statement_timeout = '3s'"))
            report["database_version"] = connection.scalar(text("SHOW server_version"))
            report["alembic_revisions"] = list(connection.scalars(text("SELECT version_num FROM alembic_version")))
            report["table_counts"] = {}
            for table in ("orders", "order_lines", "stock_reservations", "inventory_balances", "products", "suppliers"):
                # Names are fixed above, never user-supplied identifiers.
                report["table_counts"][table] = connection.scalar(text(f'SELECT count(*) FROM "{table}"'))
except Exception as error:
    report["database_inspection_error"] = type(error).__name__
finally:
    engine.dispose()
print(json.dumps(report, indent=2))
