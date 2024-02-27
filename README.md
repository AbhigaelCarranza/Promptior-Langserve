# 🦜🔗 LangServe Replit Template

[![Run on Repl.it](https://replit.com/badge/github/langchain-ai/langserve-replit-template)](https://replit.com/new/github/langchain-ai/langserve-replit-template)

This template shows how to deploy a [LangChain Expression Language Runnable](https://python.langchain.com/docs/expression_language/) as a set of HTTP endpoints with stream and batch support using [LangServe](https://github.com/langchain-ai/langserve) onto [Replit](https://replit.com), a collaborative online code editor and platform for creating and deploying software.

## Getting started

The default chat endpoint is a chain that translates questions into pirate dialect.

1. Deploy your app to Replit by [clicking here](https://replit.com/new/github/langchain-ai/langserve-replit-template).
    - You will also need to set an `OPENAI_API_KEY` environment variable by going under `Tools > Secrets` in the bottom left corner.
    - To enable tracing, you'll also need to set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, and optionally `LANGCHAIN_SESSION`.
2. Run `pip install -U langchain-cli` to install the required command.
3. Run `poetry install` to install the required dependencies.
4. Press `Run` on `main.py`.
5. Navigate to `https://your_url.repl.co/docs/` to see documentation for your live runnable, and `https://your_url.repl.co/pirate-speak/playground/` to access a playground where you can try sending requests!

As you experiment, you can install the [LangSmith Replit extension](https://replit.com/extension/@langchain/a1d61149-f81e-4df7-9e91-69cfdcbccce3) to see traces of your runs in action by navigating to either your default project or the one set in your `LANGCHAIN_SESSION` environment variable.

## Calling from the client

You can use the `RemoteRunnable` class in LangServe to call these hosted runnables:

```python
from langserve import RemoteRunnable

pirate_chain = RemoteRunnable("https://your_url.repl.co/pirate-speak/")

pirate_chain.invoke({"question": "how are you?"})

# or async
await pirate_chain.ainvoke({"question": "how are you?"})

# Supports astream
async for msg in pirate_chain.astream({"question": "how are you?"}):
    print(msg, end="", flush=True)
```