"""Source-free refusal entrypoint; never starts the historical science runner."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import admission
import preflight

HERE = Path(__file__).resolve().parent
RECEIPT = HERE / "admission-assessment.json"


def main() -> int:
    assessment = preflight.run()
    receipt = (json.dumps(assessment, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if RECEIPT.exists():
        if RECEIPT.read_bytes() != receipt:
            raise RuntimeError("preserving the existing assessment; new bytes need a new owned receipt name")
    else:
        with RECEIPT.open("xb") as stream:
            stream.write(receipt)
            stream.flush()
    plan = assessment["admission"]["full_phase_plan"]
    if plan["status"] == "refused":
        print(json.dumps({"status": "refused", "producer_started": False,
                          "reasons": plan["reasons"], "receipt": str(RECEIPT.name)}, sort_keys=True))
        return 0

    # A future admitted input plan still needs an independently reviewed runner
    # whose exact code/runtime/output closure is part of that same plan.
    def no_reviewed_runner():
        raise admission.AdmissionError("this refusal-only packet contains no admitted geography producer")

    try:
        admission.run_if_admitted(plan, no_reviewed_runner)
    except admission.AdmissionError as error:
        print(json.dumps({"status": "admitted-input-plan-but-no-reviewed-producer",
                          "producer_started": False, "reason": str(error)}, sort_keys=True))
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
