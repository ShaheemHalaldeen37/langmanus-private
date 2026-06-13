from typing import Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph import MessagesState
from pydantic import BaseModel

from src.config import TEAM_MEMBERS

# ── Planner structured output schema ────────────────────────────────────────

class PlanStep(BaseModel):
    agent_name: str
    title: str
    description: str
    note: Optional[str] = None


class Plan(BaseModel):
    thought: str
    title: str
    steps: list[PlanStep]


# Define routing options
OPTIONS = TEAM_MEMBERS + ["FINISH"]


class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""

    next: Literal[*OPTIONS]


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Constants
    TEAM_MEMBERS: list[str]

    # Runtime Variables
    next: str
    full_plan: str
    deep_thinking_mode: bool
    search_before_planning: bool
