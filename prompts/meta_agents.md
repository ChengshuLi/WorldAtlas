# Potata delegation rules

- Use up to 6 direct cloud subagents and up to 5 direct Codex chats. These are capacity ceilings, not quotas. Workers must not spawn subagents or chats.
- Explicitly set both the model and reasoning level whenever creating or resuming a worker or chat; never rely on defaults. Match the reasoning effort to the task.
- Use GPT-6.1 Sol or GPT-6.1 Terra for complex work such as engineering. Use GPT-6 Luna for simple tasks and geography/history research involving text processing. Model names and API IDs: GPT-6.1 Sol (`gpt-6.1-sol`), GPT-6.1 Terra (`gpt-6.1-terra`), GPT-6 Luna (`gpt-6-luna`). This supersedes any older Luna-only rule.
