"""
BackendInit - Backend project scaffolding.

Provides the `asgard init-backend` command for initialising a standard
backend project structure with opinionated directory layout, boilerplate
files, and coding standards documentation.
"""

from Asgard.BackendInit.service import init_backend

__all__ = ["init_backend"]
