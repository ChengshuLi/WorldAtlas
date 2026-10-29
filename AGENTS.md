# Working rules

For cloud workers and Codex chats managed by Potata:

- Keep code, documentation, and reports concise and human-readable.
- Use exactly two levels: Potata may delegate directly to workers; workers must not spawn subagents or Codex chats.
- Make each change in a small pull request with a clear summary and relevant test results. The user reviews and comments; workers should be ready to revise based on that feedback. The user manually merges. Never push directly to `main`, enable auto-merge, or merge any PR.
- Only the user may submit GitHub reviews or post inline code-review comments, including replies in review threads. Open pull requests ready for review by default. Use draft status only when drafts skip CI to ease a long queue for ready PRs.
- Keep CI as simple and minimal as possible. Use only fast checks relevant to each change, and avoid unnecessary full rebuilds.
- Prefer code and command-line tools. Use a browser only when absolutely necessary.
- You may download ordinary public online sources and materials in any format without asking.
