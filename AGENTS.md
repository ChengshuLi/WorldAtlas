# Working rules

For cloud workers and Codex chats managed by Potata:

- Keep code, documentation, and reports concise and human-readable.
- Use exactly two levels: Potata may delegate directly to workers; workers must not spawn subagents or Codex chats.
- Make each change in a small pull request with a clear summary and relevant test results. The user reviews, comments, and manually merges. Never push directly to `main`, enable auto-merge, or merge any PR.
- Only the user may submit GitHub reviews or post inline code-review comments, including replies in review threads. Potata and workers may comment in PR conversations and issues. No `CL:` or `Potata:` prefix is required.
- Keep CI super-minimal, fast, and relevant to the change. Do not reintroduce legacy orchestration or queues, and avoid unnecessary full rebuilds.
- Prefer code and command-line tools. Use a browser only when absolutely necessary.
- You may download ordinary public online sources and materials in any format without asking, within the authorized access. Do not bypass access controls or security, legal, or payment obligations.
