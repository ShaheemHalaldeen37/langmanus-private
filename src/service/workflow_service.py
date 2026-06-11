import asyncio
import logging
import re

from src.config import TEAM_MEMBERS
from src.graph import build_graph
from langchain_community.adapters.openai import convert_message_to_dict
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()


def _strip_think(text: str) -> str:
    """Remove inline <think>…</think> blocks emitted by reasoning models."""
    return re.sub(r"<think>.*?(</think>|$)", "", text, flags=re.S).strip()


def _extract_node_message(output) -> str | None:
    """Pull the message content out of a node's Command output, if any."""
    update = getattr(output, "update", None)
    if isinstance(update, dict):
        messages = update.get("messages") or []
        if messages:
            return getattr(messages[-1], "content", None)
    return None


async def run_agent_workflow(
    user_input_messages: list,
    debug: bool = False,
    deep_thinking_mode: bool = False,
    search_before_planning: bool = False,
):
    """Run the agent workflow with the given user input.

    Args:
        user_input_messages: The user request messages
        debug: If True, enables debug level logging

    Returns:
        The final state after the workflow completes
    """
    if not user_input_messages:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"Starting workflow with user input: {user_input_messages}")

    workflow_id = str(uuid.uuid4())

    streaming_llm_agents = [*TEAM_MEMBERS, "planner", "coordinator"]

    # Coordinator output is buffered (not streamed) so we can strip <think>
    # blocks and suppress the internal handoff_to_planner() marker reliably.
    coordinator_buffer = ""

    try:
        # TODO: extract message content from object, specifically for on_chat_model_stream
        async for event in graph.astream_events(
            {
                # Constants
                "TEAM_MEMBERS": TEAM_MEMBERS,
                # Runtime Variables
                "messages": user_input_messages,
                "deep_thinking_mode": deep_thinking_mode,
                "search_before_planning": search_before_planning,
            },
            version="v2",
        ):
            kind = event.get("event")
            data = event.get("data")
            name = event.get("name")
            metadata = event.get("metadata")
            node = (
                ""
                if (metadata.get("checkpoint_ns") is None)
                else metadata.get("checkpoint_ns").split(":")[0]
            )
            langgraph_step = (
                ""
                if (metadata.get("langgraph_step") is None)
                else str(metadata["langgraph_step"])
            )
            run_id = "" if (event.get("run_id") is None) else str(event["run_id"])

            if kind == "on_chain_start" and name in streaming_llm_agents:
                if name == "planner":
                    yield {
                        "event": "start_of_workflow",
                        "data": {
                            "workflow_id": workflow_id,
                            "input": user_input_messages,
                        },
                    }
                ydata = {
                    "event": "start_of_agent",
                    "data": {
                        "agent_name": name,
                        "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                    },
                }
            elif kind == "on_chain_end" and name in streaming_llm_agents:
                if name == "coordinator":
                    # Emit the buffered greeting only when it's a direct reply,
                    # not an internal handoff to the planner.
                    cleaned = _strip_think(coordinator_buffer)
                    coordinator_buffer = ""
                    if cleaned and "handoff_to_planner" not in cleaned:
                        yield {
                            "event": "message",
                            "data": {
                                "message_id": f"{workflow_id}_coordinator",
                                "delta": {"content": cleaned},
                            },
                        }
                elif name == "planner":
                    # The plan is produced via structured output, so it never
                    # appears in the content stream — emit it explicitly for
                    # the UI to render.
                    plan_text = _extract_node_message(data.get("output"))
                    if plan_text:
                        yield {
                            "event": "message",
                            "data": {
                                "message_id": f"{workflow_id}_plan",
                                "delta": {"content": plan_text},
                            },
                        }
                ydata = {
                    "event": "end_of_agent",
                    "data": {
                        "agent_name": name,
                        "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                    },
                }
            elif kind == "on_chat_model_start" and node in streaming_llm_agents:
                ydata = {
                    "event": "start_of_llm",
                    "data": {"agent_name": node},
                }
            elif kind == "on_chat_model_end" and node in streaming_llm_agents:
                ydata = {
                    "event": "end_of_llm",
                    "data": {"agent_name": node},
                }
            elif kind == "on_chat_model_stream" and node == "coordinator":
                content = data["chunk"].content
                if content:
                    coordinator_buffer += content
                continue
            elif kind == "on_chat_model_stream" and node in streaming_llm_agents:
                content = data["chunk"].content
                if content is None or content == "":
                    if not data["chunk"].additional_kwargs.get("reasoning_content"):
                        # Skip empty messages
                        continue
                    ydata = {
                        "event": "message",
                        "data": {
                            "message_id": data["chunk"].id,
                            "delta": {
                                "reasoning_content": (
                                    data["chunk"].additional_kwargs[
                                        "reasoning_content"
                                    ]
                                )
                            },
                        },
                    }
                else:
                    ydata = {
                        "event": "message",
                        "data": {
                            "message_id": data["chunk"].id,
                            "delta": {"content": content},
                        },
                    }
            elif kind == "on_tool_start" and node in TEAM_MEMBERS:
                ydata = {
                    "event": "tool_call",
                    "data": {
                        "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                        "tool_name": name,
                        "tool_input": data.get("input"),
                    },
                }
            elif kind == "on_tool_end" and node in TEAM_MEMBERS:
                ydata = {
                    "event": "tool_call_result",
                    "data": {
                        "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                        "tool_name": name,
                        "tool_result": (
                            data["output"].content if data.get("output") else ""
                        ),
                    },
                }
            else:
                continue
            yield ydata
    except asyncio.CancelledError:
        raise
    except Exception as e:
        # Surface the failure to the client instead of killing the stream
        logger.exception("Workflow execution failed")
        yield {
            "event": "error",
            "data": {"workflow_id": workflow_id, "message": str(e)},
        }

    yield {
        "event": "end_of_workflow",
        "data": {"workflow_id": workflow_id},
    }
