"""
EMA自研几何审查规则 - 从blueprint-ai/review_geo.py迁移 (Phase 7+1-C, 2026-05-28)

基于DXF几何数据的智能审查规则。
不依赖 review.py，避免循环导入。
"""

# 本地定义 severity（避免从engine导入）
CRITICAL = "严重"
WARNING = "警告"
SUGGEST = "建议"


def _make_issue_dict(
    rule_id: str,
    rule_name: str,
    severity: str,
    layer: str = "",
    location: str = "",
    description: str = "",
    detail: str = "",
    suggestion: str = "",
    spec_code: str = "",
    spec_section: str = "",
) -> dict:
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "severity": severity,
        "layer": layer,
        "location": location,
        "description": description,
        "detail": detail,
        "spec_code": spec_code,
        "spec_section": spec_section,
        "suggestion": suggestion,
    }


def _check_wall_door_window_integrity(layer_stats: dict) -> list:
    issues = []
    has_wall = any("WALL" in l.upper() or "墙" in l for l in layer_stats)
    has_door = any("DOOR" in l.upper() or "门" in l for l in layer_stats)
    has_window = any("WINDOW" in l.upper() or "窗" in l for l in layer_stats)

    if has_wall and not (has_door or has_window):
        issues.append(_make_issue_dict(
            "GEO_001", "建筑图门窗完整性", WARNING,
            layer="WALL",
            description="发现墙体图层但未发现门窗图层",
            detail="建筑图通常应包含门窗开口，请检查是否遗漏门窗图层（DOOR/WINDOW）",
            suggestion="补充门窗图层或在墙体图层中标注门窗位置",
            spec_code="GB 50016-2014", spec_section="6.2 建筑开口",
        ))
    return issues


def _check_structural_column_spacing(layer_stats: dict) -> list:
    issues = []
    col_layers = [l for l in layer_stats if "COLUMN" in l.upper() or "柱" in l]
    if not col_layers:
        return issues

    for l in col_layers:
        stats = layer_stats.get(l, {})
        count = stats.get("entity_count", 0)
        if count > 50:
            issues.append(_make_issue_dict(
                "GEO_002", "柱网密度检查", SUGGEST,
                layer=l,
                description=f"柱子数量过多 ({count}个)，可能存在柱网过密问题",
                detail="单层建筑柱子数量通常不超过50根，过密柱网影响使用功能",
                suggestion="复核柱网布置，确认是否符合建筑功能需求",
                spec_code="GB 50010-2010", spec_section="6.3 柱网布置",
            ))
    return issues


def check_geometry_issues(geometry: dict, drawing_type: str) -> list:
    """基于几何数据直接生成审查问题"""
    issues = []
    if not geometry:
        return issues

    bbox = geometry.get("bounding_box", {})
    width = bbox.get("width", 0)
    height = bbox.get("height", 0)
    area = geometry.get("bounding_box_area", 0)
    entity_count = geometry.get("entity_count", 0)
    total_length = geometry.get("total_length", 0)

    # GEO_003: 图纸范围过小
    if 0 < area < 100:
        issues.append(_make_issue_dict(
            "GEO_003", "图纸范围检查", SUGGEST,
            description=f"图纸范围较小 ({width} × {height})，请确认是否为局部详图",
            detail="图纸bounding box面积小于100平方单位，可能是详图或图纸数据不完整",
            suggestion="确认图纸比例和范围是否正确",
            spec_code="GB/T 50001-2017", spec_section="4.0 图幅",
        ))

    # GEO_004: 实体密度过低
    if area > 0:
        density = entity_count / area
        if density < 0.1:
            issues.append(_make_issue_dict(
                "GEO_004", "图纸实体密度检查", SUGGEST,
                description=f"图纸实体密度过低 ({density:.2f} 个/单位面积)",
                detail=f"共 {entity_count} 个实体，分布在 {area} 平方单位范围内",
                suggestion="检查图纸是否完整，确认是否有遗漏的图层或实体",
                spec_code="GB/T 50001-2017", spec_section="3.0 图纸深度",
            ))

    # GEO_005: 建筑图墙体长度过短
    if "建筑" in drawing_type:
        wall_length = geometry.get("wall_length", 0)
        if 0 < wall_length < 20:
            issues.append(_make_issue_dict(
                "GEO_005", "建筑图墙体长度检查", WARNING,
                layer="WALL",
                description=f"建筑图墙体总长度较短 ({wall_length})",
                detail="建筑平面图墙体总长度通常不低于20m",
                suggestion="检查墙体图层是否完整，确认是否有遗漏的墙体",
                spec_code="GB/T 50001-2017", spec_section="7.0 墙体",
            ))

    # GEO_006: 结构图无柱子
    if "结构" in drawing_type:
        col_count = geometry.get("column_count", 0)
        if col_count == 0:
            issues.append(_make_issue_dict(
                "GEO_006", "结构图柱网检查", CRITICAL,
                layer="COLUMN",
                description="结构图未发现柱子，请确认结构柱图层是否完整",
                detail="结构图纸应包含柱子或承重墙等竖向承重构件",
                suggestion="补充结构柱图层，或确认承重墙是否替代了柱子",
                spec_code="GB 50010-2010", spec_section="6.3 柱",
            ))

    # GEO_007: 无楼板区域
    if "建筑" in drawing_type or "结构" in drawing_type:
        slab_area = geometry.get("slab_area", 0)
        if slab_area == 0 and area > 100:
            issues.append(_make_issue_dict(
                "GEO_007", "楼板/屋面图层检查", WARNING,
                layer="SLAB",
                description="未发现闭合楼板/屋面区域，请检查SLAB或FLOOR图层",
                detail="建筑面积较大但无闭合楼板区域，可能存在图层缺失",
                suggestion="添加SLAB或FLOOR图层表示楼板/屋面区域",
                spec_code="GB 50010-2010", spec_section="6.2 楼板",
            ))

    # GEO_008: 梁长度过短但柱数较多
    if "结构" in drawing_type:
        beam_length = geometry.get("beam_length", 0)
        col_count = geometry.get("column_count", 0)
        if col_count > 0 and beam_length > 0:
            avg_beam_per_col = beam_length / col_count
            if avg_beam_per_col < 2:
                issues.append(_make_issue_dict(
                    "GEO_008", "梁柱比例检查", WARNING,
                    layer="BEAM",
                    description=f"梁柱比例异常 (每柱平均梁长 {avg_beam_per_col:.1f})",
                    detail=f"柱数 {col_count}，梁总长 {beam_length}，每柱平均梁长过短",
                    suggestion="复核梁布置，确认是否有遗漏的梁或柱子过多",
                    spec_code="GB 50010-2010", spec_section="6.3 梁",
                ))

    # GEO_009: 门窗数量与墙体长度不匹配
    if "建筑" in drawing_type:
        wall_length = geometry.get("wall_length", 0)
        window_count = geometry.get("window_count", 0)
        door_count = geometry.get("door_count", 0)
        if wall_length > 20:
            actual_openings = window_count + door_count
            if actual_openings == 0:
                issues.append(_make_issue_dict(
                    "GEO_009", "门窗数量检查", WARNING,
                    layer="DOOR/WINDOW",
                    description=f"墙体总长 {wall_length} 但未发现门窗开口",
                    detail="建筑墙体通常需要门窗开口满足采光通风需求",
                    suggestion="补充门窗图层或在墙体中标注开口位置",
                    spec_code="GB 50033-2013", spec_section="4.0 采光",
                ))

    # GEO_010: 疏散距离检查
    if "建筑" in drawing_type:
        if width > 40:
            issues.append(_make_issue_dict(
                "GEO_010", "建筑图疏散距离估算", WARNING,
                description=f"图纸宽度 {width} 超过40m，请确认疏散距离是否符合规范",
                detail="GB 50016-2014：房间内任一点至疏散门≤15m，疏散门至安全出口≤40m",
                suggestion="复核疏散走道长度和安全出口位置",
                spec_code="GB 50016-2014", spec_section="5.5.17",
            ))

    # GEO_011: 防火分区面积估算
    if "建筑" in drawing_type:
        if area > 2500:
            issues.append(_make_issue_dict(
                "GEO_011", "防火分区面积检查", WARNING,
                description=f"图纸面积 {area} 超过2500m²，请确认防火分区划分",
                detail="GB 50016-2014：一、二级耐火等级建筑防火分区最大2500-3000m²",
                suggestion="如需更大面积，应设置防火墙或喷淋系统扩大分区",
                spec_code="GB 50016-2014", spec_section="5.3",
            ))

    # GEO_012: 消防车道宽度检查
    if "总图" in drawing_type or "建筑" in drawing_type:
        if 0 < width < 4:
            issues.append(_make_issue_dict(
                "GEO_012", "消防车道宽度检查", WARNING,
                description=f"图纸最窄处 {width} 小于4m，不满足消防车道要求",
                detail="GB 50016-2014：消防车道净宽度和净空高度均不应小于4.0m",
                suggestion="确保消防车道宽度≥4m",
                spec_code="GB 50016-2014", spec_section="7.1.8",
            ))

    return issues


def get_geo_rules() -> list:
    """返回几何审查规则列表（空列表，review.py直接使用check_geometry_issues）"""
    return []
