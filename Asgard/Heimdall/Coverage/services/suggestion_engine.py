"""
Heimdall Suggestion Engine Service

Generates test suggestions for uncovered code.
"""

from pathlib import Path
from typing import List, Optional

from Asgard.Heimdall.Coverage.models.coverage_models import (
    CoverageConfig,
    CoverageGap,
    CoverageSeverity,
    MethodInfo,
    MethodType,
    SuggestionPriority,
    TestSuggestion,
)


class SuggestionEngine:
    """
    Generates test suggestions for uncovered code.

    Creates targeted test suggestions based on:
    - Method characteristics
    - Code complexity
    - Parameter types
    - Common patterns
    """

    def __init__(self, config: Optional[CoverageConfig] = None):
        """Initialize the suggestion engine."""
        self.config = config or CoverageConfig()

    def generate_suggestions(
        self,
        gaps: List[CoverageGap]
    ) -> List[TestSuggestion]:
        """
        Generate test suggestions for coverage gaps.

        Args:
            gaps: List of coverage gaps

        Returns:
            List of test suggestions
        """
        suggestions = []

        for gap in gaps:
            method = gap.method
            suggestion = self._create_suggestion(method, gap)
            suggestions.append(suggestion)

        # Sort by priority
        priority_order = {
            SuggestionPriority.URGENT: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3,
        }
        suggestions.sort(key=lambda s: priority_order[s.priority])

        return suggestions

    def _create_suggestion(
        self,
        method: MethodInfo,
        gap: CoverageGap
    ) -> TestSuggestion:
        """Create a test suggestion for a method."""
        priority = self._calculate_priority(method, gap)
        test_name = self._generate_test_name(method)
        test_type = self._determine_test_type(method)
        description = self._generate_description(method)
        test_cases = self._generate_test_cases(method)
        rationale = self._generate_rationale(method, gap)

        return TestSuggestion(
            method=method,
            test_name=test_name,
            test_type=test_type,
            priority=priority,
            description=description,
            test_cases=test_cases,
            rationale=rationale,
        )

    def _calculate_priority(
        self,
        method: MethodInfo,
        gap: CoverageGap
    ) -> SuggestionPriority:
        """Calculate suggestion priority."""
        if gap.severity == CoverageSeverity.CRITICAL:
            return SuggestionPriority.URGENT
        elif gap.severity == CoverageSeverity.HIGH:
            return SuggestionPriority.HIGH
        elif gap.severity == CoverageSeverity.MODERATE:
            return SuggestionPriority.MEDIUM
        else:
            return SuggestionPriority.LOW

    def _generate_test_name(self, method: MethodInfo) -> str:
        """Generate a test function name."""
        if method.class_name:
            return f"test_{method.class_name.lower()}_{method.name}"
        return f"test_{method.name}"

    def _determine_test_type(self, method: MethodInfo) -> str:
        """Determine the type of test needed."""
        if method.is_async:
            return "async_unit_test"
        elif method.method_type == MethodType.PROPERTY:
            return "property_test"
        elif method.method_type == MethodType.CLASSMETHOD:
            return "classmethod_test"
        elif method.method_type == MethodType.STATICMETHOD:
            return "staticmethod_test"
        elif method.has_branches and method.branch_count > 3:
            return "parametrized_test"
        else:
            return "unit_test"

    def _generate_description(self, method: MethodInfo) -> str:
        """Generate a description for the test."""
        parts = []

        if method.is_async:
            parts.append("async")

        if method.method_type == MethodType.PROPERTY:
            parts.append("property")
        elif method.method_type == MethodType.CLASSMETHOD:
            parts.append("class method")
        elif method.method_type == MethodType.STATICMETHOD:
            parts.append("static method")
        else:
            parts.append("method")

        type_str = " ".join(parts)

        if method.class_name:
            return f"Test the {type_str} '{method.name}' in {method.class_name}"
        return f"Test the {type_str} '{method.name}'"

    def _generate_test_cases(self, method: MethodInfo) -> List[str]:
        """Generate suggested test cases."""
        cases = []

        # Basic test case
        cases.append(f"Test {method.name} with valid input")

        # Parameter-based cases
        if method.parameter_count > 0:
            cases.append(f"Test {method.name} with invalid parameters")
            if method.parameter_count > 1:
                cases.append(f"Test {method.name} with partial parameters")

        # Branch-based cases
        if method.has_branches:
            if method.branch_count <= 3:
                for i in range(method.branch_count):
                    cases.append(f"Test {method.name} branch {i + 1}")
            else:
                cases.append(f"Test {method.name} true path")
                cases.append(f"Test {method.name} false path")
                cases.append(f"Test {method.name} edge cases")

        # Error handling
        cases.append(f"Test {method.name} error handling")

        # Async-specific
        if method.is_async:
            cases.append(f"Test {method.name} cancellation")
            cases.append(f"Test {method.name} timeout behavior")

        return cases

    def _generate_rationale(
        self,
        method: MethodInfo,
        gap: CoverageGap
    ) -> str:
        """Generate rationale for the test suggestion."""
        reasons = []

        if gap.severity == CoverageSeverity.CRITICAL:
            reasons.append("Critical untested code path")
        elif gap.severity == CoverageSeverity.HIGH:
            reasons.append("High-risk untested code")

        if method.complexity > 5:
            reasons.append(f"High complexity ({method.complexity})")

        if method.has_branches:
            reasons.append(f"Multiple branches ({method.branch_count})")

        if method.is_async:
            reasons.append("Async code needs special test handling")

        if method.method_type == MethodType.PUBLIC:
            reasons.append("Public API method")

        return "; ".join(reasons) if reasons else "Standard test coverage"

    def suggest_for_method(self, method: MethodInfo) -> TestSuggestion:
        """
        Generate a test suggestion for a single method.

        Args:
            method: Method to suggest tests for

        Returns:
            TestSuggestion for the method
        """
        # Create a synthetic gap
        gap = CoverageGap(
            method=method,
            gap_type="uncovered",
            severity=CoverageSeverity.MODERATE,
            message=f"No test for {method.full_name}",
        )

        return self._create_suggestion(method, gap)

    def generate_test_skeleton(
        self,
        suggestion: TestSuggestion
    ) -> str:
        """
        Generate a test code skeleton.

        Args:
            suggestion: Test suggestion

        Returns:
            Python test code skeleton
        """
        method = suggestion.method
        lines = []

        # Imports
        if method.is_async:
            lines.append("import pytest")
            lines.append("")

        # Test function
        if method.is_async:
            lines.append("@pytest.mark.asyncio")
            lines.append(f"async def {suggestion.test_name}():")
        else:
            lines.append(f"def {suggestion.test_name}():")

        # Docstring
        lines.append(f'    """{suggestion.description}."""')

        # Arrange
        lines.append("    # Arrange")
        if method.class_name:
            lines.append(f"    instance = {method.class_name}()")
        lines.append("")

        # Act
        lines.append("    # Act")
        if method.class_name:
            if method.is_async:
                lines.append(f"    result = await instance.{method.name}()")
            else:
                lines.append(f"    result = instance.{method.name}()")
        else:
            if method.is_async:
                lines.append(f"    result = await {method.name}()")
            else:
                lines.append(f"    result = {method.name}()")
        lines.append("")

        # Assert
        lines.append("    # Assert")
        lines.append("    assert result is not None  # TODO: Add specific assertions")
        lines.append("")

        return "\n".join(lines)

    def generate_parametrized_test(
        self,
        suggestion: TestSuggestion
    ) -> str:
        """
        Generate a parametrized test skeleton.

        Args:
            suggestion: Test suggestion

        Returns:
            Python parametrized test code
        """
        method = suggestion.method
        lines = []

        lines.append("import pytest")
        lines.append("")
        lines.append("")

        # Test cases as parameters
        lines.append("@pytest.mark.parametrize('input_value,expected', [")
        lines.append("    (None, None),  # TODO: Add test cases")
        lines.append("    ('valid', 'expected_result'),")
        lines.append("    ('edge_case', 'edge_result'),")
        lines.append("])")

        # Test function
        if method.is_async:
            lines.append("@pytest.mark.asyncio")
            lines.append(f"async def {suggestion.test_name}(input_value, expected):")
        else:
            lines.append(f"def {suggestion.test_name}(input_value, expected):")

        # Docstring
        lines.append(f'    """{suggestion.description}."""')

        # Arrange
        lines.append("    # Arrange")
        if method.class_name:
            lines.append(f"    instance = {method.class_name}()")
        lines.append("")

        # Act
        lines.append("    # Act")
        if method.class_name:
            if method.is_async:
                lines.append(f"    result = await instance.{method.name}(input_value)")
            else:
                lines.append(f"    result = instance.{method.name}(input_value)")
        else:
            if method.is_async:
                lines.append(f"    result = await {method.name}(input_value)")
            else:
                lines.append(f"    result = {method.name}(input_value)")
        lines.append("")

        # Assert
        lines.append("    # Assert")
        lines.append("    assert result == expected")
        lines.append("")

        return "\n".join(lines)

    def prioritize_suggestions(
        self,
        suggestions: List[TestSuggestion],
        max_count: int = 10
    ) -> List[TestSuggestion]:
        """
        Get the highest priority suggestions.

        Args:
            suggestions: All suggestions
            max_count: Maximum number to return

        Returns:
            Top priority suggestions
        """
        # Already sorted by priority
        return suggestions[:max_count]
