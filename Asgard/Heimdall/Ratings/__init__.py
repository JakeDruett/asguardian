"""
Heimdall Ratings - A-E Quality Ratings System

Calculates letter ratings (A-E) for three quality dimensions:
- Maintainability: based on technical debt ratio
- Reliability: based on worst severity bug/quality issue found
- Security: based on worst severity vulnerability found

Usage:
    from Asgard.Heimdall.Ratings import RatingsCalculator, RatingsConfig
    from Asgard.Heimdall.Ratings import LetterRating, ProjectRatings

    calculator = RatingsCalculator()
    ratings = calculator.calculate_from_reports(
        scan_path="./src",
        debt_report=debt_report,
        security_report=security_report,
    )
    print(f"Overall: {ratings.overall_rating}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Heimdall.Ratings.models.ratings_models import (
    DebtThresholds,
    DimensionRating,
    LetterRating,
    ProjectRatings,
    RatingDimension,
    RatingsConfig,
)
from Asgard.Heimdall.Ratings.services.ratings_calculator import RatingsCalculator

__all__ = [
    "DebtThresholds",
    "DimensionRating",
    "LetterRating",
    "ProjectRatings",
    "RatingDimension",
    "RatingsCalculator",
    "RatingsConfig",
]
