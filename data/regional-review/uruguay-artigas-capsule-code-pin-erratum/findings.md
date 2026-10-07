# Findings and handoff

## Confirmed integrity defect in the retained wrapper

The predecessor wrapper derived the executable inventory from the editable `evidence-quality.json` field `capsule`. It iterated the entries present and did not independently require the complete capsule path set. Its separate `PINNED` literal covered the source/input files but omitted the capsule code that the wrapper executes. The actual runner therefore accepted both an omitted capsule entry and capsule code whose hash was coherently refreshed in that manifest.

`controls/original-runner-audit-v2.json` records two fresh successful executions that reproduce the exact retained 2,506-byte report, successful execution after omitting the executable pin, and successful execution of altered code after either omitting or coherently refreshing that pin. In both altered-code cases, the fixture-local `audit-unreviewed-code.txt` probe was written; its exact bytes (`executed\n`) and SHA-256 are retained in the audit. The report bytes nevertheless matched the prior report. Other original negative controls rejected ordinary code drift, a wrong complete input, occupied output, broken symlink, symlink-parent escape, and traversal without mutating the output namespace. The original 24 source/helper bytes remained unchanged.

## Corrected runner and reproduction

The new entry point checks the raw issue snapshot against its fixed body digest and scope marker, checks exact equality of the required legacy manifest inventory, and checks the executed capsule against a fixed whole-file SHA-256 before it reserves output or starts the subprocess. A missing required pin, changed code, or coherently refreshed local manifest therefore fails before output creation. The issue contract snapshot and legacy manifest are retained with all original source and input bytes.

Two fresh corrected runs retained the same exact historical report hash `3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a`. The directed post-computation failure retained its report and `failure.json` and created no `publication.json`. `controls/corrected-runner-audit.json` records the missing-pin, altered-code, coherent-refresh, wrong-input, occupied-output, broken-symlink, symlink-parent, traversal, and failed-attempt controls with actual return codes and stdout/stderr hashes. All source/manifest/code originals remained unchanged during these controls.

## Engineering and geography limits

The executable identity is now bound to exact bytes reviewed in this PR and repeated in the issue contract. The evidence does not certify source authenticity or newer source currency. A separate source/legal review would be needed to establish either. The IGM contested labels and source-assigned department fields do not resolve title or administrative membership. No source correction, hierarchy or geometry change, historical import, production publication, regional approval, or sovereignty finding is proposed.
