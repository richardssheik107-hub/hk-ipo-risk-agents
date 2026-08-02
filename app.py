"""零依赖命令行入口：python app.py [公司ID]。"""

import json
import sys
from pathlib import Path

from risk_mvp.service import evaluate


def main() -> int:
    cases = json.loads((Path(__file__).parent / "data" / "simulated_ipo_cases.json").read_text(encoding="utf-8"))
    target = sys.argv[1] if len(sys.argv) > 1 else None
    selected = [case for case in cases if target in (None, case["company_id"])]
    if not selected:
        print(f"未找到模拟公司：{target}")
        return 1
    reports = [evaluate(case).to_dict() for case in selected]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
