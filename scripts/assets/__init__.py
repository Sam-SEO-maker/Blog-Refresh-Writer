"""
Assets Module

Gestion et préservation des assets (images, liens) lors de la réécriture.
"""

from .asset_manager import AssetManager, AssetValidationResult

__all__ = ["AssetManager", "AssetValidationResult"]
