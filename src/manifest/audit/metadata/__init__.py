"""
Metadata: blueprint loading from manifest dir.

No architecture dict or architecture.json. Use blueprint + entity_schema helpers.
"""
from .architecture_metadata import load_blueprint

__all__ = [
    "load_blueprint",
]
