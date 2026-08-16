"""SRP evaluator — Disjoint-Domain God Class via LCOM4 + import-root fan-out.

Per ``_Docs/Planning/Heimdall/02_SOLID_Detection.md``: flag when
``methods > 20`` AND (``LCOM4 > 1`` OR ``import_roots >= 3``).
"""
from typing import List

from Asgard.Bragi.Architecture.cir.models import ClassInfo, FileInfo
from Asgard.Bragi.Architecture.evaluators._lcom4 import (
    MAX_LCOM4_METHODS,
    lcom4_components,
    lcom4_oversized,
)
from Asgard.Bragi.Architecture.models.architecture_models import (
    Confidence,
    SOLIDPrinciple,
    SOLIDViolation,
    ViolationSeverity,
)

METHOD_THRESHOLD = 20
IMPORT_ROOT_THRESHOLD = 3


def evaluate(file_info: FileInfo, cls: ClassInfo) -> List[SOLIDViolation]:
    violations: List[SOLIDViolation] = []

    if lcom4_oversized(cls):
        violations.append(SOLIDViolation(
            principle=SOLIDPrinciple.SRP,
            class_name=cls.name,
            file_path=cls.filepath,
            line_number=cls.start_line,
            message=(
                f"Class '{cls.name}' has {cls.method_count} methods "
                f"(LCOM4 cap {MAX_LCOM4_METHODS}); pairwise cohesion skipped."
            ),
            severity=ViolationSeverity.MODERATE,
            suggestion="Split responsibilities into separate classes/modules.",
            confidence=Confidence.MEDIUM,
            evidence=f"LCOM4 skipped: methods={cls.method_count} exceeds {MAX_LCOM4_METHODS}",
        ))
        return violations

    if cls.method_count > METHOD_THRESHOLD:
        components = lcom4_components(cls)
        lcom_value = len(components)
        import_fanout = len(cls.import_roots)

        if lcom_value > 1 or import_fanout >= IMPORT_ROOT_THRESHOLD:
            evidence_parts = []
            if lcom_value > 1:
                comp_desc = " | ".join(
                    "{" + ", ".join(sorted(c)[:16]) + "}" for c in components[:8] if c
                )
                if len(comp_desc) > 500:
                    comp_desc = comp_desc[:497] + "..."
                evidence_parts.append(f"LCOM4={lcom_value}: {comp_desc}")
            if import_fanout >= IMPORT_ROOT_THRESHOLD:
                evidence_parts.append(f"import_roots={import_fanout}")

            violations.append(SOLIDViolation(
                principle=SOLIDPrinciple.SRP,
                class_name=cls.name,
                file_path=cls.filepath,
                line_number=cls.start_line,
                message=(
                    f"Class '{cls.name}' has {cls.method_count} methods "
                    f"(threshold {METHOD_THRESHOLD}) and shows signs of disjoint "
                    "responsibilities. Consider splitting into smaller, focused classes."
                ),
                severity=ViolationSeverity.MODERATE,
                suggestion="Split responsibilities into separate classes/modules.",
                confidence=Confidence.MEDIUM,
                evidence="; ".join(evidence_parts),
            ))

    return violations
