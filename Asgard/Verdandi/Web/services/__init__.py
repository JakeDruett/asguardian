"""Web services."""

from Asgard.Verdandi.Web.services.vitals_calculator import CoreWebVitalsCalculator
from Asgard.Verdandi.Web.services.navigation_timing import NavigationTimingCalculator
from Asgard.Verdandi.Web.services.resource_timing import ResourceTimingCalculator

__all__ = [
    "CoreWebVitalsCalculator",
    "NavigationTimingCalculator",
    "ResourceTimingCalculator",
]
