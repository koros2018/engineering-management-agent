"""
knowledge_base/__init__.py — 标准知识库统一入口

使用方式：
    from knowledge_base import get_kb
    kb = get_kb()
    stats = kb.get_stats()
    checklist = kb.get_review_checklist(EngineeringDomain.FIRE_PROTECTION)
"""
from .schema import (
    EngineeringDomain, MandatoryLevel, StandardLevel, ConflictType,
    Standard, StandardVersion, StandardConflict,
    MandatoryClause, KnowledgeBaseStats,
)
from .taxonomy import (
    CORE_STANDARDS, DOMAIN_CATEGORIES,
    get_standards_by_domain, get_mandatory_standards, get_standards_by_level,
)
from .mandatory import MandatoryClauseExtractor, get_extractor, PRESET_MANDATORY_CLAUSES
from .conflict import ConflictDetector, get_detector, KNOWN_CONFLICTS, VERSION_SUPERSEDE
from .manager import KnowledgeBase, get_kb

__all__ = [
    # Schema
    'EngineeringDomain', 'MandatoryLevel', 'StandardLevel', 'ConflictType',
    'Standard', 'StandardVersion', 'StandardConflict', 'MandatoryClause',
    'KnowledgeBaseStats',
    # Taxonomy
    'CORE_STANDARDS', 'DOMAIN_CATEGORIES',
    'get_standards_by_domain', 'get_mandatory_standards', 'get_standards_by_level',
    # Mandatory
    'MandatoryClauseExtractor', 'get_extractor', 'PRESET_MANDATORY_CLAUSES',
    # Conflict
    'ConflictDetector', 'get_detector', 'KNOWN_CONFLICTS', 'VERSION_SUPERSEDE',
    # Manager
    'KnowledgeBase', 'get_kb',
]
