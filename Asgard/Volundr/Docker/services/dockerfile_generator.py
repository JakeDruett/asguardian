"""
Dockerfile Generator Service

Generates optimized Dockerfiles with multi-stage builds,
security best practices, and layer caching optimization.
"""

import hashlib
import os
from datetime import datetime
from typing import List, Optional

from Asgard.Volundr.Docker.models.docker_models import (
    DockerfileConfig,
    GeneratedDockerConfig,
)


class DockerfileGenerator:
    """Generates Dockerfiles from configuration."""

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the Dockerfile generator.

        Args:
            output_dir: Directory for saving generated Dockerfiles
        """
        self.output_dir = output_dir or "."

    def generate(self, config: DockerfileConfig) -> GeneratedDockerConfig:
        """
        Generate a Dockerfile based on the provided configuration.

        Args:
            config: Dockerfile configuration

        Returns:
            GeneratedDockerConfig with generated content
        """
        config_json = config.model_dump_json()
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()[:16]
        config_id = f"{config.name}-dockerfile-{config_hash}"

        content: List[str] = []

        for arg_name, arg_default in config.args.items():
            content.append(f"ARG {arg_name}={arg_default}")

        if config.args:
            content.append("")

        for i, stage in enumerate(config.stages):
            is_final = i == len(config.stages) - 1

            if stage.name:
                content.append(f"FROM {stage.base_image} AS {stage.name}")
            else:
                content.append(f"FROM {stage.base_image}")

            content.append(f"WORKDIR {stage.workdir}")
            content.append("")

            for env_name, env_value in stage.env_vars.items():
                content.append(f"ENV {env_name}={env_value}")

            if stage.env_vars:
                content.append("")

            if stage.copy_from and stage.copy_src and stage.copy_dst:
                content.append(f"COPY --from={stage.copy_from} {stage.copy_src} {stage.copy_dst}")
                content.append("")

            for copy_cmd in stage.copy_commands:
                src = copy_cmd.get("src", ".")
                dst = copy_cmd.get("dst", ".")
                chown = copy_cmd.get("chown")
                if chown:
                    content.append(f"COPY --chown={chown} {src} {dst}")
                else:
                    content.append(f"COPY {src} {dst}")

            if stage.copy_commands:
                content.append("")

            if config.optimize_layers and stage.run_commands:
                combined_run = " && \\\n    ".join(stage.run_commands)
                content.append(f"RUN {combined_run}")
                content.append("")
            else:
                for run_cmd in stage.run_commands:
                    content.append(f"RUN {run_cmd}")
                if stage.run_commands:
                    content.append("")

            if is_final:
                if config.use_non_root and stage.user:
                    content.append(f"USER {stage.user}")
                    content.append("")

                for port in stage.expose_ports:
                    content.append(f"EXPOSE {port}")

                if stage.expose_ports:
                    content.append("")

                if config.healthcheck:
                    hc = config.healthcheck
                    hc_cmd = hc.get("test", ["CMD", "echo", "ok"])
                    hc_interval = hc.get("interval", "30s")
                    hc_timeout = hc.get("timeout", "10s")
                    hc_retries = hc.get("retries", 3)
                    hc_start = hc.get("start_period", "5s")

                    if isinstance(hc_cmd, list):
                        hc_cmd_str = " ".join(hc_cmd)
                    else:
                        hc_cmd_str = hc_cmd

                    content.append(
                        f"HEALTHCHECK --interval={hc_interval} --timeout={hc_timeout} "
                        f"--start-period={hc_start} --retries={hc_retries} {hc_cmd_str}"
                    )
                    content.append("")

                for label_key, label_value in config.labels.items():
                    content.append(f'LABEL {label_key}="{label_value}"')

                if config.labels:
                    content.append("")

                if stage.entrypoint:
                    entrypoint_str = ", ".join(f'"{e}"' for e in stage.entrypoint)
                    content.append(f"ENTRYPOINT [{entrypoint_str}]")

                if stage.cmd:
                    cmd_str = ", ".join(f'"{c}"' for c in stage.cmd)
                    content.append(f"CMD [{cmd_str}]")

            content.append("")

        dockerfile_content = "\n".join(content).strip() + "\n"

        validation_results = self._validate_dockerfile(dockerfile_content, config)
        best_practice_score = self._calculate_best_practice_score(dockerfile_content, config)

        return GeneratedDockerConfig(
            id=config_id,
            config_hash=config_hash,
            dockerfile_content=dockerfile_content,
            validation_results=validation_results,
            best_practice_score=best_practice_score,
            created_at=datetime.now(),
        )

    def _validate_dockerfile(self, content: str, config: DockerfileConfig) -> List[str]:
        """Validate the generated Dockerfile for common issues."""
        issues: List[str] = []

        if "FROM" not in content:
            issues.append("Dockerfile missing FROM instruction")

        if len(config.stages) == 1 and "AS " in content:
            pass
        elif len(config.stages) > 1 and "AS " not in content:
            issues.append("Multi-stage build should use named stages")

        if config.use_non_root and "USER" not in content:
            issues.append("Dockerfile should specify non-root USER")

        if ":latest" in content:
            issues.append("Avoid using :latest tag for base images")

        if "COPY . ." in content or "ADD . ." in content:
            issues.append("Copying entire context may include unnecessary files")

        return issues

    def _calculate_best_practice_score(self, content: str, config: DockerfileConfig) -> float:
        """Calculate a best practice score for the generated Dockerfile."""
        score = 0.0
        max_score = 0.0

        max_score += 20
        if len(config.stages) > 1:
            score += 20
        elif "slim" in content.lower() or "alpine" in content.lower() or "distroless" in content.lower():
            score += 15

        max_score += 20
        if "USER" in content and config.use_non_root:
            score += 20

        max_score += 15
        if "HEALTHCHECK" in content:
            score += 15

        max_score += 15
        if ":latest" not in content:
            score += 15

        max_score += 15
        if config.optimize_layers and content.count("RUN ") < len(config.stages) * 3:
            score += 15

        max_score += 15
        if config.labels:
            score += 15

        return (score / max_score) * 100 if max_score > 0 else 0.0

    def save_to_file(
        self, docker_config: GeneratedDockerConfig, output_dir: Optional[str] = None, filename: str = "Dockerfile"
    ) -> str:
        """
        Save generated Dockerfile to file.

        Args:
            docker_config: Generated Docker config to save
            output_dir: Override output directory
            filename: Dockerfile filename

        Returns:
            Path to the saved file
        """
        target_dir = output_dir or self.output_dir
        os.makedirs(target_dir, exist_ok=True)
        file_path = os.path.join(target_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(docker_config.dockerfile_content or "")

        return file_path
