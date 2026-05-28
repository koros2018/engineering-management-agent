"""EMA自研审查引擎 - 从blueprint-ai/review.py迁移 (Phase 7+1-C, 2026-05-28)"""

"""
Blueprint AI Review Module (智能审查)
基于国标规范的合规性审查引擎
"""

import json
import os
from typing import Any
from .specs import LAYER_TO_SPECS, lookup_specs_for_layer, get_layer_category

# P3: 几何审查规则集成
try:
    from .geo_rules import get_geo_rules, check_geometry_issues
    HAS_GEO_RULES = True
except ImportError:
    HAS_GEO_RULES = False
    get_geo_rules = lambda: []
    check_geometry_issues = lambda g, t: []


# =============================================================================
# JSON 知识库加载
# =============================================================================

def _load_kb_index():
    """加载PDF知识库索引"""
    kb_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'docs')
    idx_path = os.path.join(kb_dir, 'kb_index.json')
    if os.path.exists(idx_path):
        with open(idx_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'specs': []}


def _load_kb_spec(spec_code: str):
    """加载单个规范的知识库详情"""
    kb_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'docs')
    safe = spec_code.replace('/', '_').replace(' ', '_').replace('.', '_')
    fname = 'kb_' + safe + '.json'
    path = os.path.join(kb_dir, fname)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def _find_kb_requirements(keywords: list, category: str = "") -> list:
    """从PDF知识库中搜索匹配的规范要求
    
    Args:
        keywords: 搜索关键词列表（如 ['管道', '焊接', '压力']）
        category: 可选的分类过滤（如 '管道', '锅炉'）
    
    Returns:
        匹配到的规范要求列表
    """
    results = []
    kb_index = _load_kb_index()
    
    for spec in kb_index.get('specs', []):
        if category and spec.get('category') != category:
            continue
        
        kb = _load_kb_spec(spec['code'])
        if not kb:
            continue
        
        for req in kb.get('key_requirements', []):
            text = req.get('section', '') + ' ' + req.get('title', '') + ' ' + req.get('requirement', '')
            # 匹配任意关键词
            matched = False
            for kw in keywords:
                if kw in text:
                    matched = True
                    break
            
            if matched:
                results.append({
                    'spec_code': spec['code'],
                    'spec_name': spec['name'],
                    'category': spec.get('category', ''),
                    'section': req.get('section', ''),
                    'title': req.get('title', ''),
                    'requirement': req.get('requirement', ''),
                })
    
    return results[:20]  # 最多返回20条


# =============================================================================
# 问题严重等级
# =============================================================================
class Severity:
    CRITICAL = "严重"      # 违反强条，必须修改
    WARNING  = "警告"      # 不符合规范，应修改
    SUGGEST  = "建议"      # 优化建议，非强制


# =============================================================================
# 规则定义：每条规则描述一个合规检查项
# =============================================================================
class ReviewRule:
    def __init__(
        self,
        id: str,
        name: str,
        check_fn,          # (layer_stats, entities) -> list[Issue]
        severity: str,
        spec_code: str = "",
        spec_section: str = "",
        suggestion: str = "",
    ):
        self.id = id
        self.name = name
        self.check_fn = check_fn
        self.severity = severity
        self.spec_code = spec_code
        self.spec_section = spec_section
        self.suggestion = suggestion

    def run(self, layer_stats: dict, entities: list) -> list:
        """执行检查，返回问题列表"""
        return self.check_fn(self.id, layer_stats, entities, self)


def _make_issue(
    rule,
    layer: str,
    location: str = "",
    description: str = "",
    detail: str = "",
    suggestion: str = "",
) -> dict:
    """构造标准问题条目"""
    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "severity": rule.severity,
        "layer": layer,
        "location": location,
        "description": description or f"图层 {layer} 存在不符合规范的问题",
        "detail": detail,
        "spec_code": rule.spec_code,
        "spec_section": rule.spec_section,
        "suggestion": suggestion or rule.suggestion,
    }


# =============================================================================
# 内置规则集
# =============================================================================

def _check_dimension_layer(rule_id, layer_stats, entities, rule_obj):
    """检查标注图层是否缺失或异常"""
    issues = []
    dim_layers = [l for l in layer_stats if "DIM" in l.upper() or "标注" in l]
    if not dim_layers:
        issues.append(_make_issue(
            rule_obj, "标注图层",
            description="图纸中未发现标注图层，建议添加尺寸标注以满足《房屋建筑制图统一标准》GB/T 50001-2017",
            detail="建筑图纸应包含完整的尺寸标注图层（如DIM或标注）",
        ))
    return issues


def _check_structural_column(rule_id, layer_stats, entities, rule_obj):
    """检查结构柱是否缺失（建筑图有柱网时）"""
    issues = []
    has_arch = any("建筑" in get_layer_category(l) or "WALL" in l.upper() for l in layer_stats)
    has_column = any("COLUMN" in l.upper() or "柱" in l for l in layer_stats)
    if has_arch and not has_column:
        issues.append(_make_issue(
            rule_obj, "结构图层",
            location="结构专业",
            description="建筑图中发现墙体但未发现结构柱图层",
            detail="多层建筑应在结构图层中标注柱网布置（如COLUMN层）",
            suggestion="补充结构柱图层或确认建筑与结构是否合并出图",
        ))
    return issues


def _check_fire_exit(rule_id, layer_stats, entities, rule_obj):
    """检查消防疏散标识"""
    issues = []
    fire_related = [l for l in layer_stats if any(k in l.upper() for k in ["FIRE", "EXIT", "疏散", "消防"])]
    if not fire_related:
        issues.append(_make_issue(
            rule_obj, "消防疏散标识",
            description="未发现消防疏散相关图层，建议按《建筑设计防火规范》GB 50016-2014 补充",
            detail="建筑图纸应包含安全出口、疏散指示等图层",
            suggestion="添加 FIRE_EXIT、EXIT_MKS 等图层标注消防设施",
        ))
    return issues


def _check_electrical_ground(rule_id, layer_stats, entities, rule_obj):
    """检查接地图层是否存在（电气图）"""
    issues = []
    elec_layers = [l for l in layer_stats if get_layer_category(l) == "电气"]
    has_ground = any("EARTH" in l.upper() or "接地" in l for l in layer_stats)
    if elec_layers and not has_ground:
        issues.append(_make_issue(
            rule_obj, "接地图层",
            location="电气专业",
            description="发现电气图层但未标注接地系统",
            detail="电气图纸应包含接地图层，参考《低压配电设计规范》GB 50054-2011",
            suggestion="添加 EARTH 或 PE 图层标识接地导体",
        ))
    return issues


def _check_hvac_duct(rule_id, layer_stats, entities, rule_obj):
    """检查风管标高完整性（暖通）"""
    issues = []
    duct_layers = [l for l in layer_stats if any(k in l.upper() for k in ["DUCT", "HVAC", "风管"])]
    if duct_layers:
        for l in duct_layers[:3]:  # 检查前3个风管图层
            stats = layer_stats.get(l, {})
            if stats.get("entity_count", 0) > 5 and not stats.get("has_text", False):
                issues.append(_make_issue(
                    rule_obj, l,
                    location=f"图层: {l}",
                    description=f"风管图层 {l} 实体数>{stats['entity_count']} 但未发现标注",
                    detail="风管应有标高标注或系统编号",
                    suggestion=f"为 {l} 添加风管标高标注或系统编号文字",
                ))
    return issues


def _check_plumbing_drain(rule_id, layer_stats, entities, rule_obj):
    """检查排水坡度标注（给排水）"""
    issues = []
    pipe_layers = [l for l in layer_stats if any(k in l.upper() for k in ["PIPE", "PLUMBING", "排水", "给水"])]
    has_slope_note = any("坡" in l or "SLOPE" in l.upper() or "标高" in l for l in layer_stats)
    if pipe_layers and not has_slope_note:
        issues.append(_make_issue(
            rule_obj, "排水管道",
            location="给排水专业",
            description="发现管道图层但未标注排水坡度",
            detail="排水管道应标注坡度，参考《建筑给水排水设计规范》GB 50015-2019",
            suggestion="在管道图层中添加坡度标注（如 i=0.003）",
        ))
    return issues


def _check_title_block(rule_id, layer_stats, entities, rule_obj):
    """检查标题栏是否规范（通用）"""
    issues = []
    has_title = any(any(k in l for k in ['TITLE', '标题栏', '图框', 'TITLE_BAR']) for l in layer_stats)
    if not has_title:
        issues.append(_make_issue(
            rule_obj, "标题栏",
            description="未发现标题栏图层，图纸应按《房屋建筑制图统一标准》GB/T 50001-2017 设置标题栏",
            detail="每张图纸应有明确的标题栏，标注工程名称、图纸名称、比例、设计信息等",
            suggestion="添加 TITLE_BAR 或 TITLE 图层，包含图名、比例、设计日期及设计单位信息",
        ))
    return issues


def _check_arch_stair(rule_id, layer_stats, entities, rule_obj):
    """检查楼梯设计合规性（建筑图）"""
    issues = []
    stair_layers = [l for l in layer_stats if any(k in l for k in ['楼梯', 'STAIR', 'stair'])]
    if not stair_layers:
        # 有墙体但无楼梯 → 检查是否应该配楼梯但缺失
        has_arch = any('建筑' in get_layer_category(l) or l.startswith('A-') for l in layer_stats)
        has_slab = any('SLAB' in l.upper() or '板' in l for l in layer_stats)
        if has_arch and has_slab:
            issues.append(_make_issue(
                rule_obj, "楼梯",
                description="发现楼板但未发现楼梯图层",
                detail="多层建筑应配置楼梯间，参考《住宅设计规范》GB 50096-2011 第6.4节",
                suggestion="添加楼梯图层（STAIR）或在楼梯间区域标注上下方向及踏步数",
            ))
        return issues
    # 楼梯踏步标注检查（踏步数量、梯段净高标注）
    for l in stair_layers[:2]:
        stats = layer_stats.get(l, {})
        if stats.get('entity_count', 0) > 3 and not stats.get('has_text', False):
            issues.append(_make_issue(
                rule_obj, l,
                description=f"楼梯图层 {l} 实体数>{stats['entity_count']} 但未发现踏步尺寸标注",
                detail="楼梯应标注踏步宽、高及梯段净高",
                suggestion=f"为 {l} 添加踏步尺寸标注（b×h），或梯段净高标注（H≥2200）",
            ))
    return issues


def _check_fire_compartment(rule_id, layer_stats, entities, rule_obj):
    """检查防火分区标识（建筑图）"""
    issues = []
    # 建筑或总图且有防火墙/防火门图层
    has_arch = any('建筑' in get_layer_category(l) or l.startswith('A-') for l in layer_stats)
    fire_compartment = [l for l in layer_stats if any(k in l for k in ['防火分区', 'FIRE', 'COMPARTMENT', '防火墙', '防火门'])]
    if has_arch and not fire_compartment:
        issues.append(_make_issue(
            rule_obj, "防火分区",
            description="建筑图纸未发现防火分区分隔标识",
            detail="大于一定规模的建筑应划分防火分区，参考《建筑设计防火规范》GB 50016-2014 第5.3节",
            suggestion="添加防火分区分隔线图层（FIRE_COMPARTMENT）及分区编号标注",
        ))
    return issues


def _check_electrical_distribution(rule_id, layer_stats, entities, rule_obj):
    """检查配电系统完整性（电气图）"""
    issues = []
    elec_layers = [l for l in layer_stats if get_layer_category(l) == '电气' or '电气' in l]
    has_distribution = any(any(k in l for k in ['配电', 'DIST', '配电箱', '柜', 'PANEL']) for l in layer_stats)
    if elec_layers and not has_distribution:
        issues.append(_make_issue(
            rule_obj, "配电系统",
            description="发现电气图层但未标注配电系统",
            detail="电气图纸应包含配电箱柜编号及干线走向，参考《低压配电设计规范》GB 50054-2011",
            suggestion="添加配电箱图层（DIST_PANEL）或在系统图中标注柜编号及负荷等级",
        ))
    return issues


def _check_electrical_fire_power(rule_id, layer_stats, entities, rule_obj):
    """检查消防电源标注（电气图）"""
    issues = []
    has_fire_elec = any('消防' in l or 'FIRE' in l.upper() for l in layer_stats)
    has_fire_power = any('消防电源' in l or '双电源' in l or 'FIRE_POWER' in l.upper() for l in layer_stats)
    if has_fire_elec and not has_fire_power:
        issues.append(_make_issue(
            rule_obj, "消防电源",
            location="电气专业",
            description="发现消防相关电气图层但未标注消防电源系统",
            detail="消防设备应采用专用供电回路，参考《建筑设计防火规范》GB 50016-2014 第10.1节",
            suggestion="添加消防电源标注图层（FIRE_POWER），说明双电源切换及供电等级",
        ))
    return issues


def _check_structural_foundation(rule_id, layer_stats, entities, rule_obj):
    """检查结构基础标注（结构图）"""
    issues = []
    struct_layers = [l for l in layer_stats if get_layer_category(l) == '结构' or '结构' in l or l.startswith('S-')]
    has_foundation = any('基础' in l or 'FOUNDATION' in l.upper() or '筏板' in l or '桩' in l for l in layer_stats)
    has_base_elevation = any('标高' in l or '基底' in l or 'BASE' in l.upper() for l in layer_stats)
    if struct_layers and not has_foundation and not has_base_elevation:
        issues.append(_make_issue(
            rule_obj, "基础设计",
            description="结构图纸未发现基础设计标注",
            detail="结构施工图应标注基础埋深、基底标高及地基承载力特征值，参考《建筑地基基础设计规范》GB 50007-2011",
            suggestion="添加基础标注图层（FOUNDATION），注明基底标高（如-2.500）及持力层信息",
        ))
    return issues


def _check_layer_naming_convention(rule_id, layer_stats, entities, rule_obj):
    """检查图层命名是否符合规范（鼓励中文命名或标准英文前缀）"""
    issues = []
    bad_layers = []
    for l in layer_stats:
        # 检测纯数字或无意义短名
        if len(l) <= 2 and not any(c.isalpha() for c in l):
            bad_layers.append(l)
        # 检测混用中英文（建议统一）
        has_cn = any('\u4e00' <= c <= '\u9fff' for c in l)
        has_en = any('A' <= c <= 'Z' or 'a' <= c <= 'z' for c in l)
        if has_cn and has_en and len(l) > 8:
            pass  # 混用暂不报错，但记录
    if bad_layers:
        issues.append(_make_issue(
            rule_obj, "图层命名",
            description=f"发现 {len(bad_layers)} 个不规范图层名: {', '.join(bad_layers[:5])}",
            detail="图层名应具有业务含义，建议使用英文或中文全称",
            suggestion="将短名图层（如 0、A、1等）重命名为有意义的名称",
        ))
    return issues


def _check_dimension_text_height(rule_id, layer_stats, entities, rule_obj):
    """检查尺寸标注文字高度是否一致"""
    issues = []
    dim_layers = [l for l in layer_stats if "DIM" in l.upper() or "标注" in l]
    if dim_layers:
        heights = []
        for l in dim_layers:
            stats = layer_stats.get(l, {})
            if stats.get("avg_text_height"):
                heights.append((l, stats["avg_text_height"]))
        if len(heights) >= 2:
            vals = [h for _, h in heights]
            if max(vals) - min(vals) > 1.5:  # 高低差超过1.5视为不一致
                issues.append(_make_issue(
                    rule_obj, "标注一致性",
                    description=f"发现标注图层文字高度不一致: {dict(heights)}",
                    detail="同一图纸中尺寸标注文字高度应统一",
                    suggestion="统一各标注图层的文字高度（建议 2.5~3.5mm 打印高度）",
                ))
    return issues


def _check_axle_layer(rule_id, layer_stats, entities, rule_obj):
    """检查轴线图层是否存在（建筑专业）"""
    issues = []
    has_arch = any("建筑" in get_layer_category(l) or "WALL" in l.upper() or "FLOOR" in l.upper() for l in layer_stats)
    has_axle = any("AXIS" in l.upper() or "轴线" in l or "GRID" in l.upper() for l in layer_stats)
    if has_arch and not has_axle:
        issues.append(_make_issue(
            rule_obj, "轴线图层",
            location="建筑专业",
            description="建筑图中未发现轴线图层，建议按《房屋建筑制图统一标准》添加轴线编号",
            detail="建筑平面图应包含轴线图层（AXIS），并对轴线进行编号标注",
            suggestion="添加 AXIS 或轴线图层，标注轴线编号（如A、B、1、2）",
        ))
    return issues


# =============================================================================
# 规则注册表
# =============================================================================
RULES = [
    ReviewRule(
        id="TITLE_001", name="标题栏规范性", severity=Severity.WARNING,
        check_fn=_check_title_block,
        spec_code="GB/T 50001-2017", spec_section="4.0 图框与标题栏",
        suggestion="添加标准标题栏图层",
    ),
    ReviewRule(
        id="NAMING_001", name="图层命名规范性", severity=Severity.SUGGEST,
        check_fn=_check_layer_naming_convention,
        suggestion="使用规范的中文或英文图层名",
    ),
    ReviewRule(
        id="DIM_001", name="标注图层完整性", severity=Severity.WARNING,
        check_fn=_check_dimension_layer,
        spec_code="GB/T 50001-2017", spec_section="7.0 尺寸标注",
        suggestion="补充完整尺寸标注图层",
    ),
    ReviewRule(
        id="DIM_002", name="标注文字高度一致性", severity=Severity.SUGGEST,
        check_fn=_check_dimension_text_height,
        spec_code="GB/T 50001-2017", spec_section="7.2 标注文字",
        suggestion="统一标注图层文字高度",
    ),
    ReviewRule(
        id="STRUCT_001", name="结构柱图层完整性", severity=Severity.WARNING,
        check_fn=_check_structural_column,
        spec_code="GB 50010-2010", spec_section="6.3 受压构件",
        suggestion="补充结构柱图层，标注柱网布置",
    ),
    ReviewRule(
        id="AXIS_001", name="轴线图层完整性", severity=Severity.SUGGEST,
        check_fn=_check_axle_layer,
        spec_code="GB/T 50001-2017", spec_section="5.0 轴线编号",
        suggestion="添加轴线图层和编号标注",
    ),
    ReviewRule(
        id="FIRE_001", name="消防疏散标识", severity=Severity.CRITICAL,
        check_fn=_check_fire_exit,
        spec_code="GB 50016-2014", spec_section="6.4 安全出口",
        suggestion="按防火规范添加消防疏散标识",
    ),
    ReviewRule(
        id="ELEC_001", name="接地系统标注", severity=Severity.WARNING,
        check_fn=_check_electrical_ground,
        spec_code="GB 50054-2011", spec_section="3.2 接地设计",
        suggestion="添加接地图层标识接地导体",
    ),
    ReviewRule(
        id="HVAC_001", name="风管标高标注", severity=Severity.WARNING,
        check_fn=_check_hvac_duct,
        spec_code="GB 50736-2012", spec_section="5.6 风管设计",
        suggestion="为风管添加标高标注",
    ),
    ReviewRule(
        id="PLUMB_001", name="排水坡度标注", severity=Severity.WARNING,
        check_fn=_check_plumbing_drain,
        spec_code="GB 50015-2019", spec_section="3.5 管道坡度",
        suggestion="添加排水管道坡度标注",
    ),
    # ─── 新增规则 ───────────────────────────────────────────────────────
    ReviewRule(
        id="ARCH_001", name="楼梯设计合规性", severity=Severity.CRITICAL,
        check_fn=_check_arch_stair,
        spec_code="GB 50096-2011", spec_section="6.4 楼梯",
        suggestion="补充楼梯踏步尺寸、梯段净高标注，确保满足防火规范",
    ),
    ReviewRule(
        id="ARCH_002", name="防火分区标识", severity=Severity.CRITICAL,
        check_fn=_check_fire_compartment,
        spec_code="GB 50016-2014", spec_section="5.3 防火分区",
        suggestion="添加防火分区分隔线及标注",
    ),
    ReviewRule(
        id="ELEC_002", name="配电系统完整性", severity=Severity.WARNING,
        check_fn=_check_electrical_distribution,
        spec_code="GB 50054-2011", spec_section="4.1 配电系统",
        suggestion="补充配电箱柜编号及系统干线标注",
    ),
    ReviewRule(
        id="ELEC_003", name="消防电源标注", severity=Severity.CRITICAL,
        check_fn=_check_electrical_fire_power,
        spec_code="GB 50016-2014", spec_section="10.1 消防电源",
        suggestion="添加消防电源专用标注及双电源切换说明",
    ),
    ReviewRule(
        id="STRUCT_002", name="结构基础标注", severity=Severity.WARNING,
        check_fn=_check_structural_foundation,
        spec_code="GB 50007-2011", spec_section="8.2 基础设计",
        suggestion="补充基础埋深、基底标高及地基承载力标注",
    ),
]


# 添加几何审查规则
if HAS_GEO_RULES:
    RULES.extend(get_geo_rules())


# =============================================================================
# 主审查函数
# =============================================================================

def review_drawing(analysis: dict, options: dict | None = None) -> dict:
    """
    执行图纸智能审查

    参数:
        analysis: inference.py 输出的分析结果字典
                  包含 layers, entity_count, blocks, drawing_type 等
        options: 可选配置，如 include_rules=["TITLE_001", ...], min_severity 等

    返回:
        审查报告字典，包含 issues, summary, specs_linked 等
    """
    options = options or {}
    include_rules = options.get("include_rules")
    exclude_rules = options.get("exclude_rules", [])
    min_severity = options.get("min_severity", "建议")  # 显示此级别以上的

    # 解析 layer_stats（每个图层的统计信息）
    layer_stats_raw = analysis.get("layer_stats", {})
    if isinstance(layer_stats_raw, list):
        # 兼容 [{layer: "WALL", count: 10, ...}, ...] 格式
        layer_stats = {}
        for item in layer_stats_raw:
            layer_stats[item["layer"]] = item
    elif isinstance(layer_stats_raw, dict):
        layer_stats = layer_stats_raw
    else:
        layer_stats = {}

    # 提取 entities 用于深入检查
    entities = analysis.get("entities", [])

    # 过滤规则
    active_rules = []
    for rule in RULES:
        if include_rules and rule.id not in include_rules:
            continue
        if rule.id in exclude_rules:
            continue
        active_rules.append(rule)

    # 执行所有规则
    all_issues = []
    for rule in active_rules:
        issues = rule.run(layer_stats, entities)
        all_issues.extend(issues)

    # P3: 基于几何数据的审查
    geometry = analysis.get("geometry", {})
    drawing_type = analysis.get("drawing_type", {})
    dt_primary = drawing_type.get("primary", "") if isinstance(drawing_type, dict) else str(drawing_type)
    if geometry:
        geo_issues = check_geometry_issues(geometry, dt_primary)
        all_issues.extend(geo_issues)

    # 按严重等级排序
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.SUGGEST: 2}
    all_issues.sort(key=lambda x: severity_order.get(x["severity"], 2))

    # 关联规范（原有硬编码映射 + 新增PDF知识库）
    for issue in all_issues:
        layer = issue.get("layer", "")
        specs = lookup_specs_for_layer(layer)
        if specs and not issue.get("spec_code"):
            issue["spec_code"] = specs[0]["code"]
            issue["spec_name"] = specs[0]["name"]
            issue["spec_section"] = specs[0]["section"]

    # 新增：从PDF知识库搜索相关规范要求
    kb_requirements = []
    drawing_type = analysis.get("drawing_type", {})
    dt_primary = drawing_type.get("primary", "") if isinstance(drawing_type, dict) else str(drawing_type)
    
    # 根据图纸类型确定搜索关键词
    category_keywords = {
        "管道": ["管道", "焊接", "压力", "阀门", "支架", "坡度"],
        "锅炉": ["锅炉", "钢结构", "焊接", "射线", "热处理"],
        "结构": ["混凝土", "钢筋", "钢结构", "焊接", "强度"],
        "电气": ["电气", "电机", "接地", "电缆", "绝缘"],
        "给排水": ["管道", "阀门", "坡度", "水封", "排水"],
        "暖通": ["风管", "保温", "绝热", "空调", "通风"],
        "机电": ["设备", "安装", "焊接", "管道", "电气"],
    }
    
    search_keywords = ["管道", "焊接"]  # 默认
    for cat, kws in category_keywords.items():
        if cat in dt_primary:
            search_keywords = kws
            break
    
    # 搜索PDF知识库
    kb_results = _find_kb_requirements(search_keywords, dt_primary)
    if kb_results:
        kb_requirements = kb_results[:10]  # 最多10条

    # 汇总
    critical_count = sum(1 for i in all_issues if i["severity"] == Severity.CRITICAL)
    warning_count = sum(1 for i in all_issues if i["severity"] == Severity.WARNING)
    suggest_count = sum(1 for i in all_issues if i["severity"] == Severity.SUGGEST)

    # 综合质量评分（0.0~1.0，越高越好）
    total_rules = len(RULES)
    rules_applied_n = len(active_rules)
    # 加权扣分：严重0.3/警告0.1/建议0.02，上限不超1.0
    penalty = critical_count * 0.3 + warning_count * 0.1 + suggest_count * 0.02
    # 规则覆盖率修正：应用规则越多越可靠
    coverage = rules_applied_n / max(total_rules, 1)
    confidence = max(0.0, min(1.0, (1.0 - penalty) * (0.5 + 0.5 * coverage)))

    summary = {
        "total_issues": len(all_issues),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "suggest_count": suggest_count,
        "confidence": round(confidence, 3),   # 综合质量评分 0~1
        "drawing_type": drawing_type,
        "layer_count": len(layer_stats),
        "rules_applied": rules_applied_n,
        "kb_specs_found": len(kb_requirements),
    }

    return {
        "summary": summary,
        "issues": all_issues,
        "kb_requirements": kb_requirements,
        "analysis_version": "1.1",
        "specs_lookup": _build_specs_summary(layer_stats),
    }


def _build_specs_summary(layer_stats: dict) -> dict:
    """构建图层→规范映射摘要"""
    result = {}
    for layer in layer_stats:
        specs = lookup_specs_for_layer(layer)
        if specs:
            result[layer] = [{"code": s["code"], "name": s["name"]} for s in specs]
    return result


def review_summary_text(report: dict) -> str:
    """生成可读的文本审查摘要（用于前端展示）"""
    s = report["summary"]
    lines = [
        f"📋 审查摘要（共 {s['total_issues']} 项问题）",
        f"  🔴 严重: {s['critical_count']} | 🟡 警告: {s['warning_count']} | 🟢 建议: {s['suggest_count']}",
        f"  图纸类型: {s['drawing_type']} | 分析图层数: {s['layer_count']}",
        "",
    ]
    if s["critical_count"] > 0:
        lines.append("⚠️  严重问题（必须修改）：")
        for issue in report["issues"]:
            if issue["severity"] == "严重":
                lines.append(f"  • [{issue['rule_id']}] {issue['description']}")
                if issue.get("suggestion"):
                    lines.append(f"    → {issue['suggestion']}")
        lines.append("")

    if s["warning_count"] > 0:
        lines.append("⚡ 警告项（建议修改）：")
        for issue in report["issues"]:
            if issue["severity"] == "警告":
                lines.append(f"  • [{issue['rule_id']}] {issue['description']}")
                if issue.get("spec_code"):
                    lines.append(f"    依据: {issue['spec_code']} {issue.get('spec_section','')}")
        lines.append("")

    if s["suggest_count"] > 0:
        lines.append("💡 优化建议：")
        for issue in report["issues"]:
            if issue["severity"] == "建议":
                lines.append(f"  • [{issue['rule_id']}] {issue['description']}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# 快捷入口：直接从 analysis dict 审查
# =============================================================================

def quick_review(analysis: dict) -> dict:
    """快速审查（使用默认规则）"""
    return review_drawing(analysis)


# =============================================================================
# API 入口函数（被 api_server.py 调用）
# =============================================================================

def review_blueprint(file_path: str, file_type: str = "dwg", drawing_type: str = "") -> dict:
    """
    从图纸文件直接审查（先分析再审查）
    被 api_server.py /review 端点调用
    
    支持两种调用方式：
    1. review_blueprint("/path/to/file.dwg") - 从文件分析
    2. review_blueprint(analysis_dict, file_type="analysis") - 从已有分析结果审查
    """
    # 如果传入的是已分析结果（dict），直接审查
    if isinstance(file_path, dict):
        analysis = file_path
        if not analysis.get('success', True):
            return {"success": False, "error": analysis.get('error', '分析结果无效')}
        return review_drawing(analysis)
    
    # 从文件分析
    from .dwg_extractor import parse_dxf_file
    from .inference import infer_drawing_type

    suffix = file_path.lower().split('.')[-1]
    if suffix == 'dwg':
        # For DWG, use analyze_dwg
        from .inference import analyze_dwg
        analysis = analyze_dwg(file_path)
        if not analysis.get('success', False):
            return {"success": False, "error": analysis.get('error', 'DWG分析失败')}
    else:
        # For DXF, use parse_dxf_file which correctly reads DXF layers
        dxf_info = parse_dxf_file(file_path)
        if not dxf_info.get('success'):
            return {"success": False, "error": dxf_info.get('error')}
        layers = dxf_info.get('layers', [])
        blocks = dxf_info.get('blocks', [])
        dt = infer_drawing_type(layers, blocks, drawing_type or '')
        analysis = {
            'success': True,
            'drawing_type': dt,
            'layers': layers,
            'blocks': blocks,
            'layer_stats': {l: {'entity_count': 0} for l in layers},
            'total_layers': len(layers),
            'entities': [],
        }

    # Build layer_stats format (compatible with review module)
    if 'layer_stats' not in analysis:
        analysis['layer_stats'] = {}

    return review_drawing(analysis)


def review_analysis(analysis: dict) -> dict:
    """
    从已有 analysis 结果做审查（不需要再分析文件）
    被 api_server.py /review/analysis 端点调用
    """
    return review_drawing(analysis)
