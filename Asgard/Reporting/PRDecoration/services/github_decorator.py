"""
Asgard GitHub PR Decorator

Posts analysis results as comments on GitHub pull requests.
Posts a summary comment with quality gate status and ratings, followed by
individual inline review comments for each detected issue (up to the configured
maximum to avoid flooding the PR with noise).

Authentication uses the api_token supplied in PRDecorationConfig. The token must
have write access to pull request reviews and issue comments.
"""

import json
from typing import List, Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from Asgard.Reporting.PRDecoration.models.decoration_models import (
    IssueComment,
    PRDecorationConfig,
    PRDecorationResult,
)

_GITHUB_API_BASE = "https://api.github.com"


class GitHubDecorator:
    """
    Posts Heimdall analysis results to a GitHub pull request.

    Requires:
        - A GitHub personal access token (or GitHub Actions GITHUB_TOKEN) with
          write access to pull request comments.
        - The repository identifier in 'owner/repo' format.
        - The PR number.

    Usage:
        config = PRDecorationConfig(
            platform="github",
            api_token=os.environ["GITHUB_TOKEN"],
            repository="my-org/my-repo",
            pr_number=42,
        )
        decorator = GitHubDecorator()
        result = decorator.decorate(config, issues, gate_result=gate_result, ratings=ratings)
        print(f"Summary posted: {result.summary_posted}")
        print(f"Inline comments: {result.inline_comments_posted}")
    """

    def decorate(
        self,
        config: PRDecorationConfig,
        issues: List[IssueComment],
        gate_result=None,
        ratings=None,
    ) -> PRDecorationResult:
        """
        Post analysis results to a GitHub pull request.

        Steps:
        1. Fetch the PR head commit SHA (needed for inline comments).
        2. Post an overall summary as an issue comment.
        3. Post inline review comments for each issue (up to max_inline_comments).

        Args:
            config: PR decoration configuration including credentials and PR details.
            issues: List of analysis issues to post as inline comments.
            gate_result: Optional quality gate result for inclusion in the summary.
            ratings: Optional project ratings object for inclusion in the summary.

        Returns:
            PRDecorationResult describing what was posted and any errors.
        """
        errors: List[str] = []
        summary_posted = False
        inline_count = 0
        decoration_url: Optional[str] = None

        headers = {
            "Authorization": f"token {config.api_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

        head_sha: Optional[str] = None
        if config.post_inline_comments and issues:
            head_sha, err = self._get_pr_head_sha(config, headers)
            if err:
                errors.append(err)

        if config.post_summary:
            summary_body = self._build_summary(issues, gate_result, ratings)
            url = f"{_GITHUB_API_BASE}/repos/{config.repository}/issues/{config.pr_number}/comments"
            response_data, err = self._post_json(url, {"body": summary_body}, headers)
            if err:
                errors.append(f"Failed to post summary comment: {err}")
            else:
                summary_posted = True
                if response_data and "html_url" in response_data:
                    decoration_url = response_data["html_url"]

        if config.post_inline_comments and head_sha:
            limited_issues = issues[: config.max_inline_comments]
            for issue in limited_issues:
                comment_url = (
                    f"{_GITHUB_API_BASE}/repos/{config.repository}"
                    f"/pulls/{config.pr_number}/comments"
                )
                body = self._format_inline_body(issue)
                payload = {
                    "body": body,
                    "commit_id": head_sha,
                    "path": issue.file_path,
                    "line": issue.line_number,
                    "side": "RIGHT",
                }
                _, err = self._post_json(comment_url, payload, headers)
                if err:
                    errors.append(f"Failed to post inline comment for {issue.file_path}:{issue.line_number}: {err}")
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

    def _get_pr_head_sha(self, config: PRDecorationConfig, headers: dict):
        """
        Fetch the head commit SHA of the pull request.

        Returns:
            Tuple of (sha_string, error_string). One of the two will be None.
        """
        url = f"{_GITHUB_API_BASE}/repos/{config.repository}/pulls/{config.pr_number}"
        data, err = self._get_json(url, headers)
        if err:
            return None, err
        if data and "head" in data:
            return data["head"].get("sha"), None
        return None, "Could not extract head SHA from PR response"

    def _build_summary(self, issues: List[IssueComment], gate_result, ratings) -> str:
        """Build the markdown body for the summary PR comment."""
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
        """Format an inline review comment body for a single issue."""
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

    def _get_json(self, url: str, headers: dict):
        """
        GET a URL and return the parsed JSON response.

        Returns:
            Tuple of (response_dict_or_None, error_string_or_None).
        """
        try:
            req = urllib_request.Request(url, headers=headers, method="GET")
            with urllib_request.urlopen(req, timeout=30) as resp:
                response_text = resp.read().decode("utf-8")
                return json.loads(response_text), None
        except HTTPError as exc:
            return None, f"HTTP {exc.code}: {exc.reason}"
        except URLError as exc:
            return None, f"URL error: {exc.reason}"
        except (ValueError, OSError) as exc:
            return None, str(exc)
