"""Population modeling and generation module."""

from episwarm.population.build import PopulationSoA, build_synthetic_population
from episwarm.population.households import compose_households
from episwarm.population.ipf import run_ipf_2d, run_ipf_3d
from episwarm.population.venues import (
    VenueRegistry, instantiate_venues, assign_venues_and_commute
)
from episwarm.population.traits import sample_traits, assign_comorbidity_multipliers

__all__ = [
    "PopulationSoA",
    "build_synthetic_population",
    "compose_households",
    "run_ipf_2d",
    "run_ipf_3d",
    "VenueRegistry",
    "instantiate_venues",
    "assign_venues_and_commute",
    "sample_traits",
    "assign_comorbidity_multipliers",
]
