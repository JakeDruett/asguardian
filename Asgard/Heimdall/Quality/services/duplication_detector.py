"""
Heimdall Duplication Detector Service

Detects code duplication using token-based analysis and similarity algorithms.

Duplication Types:
- Type 1 (Exact): Identical code blocks
- Type 2 (Structural): Same structure with different variable names
- Type 3 (Similar): Similar code with modifications
"""

import ast
import difflib
import hashlib
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from Asgard.Heimdall.Quality.models.duplication_models import (
    CloneFamily,
    CodeBlock,
    DuplicationConfig,
    DuplicationMatch,
    DuplicationResult,
    DuplicationType,
)
from Asgard.Heimdall.Quality.utilities.file_utils import scan_directory


class DuplicationDetector:
    """
    Detects code duplication using token-based analysis.

    Supports:
    - Exact match detection (Type 1 clones)
    - Structural similarity detection (Type 2 clones)
    - Near-miss detection (Type 3 clones)
    """

    # Python keywords and builtins preserved during normalization
    PYTHON_KEYWORDS = {
        'class', 'def', 'return', 'if', 'else', 'elif', 'for', 'while',
        'import', 'from', 'as', 'try', 'except', 'finally', 'with',
        'not', 'and', 'or', 'in', 'is', 'None', 'True', 'False',
        'pass', 'break', 'continue', 'raise', 'yield', 'lambda', 'async', 'await',
        'del', 'global', 'nonlocal', 'assert',
    }

    def __init__(self, config: Optional[DuplicationConfig] = None):
        """
        Initialize the duplication detector.

        Args:
            config: Detection configuration. Uses defaults if not provided.
        """
        self.config = config or DuplicationConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> DuplicationResult:
        """
        Perform duplication analysis on the specified path.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            DuplicationResult containing all findings
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        result = DuplicationResult(
            scan_path=str(path),
            min_block_size=self.config.min_block_size,
            similarity_threshold=self.config.similarity_threshold,
        )

        # Collect all code blocks from files
        all_blocks: List[CodeBlock] = []
        files_scanned = 0
        total_lines = 0

        # Build exclude patterns
        exclude_patterns = list(self.config.exclude_patterns)
        if not self.config.include_tests:
            exclude_patterns.extend(["test_", "_test.py", "tests/", "conftest.py"])

        # Scan files
        for file_path in scan_directory(
            path,
            exclude_patterns=exclude_patterns,
            include_extensions=self.config.include_extensions,
        ):
            if files_scanned >= self.config.max_files:
                break

            try:
                blocks, line_count = self._extract_blocks_from_file(file_path, path)
                all_blocks.extend(blocks)
                total_lines += line_count
                files_scanned += 1
            except Exception:
                continue

        result.total_files_scanned = files_scanned
        result.total_blocks_analyzed = len(all_blocks)

        # Find clone families
        if all_blocks:
            clone_families = self._find_clone_families(all_blocks)
            for family in clone_families:
                result.add_clone_family(family)

        # Calculate duplication percentage
        if total_lines > 0:
            result.duplication_percentage = (result.total_duplicated_lines / total_lines) * 100

        result.scan_duration_seconds = time.time() - start_time

        # Sort families by severity
        result.clone_families.sort(
            key=lambda f: (f.block_count, f.total_duplicated_lines),
            reverse=True
        )

        return result

    def _extract_blocks_from_file(
        self, file_path: Path, root_path: Path
    ) -> Tuple[List[CodeBlock], int]:
        """
        Extract code blocks from a single file.

        Args:
            file_path: Path to the file
            root_path: Root path for relative path calculation

        Returns:
            Tuple of (list of code blocks, total lines in file)
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return [], 0

        lines = content.splitlines()
        total_lines = len(lines)

        if total_lines < self.config.min_block_size:
            return [], total_lines

        blocks: List[CodeBlock] = []
        relative_path = str(file_path.relative_to(root_path))

        # Use function/class boundaries for Python files
        if file_path.suffix == ".py":
            blocks = self._extract_python_blocks(
                content, lines, str(file_path), relative_path
            )
        else:
            # Fall back to sliding window for other files
            blocks = self._extract_sliding_window_blocks(
                lines, str(file_path), relative_path
            )

        return blocks, total_lines

    def _extract_python_blocks(
        self, content: str, lines: List[str], file_path: str, relative_path: str
    ) -> List[CodeBlock]:
        """Extract code blocks based on Python function/class boundaries."""
        blocks: List[CodeBlock] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fall back to sliding window if parsing fails
            return self._extract_sliding_window_blocks(lines, file_path, relative_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                start_line = node.lineno
                end_line = node.end_lineno or start_line

                if end_line - start_line + 1 >= self.config.min_block_size:
                    block_lines = lines[start_line - 1:end_line]
                    block_content = "\n".join(block_lines)

                    # For classes, use method-name fingerprint instead of full
                    # token content. Two classes are only duplicates if they
                    # share the same set of method names, not just structure.
                    method_names = sorted(
                        n.name for n in ast.walk(node)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    hash_value = self._hash_tokens(method_names)
                    normalized = [node.name] + method_names

                    blocks.append(CodeBlock(
                        file_path=file_path,
                        relative_path=relative_path,
                        start_line=start_line,
                        end_line=end_line,
                        content=block_content,
                        tokens=self._tokenize(block_content),
                        normalized_tokens=normalized,
                        hash_value=hash_value,
                        line_count=end_line - start_line + 1,
                    ))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip methods already nested inside a class
                if self._is_nested_in_class(node, tree):
                    continue

                start_line = node.lineno
                end_line = node.end_lineno or start_line

                if end_line - start_line + 1 >= self.config.min_block_size:
                    block_lines = lines[start_line - 1:end_line]
                    block_content = "\n".join(block_lines)

                    tokens = self._tokenize(block_content)
                    normalized = self._normalize_tokens(tokens)
                    hash_value = self._hash_tokens(normalized)

                    blocks.append(CodeBlock(
                        file_path=file_path,
                        relative_path=relative_path,
                        start_line=start_line,
                        end_line=end_line,
                        content=block_content,
                        tokens=tokens,
                        normalized_tokens=normalized,
                        hash_value=hash_value,
                        line_count=end_line - start_line + 1,
                    ))

        return blocks

    @staticmethod
    def _is_nested_in_class(node: ast.AST, tree: ast.Module) -> bool:
        """Check if a function node is defined inside a class body."""
        for cls_node in ast.walk(tree):
            if isinstance(cls_node, ast.ClassDef):
                for child in ast.walk(cls_node):
                    if child is node and child is not cls_node:
                        return True
        return False

    def _extract_sliding_window_blocks(
        self, lines: List[str], file_path: str, relative_path: str
    ) -> List[CodeBlock]:
        """Extract code blocks using sliding window approach."""
        blocks: List[CodeBlock] = []
        min_size = self.config.min_block_size

        # Use a step to avoid too many overlapping blocks
        step = max(1, min_size // 2)

        for start in range(0, len(lines) - min_size + 1, step):
            end = start + min_size
            block_lines = lines[start:end]
            block_content = "\n".join(block_lines)

            # Skip blocks that are mostly empty or comments
            if not self._is_meaningful_block(block_lines):
                continue

            tokens = self._tokenize(block_content)
            normalized = self._normalize_tokens(tokens)
            hash_value = self._hash_tokens(normalized)

            blocks.append(CodeBlock(
                file_path=file_path,
                relative_path=relative_path,
                start_line=start + 1,
                end_line=end,
                content=block_content,
                tokens=tokens,
                normalized_tokens=normalized,
                hash_value=hash_value,
                line_count=min_size,
            ))

        return blocks

    def _tokenize(self, content: str) -> List[str]:
        """Tokenize code content."""
        # Split by whitespace and common delimiters
        tokens = re.findall(r'\w+|[^\w\s]', content)
        return [t.strip() for t in tokens if t.strip()]

    def _normalize_tokens(self, tokens: List[str]) -> List[str]:
        """Normalize tokens for structural comparison.

        Preserves Python keywords and operators to maintain structural
        distinction between different code blocks. Only normalizes
        user-defined identifiers, numbers, and string literals.
        """
        normalized = []
        for token in tokens:
            if token in self.PYTHON_KEYWORDS:
                normalized.append(token)
            elif re.match(r'^[a-zA-Z_]\w*$', token):
                normalized.append('IDENT')
            elif re.match(r'^\d+\.?\d*$', token):
                normalized.append('NUM')
            elif re.match(r'^["\']', token):
                normalized.append('STR')
            elif token.startswith('#') or token.startswith('//'):
                continue
            else:
                normalized.append(token)
        return normalized

    def _hash_tokens(self, tokens: List[str]) -> str:
        """Calculate hash of token sequence."""
        token_string = "".join(tokens)
        return hashlib.md5(token_string.encode()).hexdigest()

    def _is_meaningful_block(self, lines: List[str]) -> bool:
        """Check if block contains meaningful code."""
        meaningful = 0
        for line in lines:
            stripped = line.strip()
            # Skip empty lines, comments, and very short lines
            if stripped and not stripped.startswith("#") and len(stripped) > 3:
                meaningful += 1
        return meaningful >= self.config.min_block_size // 2

    def _find_clone_families(self, blocks: List[CodeBlock]) -> List[CloneFamily]:
        """
        Find clone families among code blocks.

        Groups blocks by similarity into clone families.
        """
        families: List[CloneFamily] = []
        used_blocks: Set[int] = set()

        # First pass: Group by exact hash (Type 1)
        hash_groups: Dict[str, List[int]] = defaultdict(list)
        for i, block in enumerate(blocks):
            hash_groups[block.hash_value].append(i)

        for hash_value, indices in hash_groups.items():
            if len(indices) >= 2:
                family = CloneFamily(
                    match_type=DuplicationType.EXACT,
                    average_similarity=1.0,
                    severity=CloneFamily.calculate_severity(len(indices)),
                )
                for idx in indices:
                    family.add_block(blocks[idx])
                    used_blocks.add(idx)
                families.append(family)

        # Second pass: Find structural similarities (Type 2/3)
        remaining = [i for i in range(len(blocks)) if i not in used_blocks]

        for i in range(len(remaining)):
            if remaining[i] in used_blocks:
                continue

            idx_i = remaining[i]
            similar_indices = [idx_i]

            for j in range(i + 1, len(remaining)):
                if remaining[j] in used_blocks:
                    continue

                idx_j = remaining[j]
                similarity = self._calculate_similarity(blocks[idx_i], blocks[idx_j])

                if similarity >= self.config.similarity_threshold:
                    similar_indices.append(idx_j)
                    used_blocks.add(idx_j)

            if len(similar_indices) >= 2:
                used_blocks.add(idx_i)
                avg_similarity = sum(
                    self._calculate_similarity(blocks[idx_i], blocks[k])
                    for k in similar_indices[1:]
                ) / (len(similar_indices) - 1) if len(similar_indices) > 1 else 1.0

                match_type = (
                    DuplicationType.STRUCTURAL if avg_similarity > 0.9
                    else DuplicationType.SIMILAR
                )

                family = CloneFamily(
                    match_type=match_type,
                    average_similarity=avg_similarity,
                    severity=CloneFamily.calculate_severity(len(similar_indices)),
                )
                for idx in similar_indices:
                    family.add_block(blocks[idx])
                families.append(family)

        return families

    def _calculate_similarity(self, block1: CodeBlock, block2: CodeBlock) -> float:
        """Calculate similarity between two code blocks."""
        matcher = difflib.SequenceMatcher(
            None, block1.normalized_tokens, block2.normalized_tokens
        )
        return matcher.ratio()

    def generate_report(self, result: DuplicationResult, output_format: str = "text") -> str:
        """
        Generate formatted duplication analysis report.

        Args:
            result: DuplicationResult to format
            output_format: Report format - text, json, or markdown

        Returns:
            Formatted report string

        Raises:
            ValueError: If output format is not supported
        """
        format_lower = output_format.lower()
        if format_lower == "json":
            return self._generate_json_report(result)
        elif format_lower in ("markdown", "md"):
            return self._generate_markdown_report(result)
        elif format_lower == "text":
            return self._generate_text_report(result)
        else:
            raise ValueError(f"Unsupported format: {output_format}. Use: text, json, markdown")

    def _generate_text_report(self, result: DuplicationResult) -> str:
        """Generate plain text duplication report."""
        lines = [
            "=" * 70,
            "  HEIMDALL DUPLICATION DETECTION REPORT",
            "=" * 70,
            "",
            f"  Scan Path:    {result.scan_path}",
            f"  Scanned At:   {result.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Duration:     {result.scan_duration_seconds:.2f}s",
            "",
            "-" * 70,
            "  SUMMARY",
            "-" * 70,
            "",
            f"  Files Scanned:        {result.total_files_scanned}",
            f"  Blocks Analyzed:      {result.total_blocks_analyzed}",
            f"  Clone Families:       {result.total_clone_families}",
            f"  Duplicated Lines:     {result.total_duplicated_lines}",
            f"  Duplication:          {result.duplication_percentage:.1f}%",
            f"  Min Block Size:       {result.min_block_size} lines",
            "",
        ]

        if result.has_duplicates:
            lines.extend(["-" * 70, "  CLONE FAMILIES (worst first)", "-" * 70, ""])
            for i, family in enumerate(result.worst_families, 1):
                sev = family.severity if isinstance(family.severity, str) else family.severity.value
                mtype = family.match_type if isinstance(family.match_type, str) else family.match_type.value
                lines.append(f"  Family {i}: [{sev.upper()}] {mtype} ({family.block_count} copies, {family.total_duplicated_lines} lines)")
                for block in family.blocks[:5]:
                    lines.append(f"    {block.relative_path}:{block.start_line}-{block.end_line}")
                if len(family.blocks) > 5:
                    lines.append(f"    ... and {len(family.blocks) - 5} more")
                lines.append("")

            if result.files_with_duplicates:
                lines.extend(["-" * 70, "  FILES WITH DUPLICATES", "-" * 70, ""])
                for f in result.files_with_duplicates[:20]:
                    lines.append(f"  {f}")
                lines.append("")
        else:
            lines.extend(["  No code duplication detected.", ""])

        lines.extend(["=" * 70, ""])
        return "\n".join(lines)

    def _generate_json_report(self, result: DuplicationResult) -> str:
        """Generate JSON duplication report."""
        families_data = []
        for family in result.clone_families:
            blocks_data = [
                {
                    "file_path": b.file_path,
                    "relative_path": b.relative_path,
                    "start_line": b.start_line,
                    "end_line": b.end_line,
                    "line_count": b.line_count,
                }
                for b in family.blocks
            ]
            families_data.append({
                "match_type": family.match_type if isinstance(family.match_type, str) else family.match_type.value,
                "severity": family.severity if isinstance(family.severity, str) else family.severity.value,
                "block_count": family.block_count,
                "total_duplicated_lines": family.total_duplicated_lines,
                "average_similarity": round(family.average_similarity, 3),
                "blocks": blocks_data,
            })

        report_data = {
            "scan_info": {
                "scan_path": result.scan_path,
                "scanned_at": result.scanned_at.isoformat(),
                "duration_seconds": result.scan_duration_seconds,
                "min_block_size": result.min_block_size,
                "similarity_threshold": result.similarity_threshold,
            },
            "summary": {
                "total_files_scanned": result.total_files_scanned,
                "total_blocks_analyzed": result.total_blocks_analyzed,
                "total_clone_families": result.total_clone_families,
                "total_duplicated_lines": result.total_duplicated_lines,
                "duplication_percentage": round(result.duplication_percentage, 2),
                "files_with_duplicates": result.files_with_duplicates,
            },
            "clone_families": families_data,
        }
        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, result: DuplicationResult) -> str:
        """Generate Markdown duplication report."""
        lines = [
            "# Heimdall Duplication Detection Report",
            "",
            f"**Scan Path:** `{result.scan_path}`",
            f"**Generated:** {result.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {result.scan_duration_seconds:.2f} seconds",
            "",
            "## Summary",
            "",
            f"**Files Scanned:** {result.total_files_scanned}",
            f"**Clone Families:** {result.total_clone_families}",
            f"**Duplicated Lines:** {result.total_duplicated_lines}",
            f"**Duplication Percentage:** {result.duplication_percentage:.1f}%",
            "",
        ]

        if result.has_duplicates:
            lines.extend([
                "## Clone Families",
                "",
                "| # | Type | Severity | Copies | Lines | Similarity |",
                "|---|------|----------|--------|-------|------------|",
            ])
            for i, family in enumerate(result.worst_families, 1):
                sev = family.severity if isinstance(family.severity, str) else family.severity.value
                mtype = family.match_type if isinstance(family.match_type, str) else family.match_type.value
                lines.append(f"| {i} | {mtype} | {sev} | {family.block_count} | {family.total_duplicated_lines} | {family.average_similarity:.0%} |")
            lines.append("")

            if result.files_with_duplicates:
                lines.extend(["## Files With Duplicates", ""])
                for f in result.files_with_duplicates[:20]:
                    lines.append(f"- `{f}`")
                lines.append("")
        else:
            lines.extend(["No code duplication detected.", ""])

        return "\n".join(lines)

    def analyze_single_file(self, file_path: Path) -> DuplicationResult:
        """
        Analyze a single file for internal duplication.

        Args:
            file_path: Path to the file

        Returns:
            DuplicationResult with findings

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")

        start_time = time.time()

        result = DuplicationResult(
            scan_path=str(path.parent),
            min_block_size=self.config.min_block_size,
            similarity_threshold=self.config.similarity_threshold,
        )

        try:
            blocks, total_lines = self._extract_blocks_from_file(path, path.parent)
            result.total_files_scanned = 1
            result.total_blocks_analyzed = len(blocks)

            if blocks:
                clone_families = self._find_clone_families(blocks)
                for family in clone_families:
                    result.add_clone_family(family)

            if total_lines > 0:
                result.duplication_percentage = (
                    result.total_duplicated_lines / total_lines
                ) * 100

        except Exception:
            pass

        result.scan_duration_seconds = time.time() - start_time
        return result
