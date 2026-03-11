"""
Asgard GitLab MR Decorator

Posts analysis results as comments on GitLab merge requests.
Posts a summary note on the MR and individual inline discussion comments for each
detected issue (up to the configured maximum).

Authentication uses the api_token supplied in PRDecorationConfig. The token must
be a GitLab personal access token or project access token with write access to
merge request notes and discussions.

The GitLab API URL must be supplied explicitly in PRDecorationConfig.gitlab_api_url.
No default value is provided; callers must read it from their environment and pass
it in.
"""

import json
from typing import List, Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from Asgard.Reporting.PRDecoration.models.decoration_models import (
    IssueComment,
    PRDecorationConfig,
    PRDecorationResult,
)


class GitLabDecorator:
    """
    Posts Heimdall analysis results to a GitLab merge request.

    Requires:
        - A GitLab personal access token or project access token with write
          access to merge request notes and discussions.
        - The repository identifier in 'namespace/project' format (will be
          URL-encoded automatically).
        - The MR number (iid in GitLab terminology).
        - The GitLab API base URL in PRDecorationConfig.gitlab_api_url
          (e.g. "https://gitlab.com/api/v4" or a self-hosted instance URL).

    Usage:
        config = PRDecorationConfig(
            platform="gitlab",
            api_token=os.environ["GITLAB_TOKEN"],
            repository="my-group/my-project",
            pr_number=17,
            gitlab_api_url=os.environ["GITLAB_API_URL"],
        )
        decorator = GitLabDecorator()
        result = decorator.decorate(config, issues, gate_result=gate_result, ratings=ratings)
    """

    def decorate(
        self,
        config: PRDecorationConfig,
        issues: List[IssueComment],
        gate_result=None,
        ratings=None,
    ) -> PRDecorationResult:
        """
        Post analysis results to a GitLab merge request.

        Steps:
        1. Post an overall summary as an MR note.
        2. Post inline discussion comments for each issue (up to max_inline_comments).

        Args:
            config: PR decoration configuration including credentials and MR details.
            issues: List of analysis issues to post as inline discussion comments.
            gate_result: Optional quality gate result for inclusion in the summary.
            ratings: Optional project ratings object for inclusion in the summary.

        Returns:
            PRDecorationResult describing what was posted and any errors.

        Raises:
            ValueError: If gitlab_api_url is not set in the config.
        """
        if not config.gitlab_api_url:
            raise ValueError(
                "gitlab_api_url must be set in PRDecorationConfig for GitLab decoration. "
                "Read it from the GITLAB_API_URL environment variable and pass it explicitly."
            )

        errors: List[str] = []
        summary_posted = False
        inline_count = 0
        decoration_url: Optional[str] = None

        api_base = config.gitlab_api_url.rstrip("/")
        encoded_repo = quote(config.repository, safe="")
        headers = {
            "PRIVATE-TOKEN": config.api_token,
            "Content-Type": "application/json",
        }

        if config.post_summary:
            summary_body = self._build_summary(issues, gate_result, ratings)
            url = (
                f"{api_base}/projects/{encoded_repo}"
                f"/merge_requests/{config.pr_number}/notes"
            )
            response_data, err = self._post_json(url, {"body": summary_body}, headers)
            if err:
                errors.append(f"Failed to post summary note: {err}")
            else:
                summary_posted = True
                if response_data and "web_url" in response_data:
                    decoration_url = response_data["web_url"]

        if config.post_inline_comments:
            limited_issues = issues[: config.max_inline_comments]
            for issue in limited_issues:
                discussion_url = (
                    f"{api_base}/projects/{encoded_repo}"
                    f"/merge_requests/{config.pr_number}/discussions"
                )
                body = self._format_inline_body(issue)
                payload = {
                    "body": body,
                    "position": {
                        "base_sha": None,
                        "start_sha": None,
                        "head_sha": None,
                        "position_type": "text",
                        "new_path": issue.file_path,
                        "new_line": issue.line_number,
                    },
                }
                _, err = self._post_json(discussion_url, payload, headers)
                if err:
                    errors.append(
                        f"Failed to post inline comment for "
                        f"{issue.file_path}:{issue.line_number}: {err}"
                    )
                else:
                    inline_count += 1

        return PRDecorationResult(
            platform=config.platform,
            pr_number=config.pr_number,
            summary_posted=summary_posted,
            inline_comments_posted=inline_count,
            errors=errors,
            decoration_url=decoration_url,
        )

    def _build_summary(self, issues: List[IssueComment], gate_result, ratings) -> str:
        """Build the markdown body for the MR summary note."""
        lines = ["## Heimdall Code Analysis"]
        lines.append("")

        if gate_result is not None:
            status = getattr(gate_result, "status", "unknown")
            status_str = str(status).upper()
            lines.append(f"**Quality Gate:** {status_str}")
            lines.append("")

        if ratings is not None:
            lines.append("**Quality Ratings:**")
            lines.append("")
            lines.append("| Dimension | Rating |")
            lines.append("| --- | --- |")
            maintainability = getattr(ratings, "maintainability", None)
            reliability = getattr(ratings, "reliability", None)
            security = getattr(ratings, "security", None)
            if maintainability is not None:
                lines.append(f"| Maintainability | {getattr(maintainability, 'rating', 'N/A')} |")
            if reliability is not None:
                lines.append(f"| Reliability | {getattr(reliability, 'rating', 'N/A')} |")
            if security is not None:
                lines.append(f"| Security | {getattr(security, 'rating', 'N/A')} |")
            lines.append("")

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        info_count = sum(1 for i in issues if i.severity == "info")

        lines.append(f"**Issues Found:** {len(issues)} total")
        lines.append(f"- Errors: {error_count}")
        lines.append(f"- Warnings: {warning_count}")
        lines.append(f"- Info: {info_count}")

        return "\n".join(lines)

    def _format_inline_body(self, issue: IssueComment) -> str:
        """Format an inline discussion comment body for a single issue."""
        severity_label = f"**[{issue.severity.upper()}]**"
        return f"{severity_label} `{issue.rule_id}`: {issue.message}"

    def _post_json(self, url: str, payload: dict, headers: dict):
        """
        POST JSON data to a URL and return the parsed response.

        Returns:
            Tuple of (response_dict_or_None, error_string_or_None).
        """
        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib_request.Request(url, data=body, headers=headers, method="POST")
            with urllib_request.urlopen(req, timeout=30) as resp:
                response_text = resp.read().decode("utf-8")
                if response_text:
                    return json.loads(response_text), None
                return None, None
        except HTTPError as exc:
            return None, f"HTTP {exc.code}: {exc.reason}"
        except URLError as exc:
            return None, f"URL error: {exc.reason}"
        except (ValueError, OSError) as exc:
            return None, str(exc)
