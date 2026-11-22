"""UI-agnostic application core.

This package MUST NOT import any UI framework (PyQt6, etc.) - that rule keeps
the logic reusable across frontends (Qt, CLI, future web/mobile targets).
Import submodules directly (``from core import analyzer``), the package
``__init__`` stays import-light on purpose.
"""
