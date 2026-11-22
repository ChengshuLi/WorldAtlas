# Working rules

These rules apply to every agent working in this repository. Keep code, documentation, and reports concise and readable.

## Python

- Annotate parameters and return types in all production function and method signatures. Leave `self` and `cls` unannotated and use `-> None` for functions that return no value. Use the concrete type expected from callers. Avoid bare `Any` and `object` parameters in production code. Check changed annotations against real callers with Pyright in the project Python environment.
- Follow [PEP 257](https://peps.python.org/pep-0257/) for docstrings. Give production modules, classes, functions, and methods a short summary, including private helpers. Use `Args`, `Returns`, and `Yields` where they apply. Explain units, array shapes, tuple order, errors callers need to handle, and effects such as writing a file or changing an input array.
- Follow [PEP 8](https://peps.python.org/pep-0008/#comments) for comments. Use complete sentences and explain decisions or constraints that the code alone does not show.
- Use plain, precise language in docstrings and comments. Give simple code a short explanation and use a concrete example when it helps explain complex code.
- Use Ruff to format code and check docstring structure. Aim for 88 characters per line and wrap long signatures.
- Import from the module that defines the name. Keep package `__init__.py` files empty or docstring-only by default. Expose names at package level when the package has a deliberate public interface.

## Tests and CI

- Require 100% line and branch coverage of production code. Write tests that assert meaningful behavior. Document a specific reason for any exception.
- Keep CI simple and fast. Run checks relevant to each change and avoid unnecessary full rebuilds.

## Correctness and performance

- Avoid unnecessary computation and memory use. Measure performance when a change could materially affect it.
- Use strict numeric comparisons for equality and tie decisions. Conservative bounds may keep extra candidates in the search. Use actual values to select the winner.
- Do not add application-imposed memory caps, floors, or watchdogs that stop or reject work based on memory use or availability. Do not use bounded caches as RAM ceilings. Streaming batches, chunks, and ordinary file buffering may process the full input. Keep input/output validation and operating-system constraints distinct from application memory limits.

## Working practices

- Use the shared Neon connection and R2 client in production Python code.
- When a mechanism blocks or slows work, first check whether it is needed. Remove it if unnecessary. Otherwise fix it or make a justified exception.
- Prefer code and command-line tools. Use a browser only when necessary. Ordinary public online sources and materials may be downloaded in any format without asking.
- Do not spawn subagents or create Codex chats unless the user explicitly requests it.

## Pull requests

- Keep pull requests small and include a clear summary and relevant test results. Open them ready for review by default and revise them in response to the user's feedback. Use draft status only when it skips CI to ease a long queue of ready pull requests.
- The user submits GitHub reviews and inline review comments, including replies, and merges pull requests manually. Never push directly to `main`, enable auto-merge, or merge a pull request.
