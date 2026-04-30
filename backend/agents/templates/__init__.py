"""
CrucibAI Template System — Multi-language code generation templates.

This module exports all template generators and the template registry,
allowing agents to select and generate complete project scaffolds for
seven supported language/framework stacks.
"""

from backend.agents.templates.python_fastapi import generate_python_fastapi
from backend.agents.templates.node_express import generate_node_express
from backend.agents.templates.react_vite import generate_react_vite
from backend.agents.templates.python_cli import generate_python_cli
from backend.agents.templates.cpp_cmake import generate_cpp_cmake
from backend.agents.templates.go_gin import generate_go_gin
from backend.agents.templates.rust_axum import generate_rust_axum
from backend.agents.templates.registry import (
    TEMPLATE_REGISTRY,
    select_template,
    list_templates,
)

__all__ = [
    # Generator functions
    "generate_python_fastapi",
    "generate_node_express",
    "generate_react_vite",
    "generate_python_cli",
    "generate_cpp_cmake",
    "generate_go_gin",
    "generate_rust_axum",
    # Registry helpers
    "TEMPLATE_REGISTRY",
    "select_template",
    "list_templates",
]
