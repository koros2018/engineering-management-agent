"""src/blueprint/review/ - 智能审查模块"""

from .engine import (
    Severity,
    ReviewRule,
    review_drawing,
    review_blueprint,
    review_analysis,
    quick_review,
    review_summary_text,
)
from .specs import (
    LAYER_TO_SPECS,
    BLOCK_TO_COMPONENT,
    lookup_specs_for_layer,
    lookup_component_info,
    get_layer_category,
)
from .geo_rules import (
    check_geometry_issues,
    get_geo_rules,
)

__all__ = [
    # 审查引擎
    "Severity",
    "ReviewRule",
    "review_drawing",
    "review_blueprint",
    "review_analysis",
    "quick_review",
    "review_summary_text",
    # 规范库
    "LAYER_TO_SPECS",
    "BLOCK_TO_COMPONENT",
    "lookup_specs_for_layer",
    "lookup_component_info",
    "get_layer_category",
    # 几何审查
    "check_geometry_issues",
    "get_geo_rules",
]
