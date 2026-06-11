import asyncio

from pydantic import BaseModel, Field
from typing import Optional, ClassVar, Type
from langchain.tools import BaseTool
from browser_use.agent.views import AgentHistoryList
from browser_use.agent.service import Agent as BrowserAgent
from browser_use.browser.profile import BrowserProfile
from src.tools.decorators import create_logged_tool
from src.config import CHROME_INSTANCE_PATH, VL_MODEL, VL_BASE_URL, VL_API_KEY

# Cap agent steps so a stuck page can't hang the whole workflow
MAX_BROWSER_STEPS = 15

browser_profile = BrowserProfile(
    executable_path=CHROME_INSTANCE_PATH if CHROME_INSTANCE_PATH else None,
    headless=True,
)


def _create_browser_llm():
    """Build a browser-use native LLM from the VL_* env config.

    browser-use >= 0.3 no longer accepts LangChain chat models; it ships its
    own provider wrappers, so pick one based on the configured base URL.
    """
    base_url = VL_BASE_URL or ""
    if "groq.com" in base_url:
        from browser_use.llm.groq.chat import ChatGroq

        return ChatGroq(model=VL_MODEL, api_key=VL_API_KEY, temperature=0.0)
    if "11434" in base_url or "ollama" in base_url.lower():
        from browser_use.llm.ollama.chat import ChatOllama

        # Ollama's native API lives at the root, not under /v1
        host = base_url.split("/v1")[0]
        return ChatOllama(model=VL_MODEL, host=host)
    from browser_use.llm.openai.chat import ChatOpenAI

    return ChatOpenAI(
        model=VL_MODEL,
        base_url=base_url or None,
        api_key=VL_API_KEY or None,
        temperature=0.0,
    )


browser_llm = _create_browser_llm()


class BrowserUseInput(BaseModel):
    """Input for WriteFileTool."""

    instruction: str = Field(..., description="The instruction to use browser")


class BrowserTool(BaseTool):
    name: ClassVar[str] = "browser"
    args_schema: Type[BaseModel] = BrowserUseInput
    description: ClassVar[str] = (
        "Use this tool to interact with web browsers. Input should be a natural language description of what you want to do with the browser, such as 'Go to google.com and search for browser-use', or 'Navigate to Reddit and find the top post about AI'."
    )

    _agent: Optional[BrowserAgent] = None

    def _run(self, instruction: str) -> str:
        """Run the browser task synchronously."""
        # use_vision/use_judge off: screenshots cost ~12-15k tokens per step and
        # exhaust Groq's 500k tokens-per-day free-tier budget within a few runs.
        # The agent works on the DOM text representation instead.
        self._agent = BrowserAgent(
            task=instruction,
            llm=browser_llm,
            browser_profile=browser_profile
        )
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._agent.run(max_steps=MAX_BROWSER_STEPS)
                )
                return (
                    result.final_result()
                    if isinstance(result, AgentHistoryList)
                    else str(result)
                )
            finally:
                loop.close()
        except Exception as e:
            return f"Error executing browser task: {str(e)}"

    async def _arun(self, instruction: str) -> str:
        """Run the browser task asynchronously."""
        self._agent = BrowserAgent(
            task=instruction,
            llm=browser_llm,
            browser_profile=browser_profile,
            use_vision=False,
            use_judge=False,
        )
        try:
            result = await self._agent.run(max_steps=MAX_BROWSER_STEPS)
            return (
                result.final_result()
                if isinstance(result, AgentHistoryList)
                else str(result)
            )
        except Exception as e:
            return f"Error executing browser task: {str(e)}"


BrowserTool = create_logged_tool(BrowserTool)
browser_tool = BrowserTool()
