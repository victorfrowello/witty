"""
Pydantic models for Witty - re-exports from src.witty_types.

This module re-exports all types from src.witty_types for backward
compatibility. Import from either location:
    from src.witty.types import FormalizeOptions
    from src.witty_types import FormalizeOptions
"""
from src.witty_types import (
    # Enums
    ModuleStage,
    
    # Core types
    ProvenanceRecord,
    ModuleResult,
    FormalizeOptions,
    AtomicClaim,
    ConcisionResult,
    FormalizationResult,
    
    # CNF types
    CNFClause,
    CNFResult,
    
    # Symbolizer types  
    SymbolizerResult,
    
    # World/Modal types
    WorldResult,
    EntityGrounding,
    CoherenceReport,
    ModalResult,
    ModalContext,
    
    # Enrichment/Retrieval types
    EnrichmentResult,
    EnrichmentSource,
    ExpandedClaim,
    RetrievalSource,
    RetrievalResponse,
)

__all__ = [
    "ModuleStage",
    "ProvenanceRecord",
    "ModuleResult",
    "FormalizeOptions",
    "AtomicClaim",
    "ConcisionResult",
    "FormalizationResult",
    "CNFClause",
    "CNFResult",
    "SymbolizerResult",
    "WorldResult",
    "EntityGrounding",
    "CoherenceReport",
    "ModalResult",
    "ModalContext",
    "EnrichmentResult",
    "EnrichmentSource",
    "ExpandedClaim",
    "RetrievalSource",
    "RetrievalResponse",
]
