from __future__ import annotations

from pydantic import BaseModel
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
try:
    from deepeval.tracing import observe, update_current_trace
except ImportError:
    def observe(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    def update_current_trace(*args, **kwargs):
        pass

from devmate.config import config
from devmate.tasks.task_store import TaskType
from devmate.observability.logger import get_logger
from devmate.observability.metrics_tracker import MetricsCallbackHandler

logger = get_logger(__name__)


class PlannedTask(BaseModel):
    id: str                          # stable snake_case e.g. task_001
    title: str
    description: str
    task_type: TaskType
    depends_on: list[str]            # list of task IDs that must complete first
    estimated_minutes: int
    output_files: list[str]          # files this task will create/modify
    acceptance_criteria: list[str]   # what "done" looks like for the judge


class ExecutionPlan(BaseModel):
    project_name: str
    goal_summary: str
    tech_stack: list[str]
    total_estimated_hours: float
    tasks: list[PlannedTask]
    risks: list[str]
    assumptions: list[str]


_SYSTEM_PROMPT = """\
You are a senior software architect. Given a software goal, produce a detailed
ExecutionPlan broken into concrete tasks for an AI agent to implement.

Rules:
- 5 to 20 tasks
- Task IDs must be stable snake_case: task_001, task_002, ...
- depends_on must reference valid task IDs in the same plan
- Ordering must form a valid DAG (no cycles): architecture -> schema -> config -> core -> tests -> integration
- output_files must list every file the task will write to disk
- acceptance_criteria must be concrete and verifiable (3-5 items per task)
- task_type must be one of: design, implement, test, review, integrate, configure
"""


@observe(type="agent", name="task_planner")
def create_plan(goal: str, extra_context: str = "") -> ExecutionPlan:
    """Call the LLM planner and return a structured ExecutionPlan using low-cost model."""
    provider = config.get("llm", {}).get("provider", "openai")
    model = config.get("llm", {}).get("model", "gpt-4o-mini")

    llm = init_chat_model(f"{provider}:{model}", temperature=0)

    planner_agent = create_agent(
        llm,
        tools=[],
        system_prompt=_SYSTEM_PROMPT,
        response_format=ExecutionPlan,
    )

    user_message = f"Goal: {goal}"
    if extra_context:
        user_message += f"\n\nAdditional context / change requests:\n{extra_context}"

    result = planner_agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"callbacks": [MetricsCallbackHandler()]},
    )
    plan: ExecutionPlan = result["structured_response"]
    logger.info(f"Plan created: {plan.project_name} with {len(plan.tasks)} tasks")

    update_current_trace(input=user_message, output=plan.model_dump_json(indent=2))
    return plan
