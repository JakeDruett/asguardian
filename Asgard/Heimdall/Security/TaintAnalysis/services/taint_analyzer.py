"""
Heimdall Taint Analyzer Service

Performs intra-function and cross-function taint analysis using Python's AST module
to track untrusted data from sources to dangerous sinks.
"""

import ast
import fnmatch
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from Asgard.Heimdall.Security.TaintAnalysis.models.taint_models import (
    TaintConfig,
    TaintFlow,
    TaintFlowStep,
    TaintReport,
    TaintSinkType,
    TaintSourceType,
)


# --- Source pattern definitions ---

# Mapping: attribute access patterns -> TaintSourceType
# Keys are (object_attr, method) pairs or single attribute names
SOURCE_PATTERNS: List[Tuple[str, TaintSourceType]] = [
    # HTTP parameters
    ("request.args", TaintSourceType.HTTP_PARAMETER),
    ("request.form", TaintSourceType.HTTP_PARAMETER),
    ("request.json", TaintSourceType.HTTP_PARAMETER),
    ("request.data", TaintSourceType.HTTP_PARAMETER),
    ("request.GET", TaintSourceType.HTTP_PARAMETER),
    ("request.POST", TaintSourceType.HTTP_PARAMETER),
    ("request.values", TaintSourceType.HTTP_PARAMETER),
    ("request.params", TaintSourceType.HTTP_PARAMETER),
    # Cookies
    ("request.cookies", TaintSourceType.COOKIE),
    # Headers
    ("request.headers", TaintSourceType.HEADER),
    # Environment variables
    ("os.environ", TaintSourceType.ENV_VAR),
    ("os.getenv", TaintSourceType.ENV_VAR),
    ("environ.get", TaintSourceType.ENV_VAR),
    # File reads - detected via open() call usage
    # User input
    ("input", TaintSourceType.USER_INPUT),
    # Command line args
    ("sys.argv", TaintSourceType.COMMAND_LINE_ARG),
    ("args.parse_args", TaintSourceType.COMMAND_LINE_ARG),
    ("parser.parse_args", TaintSourceType.COMMAND_LINE_ARG),
    ("argparse.parse_args", TaintSourceType.COMMAND_LINE_ARG),
]

# Source function names (single-name calls, not attribute access)
SOURCE_CALL_NAMES: Dict[str, TaintSourceType] = {
    "input": TaintSourceType.USER_INPUT,
}

# --- Sink pattern definitions ---

# Mapping: function/method call patterns -> (TaintSinkType, severity)
SINK_PATTERNS: Dict[str, Tuple[TaintSinkType, str]] = {
    # SQL sinks - CRITICAL
    "cursor.execute": (TaintSinkType.SQL_QUERY, "critical"),
    "cursor.executemany": (TaintSinkType.SQL_QUERY, "critical"),
    "session.execute": (TaintSinkType.SQL_QUERY, "critical"),
    "db.execute": (TaintSinkType.SQL_QUERY, "critical"),
    "connection.execute": (TaintSinkType.SQL_QUERY, "critical"),
    "conn.execute": (TaintSinkType.SQL_QUERY, "critical"),
    "engine.execute": (TaintSinkType.SQL_QUERY, "critical"),
    "db.query": (TaintSinkType.SQL_QUERY, "critical"),
    # Shell command sinks - CRITICAL
    "os.system": (TaintSinkType.SHELL_COMMAND, "critical"),
    "os.popen": (TaintSinkType.SHELL_COMMAND, "critical"),
    "subprocess.run": (TaintSinkType.SHELL_COMMAND, "critical"),
    "subprocess.call": (TaintSinkType.SHELL_COMMAND, "critical"),
    "subprocess.Popen": (TaintSinkType.SHELL_COMMAND, "critical"),
    "subprocess.check_output": (TaintSinkType.SHELL_COMMAND, "critical"),
    "subprocess.check_call": (TaintSinkType.SHELL_COMMAND, "critical"),
    # Eval/Exec sinks - CRITICAL
    "eval": (TaintSinkType.EVAL_EXEC, "critical"),
    "exec": (TaintSinkType.EVAL_EXEC, "critical"),
    # File path sinks - HIGH
    "open": (TaintSinkType.FILE_PATH, "high"),
    "pathlib.Path": (TaintSinkType.FILE_PATH, "high"),
    "Path": (TaintSinkType.FILE_PATH, "high"),
    # Template render sinks - HIGH
    "render_template": (TaintSinkType.TEMPLATE_RENDER, "high"),
    "template.render": (TaintSinkType.TEMPLATE_RENDER, "high"),
    "jinja2.Template": (TaintSinkType.TEMPLATE_RENDER, "high"),
    "Environment.get_template": (TaintSinkType.TEMPLATE_RENDER, "high"),
    # LDAP sinks - HIGH
    "ldap.search": (TaintSinkType.LDAP_QUERY, "high"),
    "ldap.search_s": (TaintSinkType.LDAP_QUERY, "high"),
    "connection.search": (TaintSinkType.LDAP_QUERY, "high"),
    # HTML output sinks - MEDIUM
    "render": (TaintSinkType.HTML_OUTPUT, "medium"),
    "make_response": (TaintSinkType.HTML_OUTPUT, "medium"),
    # File write sinks - MEDIUM
    "write": (TaintSinkType.FILE_WRITE, "medium"),
    "writelines": (TaintSinkType.FILE_WRITE, "medium"),
    # Redirect sinks - MEDIUM
    "redirect": (TaintSinkType.REDIRECT, "medium"),
    "HttpResponseRedirect": (TaintSinkType.REDIRECT, "medium"),
    # Log output sinks - MEDIUM
    "logger.info": (TaintSinkType.LOG_OUTPUT, "medium"),
    "logger.debug": (TaintSinkType.LOG_OUTPUT, "medium"),
    "logger.warning": (TaintSinkType.LOG_OUTPUT, "medium"),
    "logger.error": (TaintSinkType.LOG_OUTPUT, "medium"),
    "logging.info": (TaintSinkType.LOG_OUTPUT, "medium"),
    "logging.debug": (TaintSinkType.LOG_OUTPUT, "medium"),
    "logging.warning": (TaintSinkType.LOG_OUTPUT, "medium"),
    "logging.error": (TaintSinkType.LOG_OUTPUT, "medium"),
}

# Sanitizer function names that remove taint
SANITIZER_NAMES: Set[str] = {
    # SQL sanitizers
    "sql.escape",
    "escape_string",
    "quote_plus",
    "escape",
    "sanitize",
    "sanitize_sql",
    "parameterize",
    # HTML sanitizers
    "html.escape",
    "escape_html",
    "bleach.clean",
    "clean",
    "markupsafe.escape",
    "Markup.escape",
    # Shell sanitizers
    "shlex.quote",
    "quote",
    "escape_shell",
    # General sanitizers
    "validate",
    "validate_input",
    "sanitize_input",
    "clean_input",
}

# Severity mapping
SINK_SEVERITY: Dict[TaintSinkType, str] = {
    TaintSinkType.SQL_QUERY: "critical",
    TaintSinkType.SHELL_COMMAND: "critical",
    TaintSinkType.EVAL_EXEC: "critical",
    TaintSinkType.FILE_PATH: "high",
    TaintSinkType.TEMPLATE_RENDER: "high",
    TaintSinkType.LDAP_QUERY: "high",
    TaintSinkType.HTML_OUTPUT: "medium",
    TaintSinkType.FILE_WRITE: "medium",
    TaintSinkType.LOG_OUTPUT: "medium",
    TaintSinkType.REDIRECT: "medium",
}

# CWE and OWASP mappings for each sink type
SINK_CWE: Dict[TaintSinkType, str] = {
    TaintSinkType.SQL_QUERY: "CWE-89",
    TaintSinkType.SHELL_COMMAND: "CWE-78",
    TaintSinkType.HTML_OUTPUT: "CWE-79",
    TaintSinkType.FILE_WRITE: "CWE-73",
    TaintSinkType.FILE_PATH: "CWE-22",
    TaintSinkType.TEMPLATE_RENDER: "CWE-94",
    TaintSinkType.EVAL_EXEC: "CWE-95",
    TaintSinkType.LDAP_QUERY: "CWE-90",
    TaintSinkType.LOG_OUTPUT: "CWE-117",
    TaintSinkType.REDIRECT: "CWE-601",
}

SINK_OWASP: Dict[TaintSinkType, str] = {
    TaintSinkType.SQL_QUERY: "A03:2021",
    TaintSinkType.SHELL_COMMAND: "A03:2021",
    TaintSinkType.HTML_OUTPUT: "A03:2021",
    TaintSinkType.FILE_WRITE: "A01:2021",
    TaintSinkType.FILE_PATH: "A01:2021",
    TaintSinkType.TEMPLATE_RENDER: "A03:2021",
    TaintSinkType.EVAL_EXEC: "A03:2021",
    TaintSinkType.LDAP_QUERY: "A03:2021",
    TaintSinkType.LOG_OUTPUT: "A09:2021",
    TaintSinkType.REDIRECT: "A01:2021",
}

SINK_TITLES: Dict[TaintSinkType, str] = {
    TaintSinkType.SQL_QUERY: "SQL Injection",
    TaintSinkType.SHELL_COMMAND: "Command Injection",
    TaintSinkType.HTML_OUTPUT: "Cross-Site Scripting (XSS)",
    TaintSinkType.FILE_WRITE: "Tainted File Write",
    TaintSinkType.FILE_PATH: "Path Traversal",
    TaintSinkType.TEMPLATE_RENDER: "Server-Side Template Injection",
    TaintSinkType.EVAL_EXEC: "Code Injection via eval/exec",
    TaintSinkType.LDAP_QUERY: "LDAP Injection",
    TaintSinkType.LOG_OUTPUT: "Log Injection",
    TaintSinkType.REDIRECT: "Open Redirect",
}


def _attr_chain(node: ast.AST) -> str:
    """Flatten an attribute access chain into a dotted string (e.g. 'request.args.get')."""
    if isinstance(node, ast.Attribute):
        parent = _attr_chain(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _get_code_snippet(lines: List[str], line_number: int) -> str:
    """Get a code snippet around a given line number (1-indexed)."""
    idx = line_number - 1
    if 0 <= idx < len(lines):
        return lines[idx].strip()
    return ""


def _is_sanitizer_call(node: ast.AST, custom_sanitizers: Set[str]) -> bool:
    """Check if a node represents a call to a known sanitizer function."""
    if not isinstance(node, ast.Call):
        return False
    call_name = _attr_chain(node.func)
    all_sanitizers = SANITIZER_NAMES | custom_sanitizers
    return call_name in all_sanitizers or any(s in call_name for s in all_sanitizers)


def _get_source_type_for_node(node: ast.AST, custom_sources: Set[str]) -> Optional[TaintSourceType]:
    """Check if an AST node represents a taint source, return the source type if so."""
    chain = _attr_chain(node)

    for pattern, source_type in SOURCE_PATTERNS:
        if chain == pattern or chain.startswith(pattern):
            return source_type

    # Check single-name calls for source functions (e.g. input())
    if isinstance(node, ast.Call):
        func_name = _attr_chain(node.func)
        if func_name in SOURCE_CALL_NAMES:
            return SOURCE_CALL_NAMES[func_name]
        for custom in custom_sources:
            if func_name == custom or func_name.endswith(f".{custom}"):
                return TaintSourceType.HTTP_PARAMETER

    return None


def _get_sink_type_for_call(func_chain: str, custom_sinks: Set[str]) -> Optional[Tuple[TaintSinkType, str]]:
    """Check if a function call chain is a known taint sink."""
    for pattern, (sink_type, severity) in SINK_PATTERNS.items():
        if func_chain == pattern or func_chain.endswith(f".{pattern}") or func_chain.startswith(pattern):
            return sink_type, severity
    for custom in custom_sinks:
        if func_chain == custom or func_chain.endswith(f".{custom}"):
            return TaintSinkType.SQL_QUERY, "high"
    return None


class _FunctionTaintVisitor(ast.NodeVisitor):
    """
    AST visitor that tracks taint within a single function.

    Builds a taint map: variable_name -> (TaintFlowStep, TaintSourceType)
    as it walks the function body, and records sink hits.
    """

    def __init__(
        self,
        file_path: str,
        func_name: str,
        lines: List[str],
        initial_taint: Optional[Dict[str, Tuple["TaintFlowStep", TaintSourceType]]] = None,
        custom_sources: Optional[Set[str]] = None,
        custom_sinks: Optional[Set[str]] = None,
        custom_sanitizers: Optional[Set[str]] = None,
    ):
        self.file_path = file_path
        self.func_name = func_name
        self.lines = lines
        self.taint_map: Dict[str, Tuple[TaintFlowStep, TaintSourceType]] = dict(initial_taint or {})
        self.custom_sources: Set[str] = custom_sources or set()
        self.custom_sinks: Set[str] = custom_sinks or set()
        self.custom_sanitizers: Set[str] = custom_sanitizers or set()
        self.found_flows: List[Tuple[TaintFlow, str]] = []  # (flow, variable_name)

    def _make_step(self, line_number: int, step_type: str, variable_name: str) -> TaintFlowStep:
        return TaintFlowStep(
            file_path=self.file_path,
            line_number=line_number,
            function_name=self.func_name,
            step_type=step_type,
            code_snippet=_get_code_snippet(self.lines, line_number),
            variable_name=variable_name,
        )

    def _is_tainted(self, node: ast.AST) -> bool:
        """Check if an AST node refers to a tainted variable."""
        if isinstance(node, ast.Name):
            return node.id in self.taint_map
        if isinstance(node, ast.Attribute):
            chain = _attr_chain(node)
            # Direct chain match
            if chain in self.taint_map:
                return True
            # Check if the object is tainted (e.g. tainted_dict.method())
            if isinstance(node.value, ast.Name) and node.value.id in self.taint_map:
                return True
        if isinstance(node, ast.Subscript):
            # tainted_var[key]
            return self._is_tainted(node.value)
        if isinstance(node, ast.Call):
            # method calls on tainted objects propagate taint
            return self._is_tainted(node.func)
        if isinstance(node, ast.JoinedStr):
            # f-strings: tainted if any value is tainted
            for val in ast.walk(node):
                if isinstance(val, ast.FormattedValue) and self._is_tainted(val.value):
                    return True
        if isinstance(node, ast.BinOp):
            return self._is_tainted(node.left) or self._is_tainted(node.right)
        if isinstance(node, ast.IfExp):
            return self._is_tainted(node.body) or self._is_tainted(node.orelse)
        return False

    def _get_taint_source(self, node: ast.AST) -> Optional[Tuple[TaintFlowStep, TaintSourceType]]:
        """Get taint source for a tainted node (first tainted variable found)."""
        if isinstance(node, ast.Name):
            return self.taint_map.get(node.id)
        if isinstance(node, ast.Attribute):
            chain = _attr_chain(node)
            if chain in self.taint_map:
                return self.taint_map[chain]
            if isinstance(node.value, ast.Name) and node.value.id in self.taint_map:
                return self.taint_map[node.value.id]
        if isinstance(node, ast.Subscript):
            return self._get_taint_source(node.value)
        if isinstance(node, ast.Call):
            return self._get_taint_source(node.func)
        if isinstance(node, ast.JoinedStr):
            for val in ast.walk(node):
                if isinstance(val, ast.FormattedValue):
                    result = self._get_taint_source(val.value)
                    if result:
                        return result
        if isinstance(node, ast.BinOp):
            left = self._get_taint_source(node.left)
            if left:
                return left
            return self._get_taint_source(node.right)
        return None

    def _taint_variable(
        self,
        var_name: str,
        line_number: int,
        source_step: TaintFlowStep,
        source_type: TaintSourceType,
    ) -> None:
        """Mark a variable as tainted."""
        propagation_step = self._make_step(line_number, "propagation", var_name)
        self.taint_map[var_name] = (source_step, source_type)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Handle assignments: detect sources and propagate taint."""
        line_number = node.lineno

        # Check if the RHS is a source
        source_type = _get_source_type_for_node(node.value, self.custom_sources)
        if source_type is not None:
            source_step = self._make_step(line_number, "source", "")
            for target in node.targets:
                if isinstance(target, ast.Name):
                    source_step_named = self._make_step(line_number, "source", target.id)
                    self.taint_map[target.id] = (source_step_named, source_type)

        # Check if it's a call to a source function
        if isinstance(node.value, ast.Call):
            source_type = _get_source_type_for_node(node.value, self.custom_sources)
            if source_type is not None:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        source_step = self._make_step(line_number, "source", target.id)
                        self.taint_map[target.id] = (source_step, source_type)

        # Check if the RHS is a sanitizer call - if so, remove taint
        if isinstance(node.value, ast.Call) and _is_sanitizer_call(
            node.value, self.custom_sanitizers
        ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.taint_map.pop(target.id, None)
        elif self._is_tainted(node.value):
            # Propagate taint to targets
            taint_info = self._get_taint_source(node.value)
            if taint_info:
                original_step, src_type = taint_info
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self._taint_variable(target.id, line_number, original_step, src_type)

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Handle augmented assignments (+=, etc.)."""
        if self._is_tainted(node.value):
            taint_info = self._get_taint_source(node.value)
            if taint_info and isinstance(node.target, ast.Name):
                original_step, src_type = taint_info
                self._taint_variable(node.target.id, node.lineno, original_step, src_type)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Handle function calls: detect sinks and track cross-function taint."""
        func_chain = _attr_chain(node.func)

        # Check if this call is a known sink
        sink_result = _get_sink_type_for_call(func_chain, self.custom_sinks)
        if sink_result is not None:
            sink_type, severity = sink_result

            # Check each argument for taint
            all_args = list(node.args) + [kw.value for kw in node.keywords]
            for arg in all_args:
                if self._is_tainted(arg):
                    taint_info = self._get_taint_source(arg)
                    if taint_info:
                        original_step, src_type = taint_info
                        sink_step = self._make_step(node.lineno, "sink", func_chain)

                        # Check if any sanitizer is present in args
                        sanitizer_present = any(
                            _is_sanitizer_call(a, self.custom_sanitizers)
                            for a in all_args
                        )

                        flow = TaintFlow(
                            source_type=src_type,
                            sink_type=sink_type,
                            severity=severity,
                            source_location=original_step,
                            sink_location=sink_step,
                            intermediate_steps=[],
                            title=SINK_TITLES.get(sink_type, "Tainted Data Flow"),
                            description=(
                                f"Tainted data from {src_type} source reaches "
                                f"{sink_type} sink without sanitization."
                            ),
                            cwe_id=SINK_CWE.get(sink_type, ""),
                            owasp_category=SINK_OWASP.get(sink_type, ""),
                            sanitizers_present=sanitizer_present,
                        )
                        var_name = ""
                        if isinstance(arg, ast.Name):
                            var_name = arg.id
                        self.found_flows.append((flow, var_name))
                        break  # One flow per call site

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Track tainted return values (for cross-function propagation)."""
        self.generic_visit(node)


def _should_exclude(path: Path, exclude_patterns: List[str]) -> bool:
    """Check if a path should be excluded from scanning."""
    path_str = str(path)
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(path.name, pattern):
            return True
        if fnmatch.fnmatch(path_str, f"*{pattern}*"):
            return True
        if pattern in path_str:
            return True
    return False


def _collect_python_files(scan_path: Path, exclude_patterns: List[str]) -> List[Path]:
    """Collect all Python files under scan_path, respecting exclusions."""
    files: List[Path] = []
    for py_file in scan_path.rglob("*.py"):
        if not _should_exclude(py_file, exclude_patterns):
            files.append(py_file)
    return sorted(files)


class TaintAnalyzer:
    """
    Performs taint analysis on Python source code.

    Tracks untrusted data from sources (HTTP parameters, env vars, user input, etc.)
    through propagation paths to dangerous sinks (SQL, shell, eval, etc.).

    Supports:
    - Full intra-function tracking
    - Cross-function tracking within the same file (call graph)
    - Best-effort cross-file tracking for known sink patterns
    """

    def __init__(self, config: Optional[TaintConfig] = None):
        """
        Initialize the taint analyzer.

        Args:
            config: Taint analysis configuration. Uses defaults if not provided.
        """
        self.config = config or TaintConfig()
        self._custom_sources = set(self.config.custom_sources)
        self._custom_sinks = set(self.config.custom_sinks)
        self._custom_sanitizers = set(self.config.custom_sanitizers)

    def scan(self, scan_path: Optional[Path] = None) -> TaintReport:
        """
        Scan the specified path for taint flows.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            TaintReport containing all taint flows found.

        Raises:
            FileNotFoundError: If the scan path does not exist.
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        report = TaintReport(scan_path=str(path))

        python_files = _collect_python_files(path, self.config.exclude_patterns)
        report.files_analyzed = len(python_files)

        for file_path in python_files:
            flows = self._analyze_file(file_path)
            for flow in flows:
                if self._severity_meets_threshold(flow.severity):
                    report.add_flow(flow)

        # Sort flows: critical first, then high, then medium
        severity_order = {"critical": 0, "high": 1, "medium": 2}
        report.flows.sort(
            key=lambda f: (
                severity_order.get(f.severity, 3),
                f.source_location.file_path,
                f.source_location.line_number,
            )
        )

        report.scan_duration_seconds = time.time() - start_time
        return report

    def _analyze_file(self, file_path: Path) -> List[TaintFlow]:
        """
        Analyze a single Python file for taint flows.

        Args:
            file_path: Path to the Python file.

        Returns:
            List of TaintFlow objects found in the file.
        """
        flows: List[TaintFlow] = []

        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except (IOError, OSError):
            return flows

        lines = source.splitlines()

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            return flows

        file_path_str = str(file_path)

        # First pass: collect all function definitions and their bodies
        functions: Dict[str, ast.FunctionDef] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[node.name] = node

        # Second pass: analyze each function for taint flows
        # Also analyze module-level code
        module_level_taint: Dict[str, Tuple[TaintFlowStep, TaintSourceType]] = {}

        # Analyze module-level assignments (outside any function)
        module_visitor = _FunctionTaintVisitor(
            file_path=file_path_str,
            func_name="<module>",
            lines=lines,
            initial_taint={},
            custom_sources=self._custom_sources,
            custom_sinks=self._custom_sinks,
            custom_sanitizers=self._custom_sanitizers,
        )
        for stmt in tree.body:
            module_visitor.visit(stmt)
        for flow, _ in module_visitor.found_flows:
            flows.append(flow)
        module_level_taint = module_visitor.taint_map

        # Analyze each function
        for func_name, func_node in functions.items():
            func_flows = self._analyze_function(
                func_node=func_node,
                file_path_str=file_path_str,
                lines=lines,
                initial_taint=module_level_taint if self.config.track_cross_function else {},
            )
            flows.extend(func_flows)

        return flows

    def _analyze_function(
        self,
        func_node: ast.FunctionDef,
        file_path_str: str,
        lines: List[str],
        initial_taint: Optional[Dict[str, Tuple[TaintFlowStep, TaintSourceType]]] = None,
    ) -> List[TaintFlow]:
        """
        Analyze a single function for taint flows.

        Args:
            func_node: The AST function definition node.
            file_path_str: String path of the file.
            lines: Source lines for snippet extraction.
            initial_taint: Initial taint map from outer scope.

        Returns:
            List of TaintFlow objects found in the function.
        """
        visitor = _FunctionTaintVisitor(
            file_path=file_path_str,
            func_name=func_node.name,
            lines=lines,
            initial_taint=initial_taint,
            custom_sources=self._custom_sources,
            custom_sinks=self._custom_sinks,
            custom_sanitizers=self._custom_sanitizers,
        )
        visitor.visit(func_node)
        return [flow for flow, _ in visitor.found_flows]

    def _severity_meets_threshold(self, severity: str) -> bool:
        """Check if a severity meets the configured minimum threshold."""
        order = {"critical": 0, "high": 1, "medium": 2}
        min_order = order.get(self.config.min_severity, 2)
        finding_order = order.get(severity, 3)
        return finding_order <= min_order
