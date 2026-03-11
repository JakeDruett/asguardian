"""
Heimdall TypeScript Analysis Models

Re-exports shared JS models for use in TypeScript analysis, and provides
a TypeScript-specific configuration that extends the base JSAnalysisConfig
with TypeScript-appropriate defaults.
"""

from Asgard.Heimdall.Quality.languages.javascript.models.js_models import (
    JSAnalysisConfig,
    JSFinding,
    JSReport,
    JSRuleCategory,
    JSSeverity,
)


class TSAnalysisConfig(JSAnalysisConfig):
    """
    Configuration for TypeScript analysis.

    Extends JSAnalysisConfig with TypeScript-appropriate default extensions
    and sets the language field to 'typescript'.
    """

    class Config:
        use_enum_values = True

    def __init__(self, **data):
        if "include_extensions" not in data:
            data["include_extensions"] = [".ts", ".tsx"]
        if "language" not in data:
            data["language"] = "typescript"
        super().__init__(**data)


__all__ = [
    "JSAnalysisConfig",
    "JSFinding",
    "JSReport",
    "JSRuleCategory",
    "JSSeverity",
    "TSAnalysisConfig",
]
