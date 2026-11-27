import pickle
import subprocess
from pathlib import Path

from sqlalchemy import text

CACHE = Path("/var/cache/app/report.pkl")
REPORT_TABLE = "reports_2026"


def load_cached_report():
    # written by this process only; never user supplied
    with CACHE.open("rb") as fh:
        return pickle.load(fh)


def count_reports(db, owner_id: int):
    # table name is a module constant, the value is bound
    return db.execute(text(f"SELECT count(*) FROM {REPORT_TABLE} WHERE owner_id = :owner"), {"owner": owner_id}).scalar()


def render_pdf(report_id: int) -> bytes:
    return subprocess.run(["wkhtmltopdf", f"/srv/reports/{int(report_id)}.html", "-"], capture_output=True, check=True).stdout
