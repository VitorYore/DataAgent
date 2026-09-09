"""Servidor exclusivo dos testes E2E: nunca publica nos relatórios do usuário."""
import atexit
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from api.app import REPORT_PATH, create_app

base = REPORT_PATH.parents[1] / "data/uploads"
base.mkdir(parents=True, exist_ok=True)
workspace = TemporaryDirectory(prefix="e2e-", dir=base)
root = Path(workspace.name).resolve()
assert root.is_relative_to(base.resolve())
atexit.register(workspace.cleanup)
report = root / "reports/resumo_executivo.json"
report.parent.mkdir()
if REPORT_PATH.exists():
    shutil.copyfile(REPORT_PATH, report)
app = create_app(report, root / "data/uploads")
