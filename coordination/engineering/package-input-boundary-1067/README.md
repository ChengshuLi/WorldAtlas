# Package input boundary — issue 1067

The shared declaration replaces frozen builder module fingerprints. Actual package commands build from a temporary source image; tests exercise real child reads/imports and installed-dependency/source symlinks. The declaration survey found no retained research-namespace dependency in the former inspected manifests; current dataset/source roots remain explicitly included.

The real Cloudflare build succeeded. `client-parity.json` compares every baseline hosted client file to the Cloudflare client and records no differences. Backend package flavors are intentionally different. The baseline hosted build reached complete package generation but its archive measurement failed because macOS BSD tar does not support the existing GNU tar flags. Ubuntu hosted CI must validate the hosted archive before merge. Local evidence does not claim a deployment, live database operation, or current production correctness.

`positive-control.json` and `negative-control.json` record executed child-build controls with their logs. `final-local-tests.log` retains the relevant selector, boundary, integration and Cloudflare unit results. The build receipt predates the later change to hash raw declaration bytes rather than its parsed representation; it establishes the completed source image/build, not the final receipt-format field. The final receipt format and stale-receipt removal are exercised by subsequent unit tests and hosted CI.

The source image is a cooperative build contract rather than an OS security sandbox. Malicious code can deliberately access outside paths. Generated local datasets were restored and are not committed. Images clean up after success/failure; interrupted images stay inside the managed slot for normal cleanup.
