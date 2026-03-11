"""
Asgard Reporting PRDecoration - Pull Request Decoration

Posts Heimdall analysis results as comments on GitHub pull requests and
GitLab merge requests. Supports posting a summary comment with quality gate
status and ratings, plus individual inline review comments for each issue.

Supports:
- GitHub: Posts to /repos/{owner}/{repo}/issues/{pr}/comments (summary) and
          /repos/{owner}/{repo}/pulls/{pr}/comments (inline).
- GitLab: Posts to /projects/{encoded_repo}/merge_requests/{mr}/notes (summary)
          and /projects/{encoded_repo}/merge_requests/{mr}/discussions (inline).

Usage:
    import os
    from Asgard.Reporting.PRDecoration import (
        GitHubDecorator, PRDecorationConfig, IssueComment, PRPlatform,
    )

    config = PRDecorationConfig(
        platform=PRPlatform.GITHUB,
        api_token=os.environ["GITHUB_TOKEN"],
        repository="my-org/my-repo",
        pr_number=42,
        max_inline_comments=30,
    )

    issues = [
        IssueComment(
            file_path="src/service.py",
            line_number=42,
            message="Cyclomatic complexity exceeds threshold (12 > 10)",
            severity="error",
            rule_id="quality.cyclomatic_complexity",
        ),
    ]

    decorator = GitHubDecorator()
    result = decorator.decorate(config, issues)
    print(f"Summary posted: {result.summary_posted}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Reporting.PRDecoration.models.decoration_models import (
    IssueComment,
    PRDecorationConfig,
    PRDecorationResult,
    PRPlatform,
)
from Asgard.Reporting.PRDecoration.services.github_decorator import GitHubDecorator
from Asgard.Reporting.PRDecoration.services.gitlab_decorator import GitLabDecorator

__all__ = [
    "GitHubDecorator",
    "GitLabDecorator",
    "IssueComment",
    "PRDecorationConfig",
    "PRDecorationResult",
    "PRPlatform",
]
