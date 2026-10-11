import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_CORE = _ROOT / "libs" / "threadit_core"
for p in (str(_ROOT), str(_CORE)):
    if p not in sys.path:
        sys.path.insert(0, p)
