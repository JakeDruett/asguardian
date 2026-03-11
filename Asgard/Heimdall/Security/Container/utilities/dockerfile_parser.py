"""
Heimdall Security Container Dockerfile Parser Utilities

Helper functions for parsing and analyzing Dockerfile content.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class DockerfileInstruction:
    """Represents a parsed Dockerfile instruction."""
    instruction: str
    arguments: str
    line_number: int
    raw_line: str
    is_continuation: bool = False


@dataclass
class DockerfileStage:
    """Represents a build stage in a multi-stage Dockerfile."""
    name: Optional[str]
    base_image: str
    tag: Optional[str]
    start_line: int
    instructions: List[DockerfileInstruction]


def parse_dockerfile(content: str) -> List[DockerfileInstruction]:
    """
    Parse Dockerfile content into a list of instructions.

    Args:
        content: Raw Dockerfile content

    Returns:
        List of DockerfileInstruction objects
    """
    instructions: List[DockerfileInstruction] = []
    lines = content.split("\n")

    current_instruction = ""
    current_line_number = 0
    is_continuation = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if is_continuation:
            current_instruction += " " + stripped.rstrip("\\").strip()
            if not stripped.endswith("\\"):
                instructions.append(_parse_instruction_line(
                    current_instruction,
                    current_line_number,
                    line
                ))
                is_continuation = False
                current_instruction = ""
        else:
            if stripped.endswith("\\"):
                is_continuation = True
                current_instruction = stripped.rstrip("\\").strip()
                current_line_number = i
            else:
                instructions.append(_parse_instruction_line(stripped, i, line))

    if current_instruction:
        instructions.append(_parse_instruction_line(
            current_instruction,
            current_line_number,
            current_instruction
        ))

    return instructions


def _parse_instruction_line(line: str, line_number: int, raw_line: str) -> DockerfileInstruction:
    """
    Parse a single Dockerfile instruction line.

    Args:
        line: The instruction line (without continuation)
        line_number: Line number in the file
        raw_line: The raw line content

    Returns:
        DockerfileInstruction object
    """
    parts = line.split(None, 1)
    instruction = parts[0].upper() if parts else ""
    arguments = parts[1] if len(parts) > 1 else ""

    return DockerfileInstruction(
        instruction=instruction,
        arguments=arguments,
        line_number=line_number,
        raw_line=raw_line.strip(),
    )


def parse_stages(content: str) -> List[DockerfileStage]:
    """
    Parse multi-stage Dockerfile into stages.

    Args:
        content: Raw Dockerfile content

    Returns:
        List of DockerfileStage objects
    """
    instructions = parse_dockerfile(content)
    stages: List[DockerfileStage] = []
    current_stage: Optional[DockerfileStage] = None

    for instr in instructions:
        if instr.instruction == "FROM":
            if current_stage:
                stages.append(current_stage)

            base_image, tag, name = _parse_from_instruction(instr.arguments)
            current_stage = DockerfileStage(
                name=name,
                base_image=base_image,
                tag=tag,
                start_line=instr.line_number,
                instructions=[instr],
            )
        elif current_stage:
            current_stage.instructions.append(instr)

    if current_stage:
        stages.append(current_stage)

    return stages


def _parse_from_instruction(arguments: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse FROM instruction arguments.

    Args:
        arguments: FROM instruction arguments

    Returns:
        Tuple of (base_image, tag, stage_name)
    """
    as_match = re.search(r"\s+[Aa][Ss]\s+(\S+)", arguments)
    stage_name = as_match.group(1) if as_match else None

    if as_match:
        arguments = arguments[:as_match.start()]

    arguments = arguments.strip()

    if ":" in arguments:
        parts = arguments.split(":", 1)
        base_image = parts[0]
        tag = parts[1].split()[0] if parts[1] else None
    else:
        base_image = arguments.split()[0] if arguments else ""
        tag = None

    return base_image, tag, stage_name


def extract_env_vars(instructions: List[DockerfileInstruction]) -> Dict[str, str]:
    """
    Extract environment variables from Dockerfile instructions.

    Args:
        instructions: List of parsed instructions

    Returns:
        Dictionary of environment variable names to values
    """
    env_vars: Dict[str, str] = {}

    for instr in instructions:
        if instr.instruction == "ENV":
            env_pairs = _parse_env_instruction(instr.arguments)
            env_vars.update(env_pairs)

    return env_vars


def _parse_env_instruction(arguments: str) -> Dict[str, str]:
    """
    Parse ENV instruction arguments.

    Args:
        arguments: ENV instruction arguments

    Returns:
        Dictionary of environment variable names to values
    """
    env_vars: Dict[str, str] = {}

    key_value_pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))'
    matches = re.findall(key_value_pattern, arguments)

    for match in matches:
        key = match[0]
        value = match[1] or match[2] or match[3]
        env_vars[key] = value

    if not matches:
        parts = arguments.split(None, 1)
        if len(parts) == 2:
            env_vars[parts[0]] = parts[1]

    return env_vars


def extract_exposed_ports(instructions: List[DockerfileInstruction]) -> List[Tuple[int, int]]:
    """
    Extract exposed ports from Dockerfile instructions.

    Args:
        instructions: List of parsed instructions

    Returns:
        List of (port, line_number) tuples
    """
    ports: List[Tuple[int, int]] = []

    for instr in instructions:
        if instr.instruction == "EXPOSE":
            port_numbers = _parse_expose_instruction(instr.arguments)
            for port in port_numbers:
                ports.append((port, instr.line_number))

    return ports


def _parse_expose_instruction(arguments: str) -> List[int]:
    """
    Parse EXPOSE instruction arguments.

    Args:
        arguments: EXPOSE instruction arguments

    Returns:
        List of port numbers
    """
    ports: List[int] = []

    port_pattern = r"(\d+)(?:/(?:tcp|udp))?"
    matches = re.findall(port_pattern, arguments)

    for match in matches:
        try:
            ports.append(int(match))
        except ValueError:
            pass

    return ports


def has_user_instruction(instructions: List[DockerfileInstruction]) -> bool:
    """
    Check if Dockerfile has a USER instruction (not running as root).

    Args:
        instructions: List of parsed instructions

    Returns:
        True if USER instruction is present
    """
    for instr in instructions:
        if instr.instruction == "USER":
            user = instr.arguments.strip().lower()
            if user and user != "root" and user != "0":
                return True
    return False


def has_healthcheck(instructions: List[DockerfileInstruction]) -> bool:
    """
    Check if Dockerfile has a HEALTHCHECK instruction.

    Args:
        instructions: List of parsed instructions

    Returns:
        True if HEALTHCHECK instruction is present
    """
    for instr in instructions:
        if instr.instruction == "HEALTHCHECK":
            if instr.arguments.strip().upper() != "NONE":
                return True
    return False


def find_run_commands(instructions: List[DockerfileInstruction]) -> List[DockerfileInstruction]:
    """
    Find all RUN instructions in the Dockerfile.

    Args:
        instructions: List of parsed instructions

    Returns:
        List of RUN instructions
    """
    return [instr for instr in instructions if instr.instruction == "RUN"]


def find_copy_add_instructions(
    instructions: List[DockerfileInstruction]
) -> List[DockerfileInstruction]:
    """
    Find all COPY and ADD instructions in the Dockerfile.

    Args:
        instructions: List of parsed instructions

    Returns:
        List of COPY and ADD instructions
    """
    return [instr for instr in instructions if instr.instruction in ("COPY", "ADD")]


def extract_code_snippet(lines: List[str], line_number: int, context_lines: int = 2) -> str:
    """
    Extract a code snippet around a specific line.

    Args:
        lines: List of file lines
        line_number: Line number (1-indexed)
        context_lines: Number of context lines before and after

    Returns:
        Code snippet with context
    """
    if not lines or line_number < 1:
        return ""

    start_idx = max(0, line_number - 1 - context_lines)
    end_idx = min(len(lines), line_number + context_lines)

    snippet_lines = []
    for i in range(start_idx, end_idx):
        line_num = i + 1
        marker = ">>> " if line_num == line_number else "    "
        line_content = lines[i] if i < len(lines) else ""
        snippet_lines.append(f"{marker}{line_num}: {line_content.rstrip()}")

    return "\n".join(snippet_lines)
