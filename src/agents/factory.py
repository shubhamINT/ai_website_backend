from typing import Type
from src.agents.base import BaseAgent
from src.agents.indusnet.agent import IndusNetAgent

_AGENT_CLASSES = {
    "indusnet": IndusNetAgent,
}

def get_agent_class(agent_type: str) -> Type[BaseAgent]:
    return _AGENT_CLASSES.get(agent_type, IndusNetAgent)
