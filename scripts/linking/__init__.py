"""
Linking Package

Live path: EnseignaAvisLinker (`cw linking avis`, finalize step 4) +
InjectionValidator. The generic cocoon-injection pipeline (LinkInjector,
LinkMappingLoader, AnchorGenerator, InjectionPlanner, similarity engine)
was removed on 2026-07-23: zero consumers, and its links.csv inputs never
existed (see memory: no silo internal linking on SP Ressources).
"""

from .injection_validator import InjectionValidator

__all__ = ["InjectionValidator"]
