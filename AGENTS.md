# Working rules

These rules apply to every agent working in this repository. Keep code, documentation, and reports concise and readable.

## Design and simplification

- Start with the actual inputs, outputs and callers. Before adding or keeping an option, field, helper, check or compatibility path, identify the supported workflow that needs it. Check real configurations, records or artifacts when usage is unclear.
- Prefer one way to do a job. Remove obsolete paths across code, tests and docs. Keep decisions and data in one place. Avoid defaults, fallbacks and special cases for hypothetical use. Validate where data enters the code. Keep a second check only when it covers a different failure or the data may have changed.
- Give each function one responsibility and name it for what it does. Reuse an existing project helper, standard-library function or installed library before writing generic code. Review the setup and CI cost before introducing a new dependency or platform requirement.
- Keep build stages focused on producing their outputs. Run optional comparisons and one-off investigations separately. Keep reusable review scripts and reports in the local analysis workspace. Use local review pages for this project.

## Python

- Annotate parameters and return types in all production function and method signatures. Leave `self` and `cls` unannotated and use `-> None` for functions that return no value. Use the concrete type expected from callers. Avoid bare `Any` and `object` parameters in production code. Check changed annotations against real callers with Pyright in the project Python environment.
- Follow [PEP 257](https://peps.python.org/pep-0257/) for docstrings. Give production modules, classes, functions, and methods a short summary, including private helpers. Use `Args`, `Returns`, and `Yields` where they apply. Explain units, array shapes, tuple order, errors callers need to handle, and effects such as writing a file or changing an input array.
- Follow [PEP 8](https://peps.python.org/pep-0008/#comments) for comments. Use complete sentences and explain decisions or constraints that the code alone does not show.
- Use plain, precise language in docstrings and comments. Give simple code a short explanation and use a concrete example when it helps explain complex code.
- Use Ruff to format code and check docstring structure. Aim for 88 characters per line and wrap long signatures.
- Import from the module that defines the name. Keep package `__init__.py` files empty or docstring-only by default. Expose names at package level when the package has a deliberate public interface.

## Tests and CI

- Require 100% line and branch coverage of production code. Write tests that assert meaningful behavior. Document a specific reason for any exception.
- Verify changes through the normal entry point. State what was checked with fixtures and what was checked with real data or a saved build.
- Keep CI simple and fast. Run checks relevant to each change and avoid unnecessary full rebuilds.

## Correctness and performance

- Avoid unnecessary computation and memory use. Measure performance when a change could materially affect it, and address the largest measured bottleneck first. When a refactor is meant to preserve the map, compare the resulting cell assignments.
- Use strict numeric comparisons for equality and tie decisions. Conservative bounds may keep extra candidates in the search. Use actual values to select the winner.
- Do not add application-imposed memory caps, floors, or watchdogs that stop or reject work based on memory use or availability. Do not use bounded caches as RAM ceilings. Streaming batches, chunks, and ordinary file buffering may process the full input. Keep input/output validation and operating-system constraints distinct from application memory limits.

## Working practices

- Use the shared Neon connection and R2 client in production Python code.
- When a mechanism blocks or slows work, first check whether it is needed. Remove it if unnecessary. Otherwise fix it or make a justified exception.
- Prefer code and command-line tools. Use a browser only when necessary. Ordinary public online sources and materials may be downloaded in any format without asking.
- Do not spawn subagents or create Codex chats unless the user explicitly requests it.
- Discuss unapproved changes that materially alter supported workflows, data formats, dependencies or development setup before implementing them. Keep edits scoped to the decision the user approved.
- Let Markdown paragraphs wrap naturally. Use line breaks where Markdown needs them for structure.

## Guided code review

- State the file, line and function under review. Follow the call stack in execution order, including helpers, and return to the caller when a helper is covered. Match the requested pace. When reviewing one block at a time, treat “next” as one block and pause before starting a different file.
- Explain what goes in, what comes out, who uses the result, and why the code is needed. Use plain language and a concrete input and output from the current implementation when possible. Explain terms and file formats as they appear.
- For a database table review, give the row count and what the rows represent. Show column meanings, types and values from one actual row. Explain each constraint and when it is enforced.
- Distinguish what the code does today from a proposed change. Verify claims about current behavior against the code, saved artifacts or live records as appropriate.

## Pull requests

- Keep pull requests small and include a clear summary and relevant test results. Open them ready for review by default and revise them in response to the user's feedback. Use draft status only when it skips CI to ease a long queue of ready pull requests.
- The user submits GitHub reviews and inline review comments, including replies, and merges pull requests manually. Never push directly to `main`, enable auto-merge, or merge a pull request.
