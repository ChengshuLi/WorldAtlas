# Working rules

These rules apply to every agent working in this repository.

- Keep code, documentation, and reports concise and human-readable.
- Follow [PEP 257](https://peps.python.org/pep-0257/) for Python docstrings. Give public modules, classes, and functions a short summary. Use an explicit `Args` section for caller-supplied parameters and a `Returns` section for returned values, including for short functions. Document side effects and relevant exceptions. Omit empty sections.
- Follow [PEP 8](https://peps.python.org/pep-0008/#comments) for comments. Use complete sentences and keep comments in sync with the code. Use inline comments sparingly and explain decisions or constraints that the code alone does not show.
- Treat correctness and performance as core requirements. Avoid unnecessary computation and memory use, and measure performance when a change could materially affect it.
- When blocked or slowed down, always first ask whether the blocking mechanism is needed. Remove it completely if unnecessary. If it is needed, choose the appropriate fix, including a justified exception when warranted.
- Do not spawn subagents or create Codex chats unless the user explicitly requests it.
- Make each change in a small pull request with a clear summary and relevant test results. The user reviews and comments; workers should be ready to revise based on that feedback. The user manually merges. Never push directly to `main`, enable auto-merge, or merge any PR.
- Only the user may submit GitHub reviews or post inline code-review comments, including replies in review threads. Open pull requests ready for review by default. Use draft status only when drafts skip CI to ease a long queue for ready PRs.
- Keep CI as simple and minimal as possible. Use only fast checks relevant to each change, and avoid unnecessary full rebuilds.
- Prefer code and command-line tools. Use a browser only when absolutely necessary.
- You may download ordinary public online sources and materials in any format without asking.
- Do not add application-imposed memory caps or floors, or memory watchdogs that stop or reject work based on memory use or availability. Ordinary streaming batches, chunks, and normal file buffering that process the full input are allowed; they are not memory caps. Do not use bounded caches as RAM ceilings. Keep ordinary input/output validation and operating-system/environment constraints distinct.
