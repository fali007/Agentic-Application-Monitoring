import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow
Traceloop.init(app_name="Agent", api_endpoint="localhost:4317")

model = ChatOpenAI(model="meta-llama/llama-3-3-70b-instruct")
prompt = "You are a helpful assistant capable of getting weather forecast and weather alerts. You are provided with state or co-ordinates. Call relavant tools to complete the input task and return summarised response"
mcp_server_url = "http://0.0.0.0:8000/sse"

class MCPServer:
    async def connect_to_sse_server(self, url):
        self.stream_context = sse_client(url = url)
        streams = await self.stream_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()
        await self.session.initialize()
    
    async def cleanup(self):
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self.stream_context:
            await self.stream_context.__aexit__(None, None, None)

@workflow(name="instana_agent_workflow")
async def run_agent():
    mcp_server = MCPServer()
    await mcp_server.connect_to_sse_server(mcp_server_url)
    tools = await load_mcp_tools(mcp_server.session)
    print(f"Tool list : {tools}")
    
    agent = create_react_agent(model, tools, prompt = prompt)
    inputs = {"messages" : "Get me weather alerts and forecast for NYC"}
    response = await agent.ainvoke(inputs)
    
    print_stream(response)
    await mcp_server.cleanup()

def print_stream(stream):
    for message in stream['messages']:
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()

asyncio.run(run_agent())
