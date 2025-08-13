from typing import Callable, Optional, Dict, Any
from pydantic import BaseModel, ValidationError

class MCPRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, func: Callable, description: str = "", input_model: Optional[BaseModel] = None):
        if name in self.tools:
            raise ValueError(f"Tool {name} already registered")
        self.tools[name] = {"func": func, "description": description, "input_model": input_model}

    def call(self, name: str, **kwargs):
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not registered")
        entry = self.tools[name]
        model = entry.get("input_model")
        if model:
            try:
                validated = model(**kwargs)
                return entry["func"](**validated.dict())
            except ValidationError as e:
                raise e
        else:
            return entry["func"](**kwargs)
