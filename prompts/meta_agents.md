# Potata delegation rules

- Use up to 6 direct cloud subagents and up to 5 direct Codex chats. Workers must not spawn subagents or chats.
- Explicitly set both the model and reasoning level whenever creating or resuming a worker or chat; never rely on defaults.
- Use GPT-6.1 Terra (`gpt-6.1-terra`) with high reasoning as the default for cloud subagents and Codex chats, unless the user explicitly requests another model or reasoning level.
