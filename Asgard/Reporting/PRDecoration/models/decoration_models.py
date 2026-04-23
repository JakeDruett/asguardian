"""
Asgard PR Decoration Models

Data models for configuring and recording the results of pull request decoration.
PR decoration posts analysis summaries and inline comments directly to GitHub or
GitLab pull requests / merge requests as part of a CI/CD workflow.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class PRPlatform(str, Enum):
    """Supported PR/MR hosting platforms."""
    GITHUB = "github"
    GITLAB = "gitlab"


class IssueComment(BaseModel):
    """
    Represents a single analysis issue to be posted as an inline review comment.

    The file_path and line_number identify the location of the issue in the
    diff. The rule_id links the comment back to the specific analysis rule.
    """
    file_path: str = Field(..., description="Repository-relative path to the affected file")
    line_number: int = Field(..., description="Line number where the issue was detected")
    message: str = Field(..., description="Human-readable description of the issue")
    severity: str = Field("warning", description="Severity level: error, warning, or info")
    rule_id: str = Field(..., description="Identifier of the rule that raised this issue")

    class Config:
        use_enum_values = True


class PRDecorationConfig(BaseModel):
    """
    Configuration required to post decoration to a pull request.

    API tokens must be sourced from environment variables by the caller and
    passed in explicitly. This class does not read environment variables itself.
    """
    platform: PRPlatform = Field(..., description="Target platform: github or gitlab")
    api_token: str = Field(..., description="API token for authenticating with the platform")
    repository: str = Field(
        ...,
        description="Repository identifier in 'owner/repo' format",
    )
    pr_number: int = Field(..., description="Pull request or merge request number")
    post_summary: bool = Field(
        True,
        description="Whether to post an overall summary comment",
    )
    post_inline_comments: bool = Field(
        True,
        description="Whether to post individual inline review comments",
    )
    max_inline_comments: int = Field(
        50,
        description="Maximum number of inline comments to post (to avoid spam)",
    )
    gitlab_api_url: Optional[str] = Field(
        None,
        description="GitLab API base URL (required for GitLab; e.g. 'https://gitlab.com/api/v4')",
    )
    github_api_url: Optional[str] = Field(
        None,
        description=(
            "GitHub API base URL. Defaults to 'https://api.github.com'. "
            "Override to target GitHub Enterprise Server instances."
        ),
    )

    class Config:
        use_enum_values = True


class PRDecorationResult(BaseModel):
    """
    Records the outcome of a pull request decoration operation.

    Captures whether the summary and inline comments were successfully posted,
    how many inline comments were created, any errors encountered, and the URL
    of the posted summary (if available).
    """
    platform: PRPlatform = Field(..., description="Platform that was decorated")
    pr_number: int = Field(..., description="Pull request or merge request number")
    summary_posted: bool = Field(False, description="Whether the summary comment was posted")
    inline_comments_posted: int = Field(0, description="Number of inline comments successfully posted")
    errors: List[str] = Field(
        default_factory=list,
        description="Errors encountered during decoration",
    )
    decoration_url: Optional[str] = Field(
        None,
        description="URL of the posted summary comment (if available)",
    )

    class Config:
        use_enum_values = True
