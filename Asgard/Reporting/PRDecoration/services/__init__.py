"""
Asgard PR Decoration Services
"""

from Asgard.Reporting.PRDecoration.services.github_decorator import GitHubDecorator
from Asgard.Reporting.PRDecoration.services.gitlab_decorator import GitLabDecorator

__all__ = [
    "GitHubDecorator",
    "GitLabDecorator",
]
