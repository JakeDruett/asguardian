"""
Heimdall language-specific analysis subpackage.

Provides static analysis for languages that cannot use Python's ast module:
- javascript: Regex-based analysis for .js and .jsx files
- typescript: Extends JavaScript analysis with TypeScript-specific rules for .ts and .tsx
- shell: Regex-based analysis for .sh, .bash, and shebang-identified shell scripts
"""

from Asgard.Heimdall.Quality.languages.javascript.models.js_models import (
    JSAnalysisConfig,
    JSFinding,
    JSReport,
    JSRuleCategory,
    JSSeverity,
)
from Asgard.Heimdall.Quality.languages.javascript.services.js_analyzer import JSAnalyzer
from Asgard.Heimdall.Quality.languages.typescript.models.ts_models import TSAnalysisConfig
from Asgard.Heimdall.Quality.languages.typescript.services.ts_analyzer import TSAnalyzer
from Asgard.Heimdall.Quality.languages.shell.models.shell_models import (
    ShellAnalysisConfig,
    ShellFinding,
    ShellReport,
    ShellRuleCategory,
    ShellSeverity,
)
from Asgard.Heimdall.Quality.languages.shell.services.shell_analyzer import ShellAnalyzer

__all__ = [
    # JavaScript
    "JSAnalysisConfig",
    "JSAnalyzer",
    "JSFinding",
    "JSReport",
    "JSRuleCategory",
    "JSSeverity",
    # TypeScript
    "TSAnalysisConfig",
    "TSAnalyzer",
    # Shell
    "ShellAnalysisConfig",
    "ShellAnalyzer",
    "ShellFinding",
    "ShellReport",
    "ShellRuleCategory",
    "ShellSeverity",
]
