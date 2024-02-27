from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from packages.agent_promptior.agent_promptior import PromptiorAgent
from langchain_core.runnables import RunnableLambda


app = FastAPI()

agent = PromptiorAgent("https://www.promptior.com")
# custom = agent.astream()
chain = agent.run()

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

# add_routes(app, RunnableLambda(agent.custom_stream), path="/chat")
add_routes(app, chain, path="/invoke")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
