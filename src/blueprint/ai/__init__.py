"""src/blueprint/ai/ - AI推理模块"""

from .classifier import smart_classify, batch_classify
from .inference import (
    analyze_blueprint,
    infer_drawing_type,
    infer_layer_semantics,
    analyze_layers,
    infer_design_principles,
    infer_construction_requirements,
    extract_project_info,
    call_llm,
)
from .extractor import (
    smart_extract,
    rule_extract,
    llm_extract,
    extract_material_specs,
    extract_design_params,
)

__all__ = [
    # 分类器
    "smart_classify",
    "batch_classify",
    # 推理引擎
    "analyze_blueprint",
    "infer_drawing_type",
    "infer_layer_semantics",
    "analyze_layers",
    "infer_design_principles",
    "infer_construction_requirements",
    "extract_project_info",
    "call_llm",
    # 信息提取
    "smart_extract",
    "rule_extract",
    "llm_extract",
    "extract_material_specs",
    "extract_design_params",
]
