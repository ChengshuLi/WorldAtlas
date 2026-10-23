# MCO 37-key current-owner readback blocker

Accepted-main target: `1a137b1b2e8d5d655412c242a5950f3d39e95bbb`.

The supported diagnostic named by the parent is `selected-owner-example.mjs` (reported SHA-256 prefix `7b354a...`). Its invocation requires a worktree at the exact accepted-main commit:

```sh
GIT_NO_LAZY_FETCH=1 GIT_NO_REPLACE_OBJECTS=1 \
  /Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node \
  /your/task/selected-owner-example.mjs \
  1a137b1b2e8d5d655412c242a5950f3d39e95bbb \
  '[{"y":95580,"x":136498}]' .
```

This task workspace has no managed checkout at that commit. The available `WorldAtlas` checkout is at `e760d68ff48a679b08f6fbf0581d1035de35105`; it is stale and was not used for accepted-main owner conclusions. No fetch, clone, checkout switch, or owner query was attempted. Therefore the 37 exact current owner IDs and their accepted-main stable location identities remain unknown. The MCO candidate preserves all 37 holds and makes no disposition, credit, or legal-boundary claim.
