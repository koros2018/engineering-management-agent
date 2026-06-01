"""
EMA自研工程文档生成器 - 从blueprint-ai/documents.py迁移 (Phase 7+1-C, 2026-05-28)

本模块是 blueprint-ai/src/blueprint_parser/documents.py 的精简迁移版本。
采用核心功能内联策略，删除了对重型子模块（layout_analyzer, text_extractor,
template_engine, sop, mop, eop, lcc）的依赖，所有生成逻辑直接在模块内实现。

依赖：
- src.blueprint.ai.inference  (infer_drawing_type, infer_layer_semantics,
  LAYER_PREFIX_CATEGORY, LAYER_SEMANTICS)
- src.blueprint.review.specs  (lookup_specs_for_layer, get_layer_category)

提供6个核心生成函数：
- generate_full_document_set(analysis)      完整文档集
- generate_design_description(analysis)     设计说明
- generate_technical_disclosure(analysis)   施工技术交底
- generate_quantity_list(analysis)          工程量清单
- generate_change_request(analysis, changes) 技术核定单
- generate_bid_document(analysis)           招投标文件
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

# ── 从 AI 推理模块导入 ──────────────────────────────────────
from src.blueprint.ai.inference import (
    infer_drawing_type,
    infer_layer_semantics,
    LAYER_PREFIX_CATEGORY,
    LAYER_SEMANTICS,
)

# ── 从规范库导入（带内联 fallback） ─────────────────────────
try:
    from src.blueprint.review.specs import lookup_specs_for_layer, get_layer_category
except ImportError:
    # ── 内联规范映射（从 blueprint-ai/spec_mapper.py 精简） ──
    _LAYER_TO_SPECS: Dict[str, List[Dict[str, str]]] = {
        'FIRE': [
            {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '7.4 疏散楼梯', 'requirement': '疏散楼梯净宽>=1.1m'},
            {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '5.5 疏散出口', 'requirement': '疏散距离满足要求'},
        ],
        'EXIT': [
            {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '6.4 安全出口', 'requirement': '安全出口数量>=2个'},
        ],
        'STAIR': [
            {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '6.4 疏散楼梯', 'requirement': '楼梯间耐火极限>=1h'},
            {'code': 'JGJ 67-2019', 'name': '办公建筑设计规范', 'section': '4.4 楼梯', 'requirement': '楼梯踏步高宽比<=1:2'},
        ],
        'COLUMN': [
            {'code': 'GB 50010-2010', 'name': '混凝土结构设计规范', 'section': '6.3 受压构件', 'requirement': '轴压比限值满足抗震要求'},
            {'code': 'GB 50011-2010', 'name': '建筑抗震设计规范', 'section': '3.9 结构材料', 'requirement': '混凝土强度等级>=C30'},
        ],
        'BEAM': [
            {'code': 'GB 50010-2010', 'name': '混凝土结构设计规范', 'section': '6.2 受弯构件', 'requirement': '正截面承载力计算'},
        ],
        'SLAB': [
            {'code': 'GB 50010-2010', 'name': '混凝土结构设计规范', 'section': '9.1 板', 'requirement': '双向板最小厚度>=80mm'},
        ],
        'FOUNDATION': [
            {'code': 'GB 50007-2011', 'name': '建筑地基基础设计规范', 'section': '8.2 基础设计', 'requirement': '地基承载力特征值确定'},
        ],
        'REBAR': [
            {'code': 'GB 50010-2010', 'name': '混凝土结构设计规范', 'section': '8.4 钢筋连接', 'requirement': '钢筋锚固长度>=lae'},
        ],
        'WATERPROOF': [
            {'code': 'GB 50108-2008', 'name': '地下工程防水技术规范', 'section': '4.3 防水混凝土', 'requirement': '抗渗等级>=P6'},
        ],
        'WINDOW': [
            {'code': 'JGJ 151-2008', 'name': '建筑门窗洞口和外墙节能标准', 'section': '4.1 门窗', 'requirement': '气密性>=6级'},
        ],
        'HVAC': [
            {'code': 'GB 50736-2012', 'name': '民用建筑供暖通风与空气调节设计规范', 'section': '5.6 风管设计', 'requirement': '风管风速<=8m/s'},
        ],
        'DUCT': [
            {'code': 'GB 50243-2016', 'name': '通风与空调工程施工质量验收规范', 'section': '6.0 风管制作', 'requirement': '风管板材厚度按风压选择'},
        ],
        'ELECTRICAL': [
            {'code': 'GB 50052-2009', 'name': '供配电系统设计规范', 'section': '5.0 低压配电', 'requirement': '低压配电半径<=200m'},
        ],
        'LIGHTING': [
            {'code': 'GB 50034-2013', 'name': '建筑照明设计标准', 'section': '6.1 照度标准', 'requirement': '办公室照度>=300lx'},
        ],
        'PLUMBING': [
            {'code': 'GB 50015-2019', 'name': '建筑给水排水设计规范', 'section': '3.5 管道', 'requirement': '给水管流速<=2.0m/s'},
        ],
        'FIRE_SPRINKLER': [
            {'code': 'GB 50084-2017', 'name': '自动喷水灭火系统设计规范', 'section': '8.0 喷头布置', 'requirement': '喷头间距<=3.6m'},
        ],
        'HYDRANT': [
            {'code': 'GB 50974-2014', 'name': '消防给水及消火栓系统技术规范', 'section': '7.4 室内消火栓', 'requirement': '室内消火栓充实水柱>=10m'},
        ],
        'CEILING': [
            {'code': 'GB 50222-2017', 'name': '建筑内部装修设计防火规范', 'section': '3.0 装修材料', 'requirement': '顶棚装修材料燃烧性能A级'},
        ],
        'INSULATION': [
            {'code': 'JGJ 26-2018', 'name': '严寒和寒冷地区居住建筑节能设计标准', 'section': '5.2 围护结构', 'requirement': '外墙传热系数<=0.60'},
        ],
        'GREEN': [
            {'code': 'GB/T 50378-2019', 'name': '绿色建筑评价标准', 'section': '4.1 安全耐久', 'requirement': '绿色建筑星级>=三星'},
        ],
        'PILE': [
            {'code': 'JGJ 94-2008', 'name': '建筑桩基技术规范', 'section': '6.2 混凝土灌注桩', 'requirement': '桩身混凝土强度>=C25'},
        ],
        'SEISMIC': [
            {'code': 'GB 50011-2010', 'name': '建筑抗震设计规范', 'section': '3.1 地震作用', 'requirement': '抗震设防烈度按当地标准确定'},
        ],
        'BOILER': [
            {'code': 'DL/T 5190.2-2019', 'name': '电力建设施工技术规范 第2部分：锅炉机组', 'section': '锅炉安装', 'requirement': '锅炉钢架安装垂直度偏差<=高度的1/1000'},
        ],
    }

    def lookup_specs_for_layer(layer_name: str) -> List[Dict[str, str]]:
        """查询图层对应的规范条目"""
        layer_upper = layer_name.upper()
        matched_specs: List[Dict[str, str]] = []
        matched_keys: set = set()
        for key, specs in _LAYER_TO_SPECS.items():
            if key in layer_upper and key not in matched_keys:
                matched_specs.extend(specs)
                matched_keys.add(key)
        return matched_specs

    _CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        '建筑': ['WALL', 'DOOR', 'WINDOW', 'STAIR', 'FLOOR', 'CEILING', 'PARTITION', 'RAILING'],
        '结构': ['COLUMN', 'BEAM', 'SLAB', 'FOUNDATION', 'FOOTING', 'REBAR', 'STEEL', 'STRUCTURE'],
        '机电': ['MECHANICAL', 'ELECTRICAL', 'PLUMBING', 'HVAC', 'MEP', 'EQUIP', 'PIPE', 'DUCT'],
        '暖通': ['HVAC', 'AIR', 'DUCT', 'VENT', 'CHILLER', 'BOILER', 'AHU', 'FAN', 'COIL'],
        '给排水': ['PLUMBING', 'WATER', 'DRAIN', 'SEWER', 'PIPE', 'VALVE', 'FIRE_SPRINKLER'],
        '电气': ['ELECTRICAL', 'POWER', 'LIGHTING', 'CABLE', 'PANEL', 'CIRCUIT', 'SWITCH', 'EARTH'],
        '消防': ['FIRE', 'SPRINKLER', 'ALARM', 'SMOKE', 'EXIT', 'FIRE_Door', 'PUMP'],
        '景观': ['LANDSCAPE', 'PLANT', 'TREE', 'LAWN', 'PATH', 'WALKWAY', 'GREENERY'],
        '节能': ['INSULATION', 'WINDOW', 'GLAZING', 'SHADING', 'SOLAR'],
        '精装': ['CEILING', 'PARTITION', 'DECORATION', 'FINISH', 'TILE'],
        '标注': ['DIM', 'TEXT', 'TITLE', 'NOTE', 'ANNOTATION', 'SYMBOL'],
        '轴线': ['AXIS', 'GRID', 'COLUMN_LINE'],
    }

    def get_layer_category(layer_name: str) -> str:
        """识别图层属于哪个专业类别"""
        layer_upper = layer_name.upper()
        for category, keywords in _CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in layer_upper:
                    return category
        prefix = layer_name[0].upper() if layer_name and layer_name[0].isalpha() else ''
        if prefix in LAYER_PREFIX_CATEGORY:
            return LAYER_PREFIX_CATEGORY[prefix][1]
        return '其他'


# ── 辅助函数 ─────────────────────────────────────────────────

def _get_layer_english(layer_name: str) -> str:
    """Get English category key from layer name."""
    upper = layer_name.upper()
    for pat, (eng, _, _) in LAYER_SEMANTICS.items():
        if pat in upper:
            return eng
    prefix = layer_name[0].upper() if layer_name and layer_name[0].isalpha() else ''
    if prefix in LAYER_PREFIX_CATEGORY:
        return LAYER_PREFIX_CATEGORY[prefix][0]
    return 'unknown'


def _format_confidence(conf: str) -> str:
    """将置信度转为星级标记"""
    return {'high': '★★★', 'medium': '★★☆', 'low': '★☆☆'}.get(conf, '？')


def _estimate_quantities_from_layers(analysis: Dict) -> Dict[str, Any]:
    """
    基于图层统计估算工程量（不依赖 layout_analyzer 的几何分析）
    """
    layers = analysis.get('layers', [])
    geometry = analysis.get('geometry', {})

    category_layer_count: Dict[str, int] = {}
    for layer in layers:
        sem = infer_layer_semantics(layer)
        eng = sem.get('english', 'unknown')
        if sem.get('confidence') != 'none':
            category_layer_count[eng] = category_layer_count.get(eng, 0) + 1

    quantities: Dict[str, Dict[str, Any]] = {}

    wall_layers = category_layer_count.get('wall', 0)
    wall_length = geometry.get('wall_length', 0)
    if wall_length:
        quantities['墙体总长度'] = {'value': wall_length, 'unit': '长度单位', 'confidence': 'high', 'note': '几何提取'}
    elif wall_layers > 0:
        quantities['墙体总长度'] = {'value': wall_layers * 30, 'unit': 'm', 'confidence': 'low', 'note': f'基于{wall_layers}个墙体图层估算'}

    col_layers = category_layer_count.get('column', 0)
    col_count = geometry.get('column_count', 0)
    if col_count:
        quantities['柱子数量'] = {'value': col_count, 'unit': '个', 'confidence': 'high', 'note': '几何提取'}
    elif col_layers > 0:
        quantities['柱子数量（估算）'] = {'value': col_layers * 8, 'unit': '个', 'confidence': 'low', 'note': f'基于{col_layers}个柱图层估算'}

    beam_layers = category_layer_count.get('beam', 0)
    beam_length = geometry.get('beam_length', 0)
    if beam_length:
        quantities['梁总长度'] = {'value': beam_length, 'unit': '长度单位', 'confidence': 'high', 'note': '几何提取'}
    elif beam_layers > 0:
        quantities['梁总长度（估算）'] = {'value': beam_layers * 25, 'unit': 'm', 'confidence': 'low', 'note': f'基于{beam_layers}个梁图层估算'}

    slab_layers = category_layer_count.get('slab', 0)
    slab_area = geometry.get('slab_area', 0)
    if slab_area:
        quantities['楼板/屋面面积'] = {'value': slab_area, 'unit': '面积单位', 'confidence': 'high', 'note': '几何提取'}
    elif slab_layers > 0:
        quantities['楼板/屋面面积（估算）'] = {'value': slab_layers * 200, 'unit': '㎡', 'confidence': 'low', 'note': f'基于{slab_layers}个板图层估算'}

    window_count = geometry.get('window_count', 0)
    door_count = geometry.get('door_count', 0)
    win_layers = category_layer_count.get('window', 0)
    door_layers = category_layer_count.get('door', 0)

    if window_count:
        quantities['窗户数量'] = {'value': window_count, 'unit': '个', 'confidence': 'high', 'note': '几何提取'}
    elif win_layers > 0:
        quantities['窗户数量（估算）'] = {'value': win_layers * 6, 'unit': '个', 'confidence': 'low', 'note': f'基于{win_layers}个窗图层估算'}

    if door_count:
        quantities['门数量'] = {'value': door_count, 'unit': '个', 'confidence': 'high', 'note': '几何提取'}
    elif door_layers > 0:
        quantities['门数量（估算）'] = {'value': door_layers * 4, 'unit': '个', 'confidence': 'low', 'note': f'基于{door_layers}个门图层估算'}

    found_layers = category_layer_count.get('foundation', 0)
    if found_layers > 0:
        quantities['基础工程量（估算）'] = {'value': found_layers * 50, 'unit': 'm³', 'confidence': 'low', 'note': f'基于{found_layers}个基础图层估算'}

    rebar_layers = category_layer_count.get('rebar', 0)
    if rebar_layers > 0:
        quantities['钢筋用量（估算）'] = {'value': rebar_layers * 5, 'unit': 't', 'confidence': 'low', 'note': f'基于{rebar_layers}个钢筋图层估算'}

    return {'quantities': quantities, 'notes': []}


def _collect_specs_for_analysis(analysis: Dict) -> List[Dict[str, str]]:
    """从图纸分析结果中收集所有涉及的规范条目"""
    layers = analysis.get('layers', [])
    all_specs: List[Dict[str, str]] = []
    seen_codes: set = set()
    for layer in layers:
        for spec in lookup_specs_for_layer(layer):
            key = f"{spec['code']}_{spec['section']}"
            if key not in seen_codes:
                all_specs.append(spec)
                seen_codes.add(key)
    return all_specs


def _get_drawing_type_name(analysis: Dict) -> str:
    """获取图纸类型名称"""
    dt = analysis.get('drawing_type', {})
    if isinstance(dt, dict):
        return dt.get('primary', '未知')
    return str(dt)


# ═══════════════════════════════════════════════════════════════
# 核心生成函数
# ═══════════════════════════════════════════════════════════════

def generate_design_description(analysis: Dict) -> str:
    """生成设计说明

    基于图纸分析结果生成结构化设计说明文档，包含：
    - 工程概况
    - 设计依据
    - 主要技术指标
    - 材料规格

    Args:
        analysis: 图纸分析结果字典，需包含 drawing_type, layers, blocks,
                  design_principles, project_info 等字段

    Returns:
        设计说明纯文本字符串
    """
    lines: List[str] = []
    now = datetime.now().strftime('%Y年%m月%d日')
    file_name = analysis.get('file_name', '未知图纸')
    drawing_type = _get_drawing_type_name(analysis)
    project_info = analysis.get('project_info', {})
    design_principles = analysis.get('design_principles', [])
    layers = analysis.get('layers', [])
    blocks = analysis.get('blocks', [])

    # 标题
    lines.append("=" * 60)
    lines.append("设 计 说 明")
    lines.append("=" * 60)
    lines.append(f"图纸名称: {file_name}")
    lines.append(f"图纸类型: {drawing_type}")
    lines.append(f"生成日期: {now}")
    lines.append("")

    # 一、工程概况
    lines.append("一、工程概况")
    lines.append("-" * 40)
    if project_info:
        if 'project_name' in project_info:
            lines.append(f"  项目名称: {project_info['project_name']}")
        if 'building_area' in project_info:
            lines.append(f"  建筑面积: {project_info['building_area']}")
        if 'floor_count' in project_info:
            lines.append(f"  层    数: {project_info['floor_count']}")
        if 'structure_type' in project_info:
            lines.append(f"  结构形式: {project_info['structure_type']}")
        if 'design_unit' in project_info:
            lines.append(f"  设计单位: {project_info['design_unit']}")
        if 'project_number' in project_info:
            lines.append(f"  工程编号: {project_info['project_number']}")
        if 'drawing_number' in project_info:
            lines.append(f"  图    号: {project_info['drawing_number']}")
    else:
        lines.append("  （未提取到工程信息，请补充）")
    lines.append(f"  图纸专业: {drawing_type}")
    lines.append(f"  图层数量: {len(layers)} 个")
    lines.append(f"  块 数 量: {len(blocks)} 个")
    lines.append("")

    # 二、设计依据
    lines.append("二、设计依据")
    lines.append("-" * 40)

    specs = _collect_specs_for_analysis(analysis)
    if specs:
        lines.append("  1) 主要规范及标准：")
        for i, spec in enumerate(specs, 1):
            lines.append(f"     {i}. {spec['code']}《{spec['name']}》")
            lines.append(f"        {spec['section']}：{spec['requirement']}")
    else:
        lines.append("  （未匹配到具体规范条目，按专业通用规范执行）")

    if design_principles:
        lines.append("")
        lines.append("  2) 设计原则：")
        for i, p in enumerate(design_principles, 1):
            lines.append(f"     {i}. {p['type']}：{p['description']}")
    lines.append("")

    # 三、主要技术指标
    lines.append("三、主要技术指标")
    lines.append("-" * 40)

    categories: Dict[str, List[str]] = {}
    for layer in layers:
        layer_name = layer.get('name', '') if isinstance(layer, dict) else str(layer)
        cat = get_layer_category(layer_name)
        categories.setdefault(cat, []).append(layer_name)

    lines.append("  1) 专业图层分布：")
    for cat in sorted(categories.keys()):
        cat_layers = categories[cat]
        lines.append(f"     {cat}：{len(cat_layers)} 个图层")
        show = cat_layers[:5]
        suffix = ' ...' if len(cat_layers) > 5 else ''
        lines.append(f"       示例: {', '.join(show)}{suffix}")
    lines.append(f"     合计：{len(layers)} 个图层")
    lines.append("")

    if drawing_type == '结构' or '结构' in categories:
        lines.append("  2) 结构设计指标：")
        lines.append("     - 混凝土强度等级：不低于 C30")
        lines.append("     - 钢筋：HRB400 级热轧带肋钢筋")
        lines.append("     - 抗震设防烈度：按当地标准确定")
        lines.append("")

    if drawing_type == '建筑' or '建筑' in categories:
        lines.append("  3) 建筑节能指标：")
        lines.append("     - 外墙传热系数：<=0.60 W/(㎡·K)")
        lines.append("     - 外窗气密性：不低于 6 级")
        lines.append("")

    # 四、材料规格
    lines.append("四、主要材料规格")
    lines.append("-" * 40)

    has_concrete = any(
        infer_layer_semantics(l).get('english') in ('column', 'beam', 'slab', 'foundation')
        for l in layers
    )
    has_steel = any(
        infer_layer_semantics(l).get('english') in ('rebar', 'steel')
        for l in layers
    )
    has_masonry = any(
        infer_layer_semantics(l).get('english') == 'wall'
        for l in layers
    )

    mat_idx = 1
    if has_concrete:
        lines.append(f"  {mat_idx}) 混凝土：")
        lines.append("     - 基础/柱/梁/板：C30~C40")
        lines.append("     - 抗渗等级：地下部分不低于 P6")
        mat_idx += 1
    if has_steel:
        lines.append(f"  {mat_idx}) 钢筋：")
        lines.append("     - 主筋：HRB400 级")
        lines.append("     - 箍筋：HPB300 级")
        lines.append("     - 锚固长度：>= lae")
        mat_idx += 1
    if has_masonry:
        lines.append(f"  {mat_idx}) 砌体：")
        lines.append("     - 外墙：200mm 厚加气混凝土砌块")
        lines.append("     - 内墙：100mm/200mm 厚加气混凝土砌块")
        lines.append("     - 砂浆：M5 混合砂浆")
        mat_idx += 1

    if mat_idx == 1:
        lines.append("  （根据图纸专业类型确定材料规格）")

    lines.append("")
    lines.append("=" * 60)
    lines.append("本设计说明基于图纸分析自动生成，具体内容以施工图为准。")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_technical_disclosure(analysis: Dict) -> str:
    """生成施工技术交底

    基于图纸分析结果生成施工技术交底文档，包含：
    - 工程概况
    - 施工工艺
    - 质量标准
    - 安全措施
    - 注意事项

    Args:
        analysis: 图纸分析结果字典

    Returns:
        施工技术交底纯文本字符串
    """
    lines: List[str] = []
    now = datetime.now().strftime('%Y年%m月%d日')
    file_name = analysis.get('file_name', '未知图纸')
    drawing_type = _get_drawing_type_name(analysis)
    project_info = analysis.get('project_info', {})
    construction_requirements = analysis.get('construction_requirements', [])
    layers = analysis.get('layers', [])

    # 标题
    lines.append("=" * 60)
    lines.append("施 工 技 术 交 底")
    lines.append("=" * 60)
    lines.append(f"图纸名称: {file_name}")
    lines.append(f"图纸类型: {drawing_type}")
    lines.append(f"交底日期: {now}")
    lines.append("")

    # 一、工程概况
    lines.append("一、工程概况")
    lines.append("-" * 40)
    proj_name = project_info.get('project_name', '（待填写）')
    lines.append(f"  项目名称: {proj_name}")
    lines.append(f"  图纸专业: {drawing_type}")
    lines.append(f"  施工范围: 按 {file_name} 图纸施工")
    lines.append("")

    # 二、施工工艺
    lines.append("二、施工工艺")
    lines.append("-" * 40)

    construction_methods = _get_construction_methods(drawing_type)
    if construction_methods:
        for method_name, steps in construction_methods:
            lines.append(f"  【{method_name}】")
            for step in steps:
                lines.append(f"    {step}")
            lines.append("")
    else:
        lines.append(f"  按 {drawing_type} 专业相关规范和设计要求施工")
        lines.append("")

    # 三、质量标准
    lines.append("三、质量标准")
    lines.append("-" * 40)
    lines.append("  1) 主控项目：")
    lines.append("     - 必须符合设计要求和国家现行标准")
    if construction_requirements:
        for req in construction_requirements:
            lines.append(f"     - {req['category']}：{req['description']}")
            if req.get('note'):
                lines.append(f"       注：{req['note']}")
    lines.append("")
    lines.append("  2) 一般项目：")
    lines.append("     - 允许偏差应符合《GB 50204》等相关验收规范")
    lines.append("     - 观感质量应达到合格标准")
    lines.append("")

    # 四、安全措施
    lines.append("四、安全措施")
    lines.append("-" * 40)
    lines.append("  1) 进入施工现场必须佩戴安全帽")
    lines.append("  2) 高处作业必须系好安全带")
    lines.append("  3) 临时用电应符合《JGJ 46》规范要求")
    lines.append("  4) 施工机械应定期检查维护")
    lines.append("  5) 特殊工种必须持证上岗")

    if drawing_type == '结构':
        lines.append("  6) 模板支撑体系应经验收合格后方可浇筑")
        lines.append("  7) 钢筋吊装时应注意安全距离")
    elif drawing_type == '建筑':
        lines.append("  6) 外墙施工脚手架应经验收合格")
        lines.append("  7) 门窗安装时注意防坠落")
    elif drawing_type in ('给排水', '暖通'):
        lines.append("  6) 管道试压时严禁超压")
        lines.append("  7) 焊接作业应做好防火措施")
    lines.append("")

    # 五、注意事项
    lines.append("五、注意事项")
    lines.append("-" * 40)
    lines.append("  1) 施工前应仔细阅读图纸，有疑问及时提出")
    lines.append("  2) 各工序应做好交接检和隐蔽工程验收")
    lines.append("  3) 材料进场应报验，不合格材料不得使用")
    lines.append("  4) 施工过程中应做好成品保护")
    lines.append("  5) 发现图纸问题应及时办理设计变更或技术核定")

    layer_str = ' '.join(layers).upper()
    if 'FIRE' in layer_str or '消防' in layer_str:
        lines.append("  6) 【消防专项】消防系统施工后需通过消防验收")
    if 'SEISMIC' in layer_str or '抗震' in layer_str:
        lines.append("  6) 【抗震专项】抗震构造措施必须按图施工")
    if 'WATERPROOF' in layer_str or '防水' in layer_str:
        lines.append("  6) 【防水专项】防水施工后必须做蓄水试验")

    lines.append("")
    lines.append("=" * 60)
    lines.append("本技术交底基于图纸分析自动生成，具体施工以设计文件为准。")
    lines.append("=" * 60)

    return "\n".join(lines)


def _get_construction_methods(drawing_type: str) -> List[tuple]:
    """获取指定图纸类型的施工工艺模板"""
    methods = {
        '建筑': [
            ("墙体砌筑", [
                "1. 砌筑前应清理基层，浇水湿润",
                "2. 砌块应上下错缝，搭接长度>=1/3 砌块长度",
                "3. 灰缝厚度控制在 8~12mm",
                "4. 构造柱与墙体连接处应设马牙槎",
                "5. 砌至梁底时应留 30~50mm 空隙，7天后斜砌挤紧",
            ]),
            ("门窗安装", [
                "1. 门窗框安装应牢固，固定点间距<=600mm",
                "2. 门窗框与墙体间隙采用发泡剂填充",
                "3. 外墙门窗应做好防水密封处理",
                "4. 玻璃安装后应检查密封胶是否连续饱满",
            ]),
            ("防水施工", [
                "1. 基层应平整、干净、干燥",
                "2. 阴阳角应做成圆弧过渡，R>=50mm",
                "3. 防水层施工后需做蓄水试验，不少于 24h",
                "4. 卫生间防水层上翻高度>=300mm",
            ]),
        ],
        '结构': [
            ("钢筋工程", [
                "1. 钢筋进场应检查合格证和复试报告",
                "2. 钢筋连接方式应符合设计要求",
                "3. 锚固长度>=lae，搭接长度>=ll",
                "4. 钢筋保护层厚度：梁+-5mm，板+-3mm",
                "5. 钢筋绑扎应牢固，不得漏绑",
            ]),
            ("混凝土浇筑", [
                "1. 混凝土强度等级应满足设计要求",
                "2. 浇筑前应检查模板支撑体系",
                "3. 振捣应密实，不得漏振、过振",
                "4. 养护不少于 7 天（抗渗混凝土不少于 14 天）",
                "5. 拆模时间应满足强度要求",
            ]),
            ("模板工程", [
                "1. 模板应具有足够的强度、刚度和稳定性",
                "2. 模板接缝应严密，不得漏浆",
                "3. 起拱值：跨度>=4m 时，起拱 1/1000~3/1000",
                "4. 拆模顺序：先支后拆，后支先拆",
            ]),
        ],
        '给排水': [
            ("管道安装", [
                "1. 管道安装前应检查管材质量",
                "2. 管道坡度应符合设计要求",
                "3. 给水管流速<=2.0m/s",
                "4. 管道支架间距按管径和介质确定",
                "5. 安装完成后需做通水/通球试验",
            ]),
            ("压力试验", [
                "1. 给水管道试验压力为工作压力 1.5 倍",
                "2. 稳压 30min，压降<=0.05MPa 为合格",
                "3. 排水管道做通球试验，通球直径>=管道直径 2/3",
            ]),
        ],
        '暖通': [
            ("风管制作安装", [
                "1. 风管板材厚度按风压选择",
                "2. 风管风速<=8m/s",
                "3. 风管安装后需做漏光/漏风试验",
                "4. 支吊架间距：水平风管<=3m，垂直风管<=4m",
            ]),
            ("保温施工", [
                "1. 保温层应在管道试压合格后施工",
                "2. 绝热层厚度按设计值，负偏差<=5mm",
                "3. 接缝须错开，搭接长度>=100mm",
                "4. 防潮层搭接宽度>=50mm",
            ]),
        ],
        '电气': [
            ("配管配线", [
                "1. 管路敷设应横平竖直",
                "2. 管内导线截面积<=管内截面积 40%",
                "3. 导线绝缘电阻>=0.5MΩ",
                "4. 配电箱安装垂直度偏差<=1.5‰",
            ]),
            ("接地与绝缘", [
                "1. 接地电阻测试值<=4Ω",
                "2. 电缆敷设后需做绝缘电阻测试",
                "3. 等电位联结应可靠",
            ]),
        ],
        '消防': [
            ("消防管道", [
                "1. 消防管道应独立设置",
                "2. 室内消火栓充实水柱>=10m",
                "3. 喷头间距<=3.6m",
                "4. 系统安装完成后需做水压试验",
            ]),
        ],
    }
    return methods.get(drawing_type, [])


def generate_quantity_list(analysis: Dict) -> str:
    """生成工程量清单（估算）

    基于图层统计和几何数据（如有）估算工程量。
    优先使用几何数据，否则基于图层经验估算。

    Args:
        analysis: 图纸分析结果字典

    Returns:
        工程量清单纯文本字符串
    """
    lines: List[str] = []
    now = datetime.now().strftime('%Y年%m月%d日')
    file_name = analysis.get('file_name', '未知图纸')
    layers = analysis.get('layers', [])
    blocks = analysis.get('blocks', [])
    geometry = analysis.get('geometry', {})

    lines.append("=" * 60)
    lines.append("工程量估算清单")
    lines.append("=" * 60)
    lines.append(f"图纸: {file_name}")
    lines.append(f"生成时间: {now}")
    lines.append("")

    # 优先使用几何数据
    if geometry:
        lines.append("【说明】以下工程量基于图纸几何数据提取，")
        lines.append("实际工程量应以施工图预算为准。")
        lines.append("")
        lines.append("一、几何统计数据")
        lines.append("-" * 40)
        bbox = geometry.get('bounding_box', {})
        if bbox:
            lines.append(f"图纸范围: {bbox.get('width', 0)} x {bbox.get('height', 0)} ({geometry.get('bounding_box_area', 0)} 面积单位)")
        lines.append(f"实体总数: {geometry.get('entity_count', 0)} 个")
        lines.append(f"总线长: {geometry.get('total_length', 0)} 长度单位")
        lines.append(f"总面积: {geometry.get('total_area', 0)} 面积单位")
        lines.append("")
        lines.append("二、结构工程量（几何提取）")
        lines.append("-" * 40)
        has_struct = False
        for key, label in [('wall_length', '墙体总长度'), ('wall_area', '墙体面积'),
                           ('column_count', '柱子数量'), ('beam_length', '梁总长度'),
                           ('slab_area', '楼板/屋面面积')]:
            val = geometry.get(key, 0)
            if val:
                unit = '个' if 'count' in key else ('长度单位' if 'length' in key else '面积单位')
                lines.append(f"  {label}: {val} {unit}")
                has_struct = True
        if not has_struct:
            lines.append("  未提取到结构几何数据")
        lines.append("")
        lines.append("三、建筑工程量（几何提取）")
        lines.append("-" * 40)
        has_arch = False
        for key, label in [('window_count', '窗户数量'), ('door_count', '门数量')]:
            val = geometry.get(key, 0)
            if val:
                lines.append(f"  {label}: {val} 个")
                has_arch = True
        if not has_arch:
            lines.append("  未提取到建筑几何数据")
        lines.append("")
        lines.append("【注】以施工图预算为准。")
        return "\n".join(lines)

    # Fallback: 基于图层统计估算
    lines.append("【说明】以下工程量为基于图纸图层的估算，")
    lines.append("实际工程量应以施工图预算为准。")
    lines.append("")

    # 按专业分类统计
    categories: Dict[str, List[str]] = {}
    for layer in layers:
        layer_name = layer.get('name', '') if isinstance(layer, dict) else str(layer)
        cat = get_layer_category(layer_name)
        categories.setdefault(cat, []).append(layer_name)

    lines.append("一、图层统计（按专业分类）")
    lines.append("-" * 40)
    for cat in sorted(categories.keys()):
        lines.append(f"  {cat}: {len(categories[cat])}个图层")
    lines.append(f"  合计: {len(layers)}个图层")
    lines.append("")

    # 构件统计
    lines.append("二、构件统计（块引用）")
    lines.append("-" * 40)
    if blocks:
        for block in blocks[:20]:
            lines.append(f"  {block}")
        if len(blocks) > 20:
            lines.append(f"  ... 等共 {len(blocks)} 个块")
    else:
        lines.append("  无块引用")
    lines.append("")

    # 工程量估算
    lines.append("三、主要工程量估算")
    lines.append("-" * 40)
    qty_est = _estimate_quantities_from_layers(analysis)
    for qty_name, qty_info in qty_est.get('quantities', {}).items():
        val = qty_info['value']
        unit = qty_info['unit']
        note = qty_info.get('note', '')
        conf = qty_info.get('confidence', '')
        conf_mark = _format_confidence(conf)
        if isinstance(val, (int, float)):
            if val >= 1000:
                lines.append(f"  {conf_mark} {qty_name}：约{val:,.0f} {unit}（{note}）")
            else:
                lines.append(f"  {conf_mark} {qty_name}：约{val} {unit}（{note}）")
        else:
            lines.append(f"  {conf_mark} {qty_name}：{val} {unit}（{note}）")
    for note in qty_est.get('notes', []):
        lines.append(f"  {note}")
    lines.append("")
    lines.append("【注】★☆☆参考估算，★★☆经验估算，★★★较可靠；以施工图预算为准。")
    return "\n".join(lines)


def generate_change_request(analysis: Dict, changes: List[Dict[str, str]] = None) -> str:
    """生成技术核定单

    基于图纸分析结果和设计变更内容生成技术核定单。

    Args:
        analysis: 图纸分析结果字典
        changes: 变更内容列表，每项为 {item, original, changed, reason}

    Returns:
        技术核定单纯文本字符串
    """
    lines: List[str] = []
    now = datetime.now().strftime('%Y年%m月%d日')
    file_name = analysis.get('file_name', '未知图纸')
    drawing_type = _get_drawing_type_name(analysis)
    project_info = analysis.get('project_info', {})
    layers = analysis.get('layers', [])

    if changes is None:
        changes = []

    # 标题
    lines.append("=" * 60)
    lines.append("技 术 核 定 单")
    lines.append("=" * 60)
    lines.append(f"图纸名称: {file_name}")
    lines.append(f"图纸类型: {drawing_type}")
    lines.append(f"核定日期: {now}")
    lines.append("")

    # 工程信息
    lines.append("一、工程信息")
    lines.append("-" * 40)
    proj_name = project_info.get('project_name', '（待填写）')
    lines.append(f"  项目名称: {proj_name}")
    lines.append(f"  图纸专业: {drawing_type}")
    if 'drawing_number' in project_info:
        lines.append(f"  图    号: {project_info['drawing_number']}")
    lines.append("")

    # 变更内容
    lines.append("二、变更内容")
    lines.append("-" * 40)
    if changes:
        for i, ch in enumerate(changes, 1):
            lines.append(f"  变更项 {i}:")
            if 'item' in ch:
                lines.append(f"    变更部位: {ch['item']}")
            if 'original' in ch:
                lines.append(f"    原设计: {ch['original']}")
            if 'changed' in ch:
                lines.append(f"    变更后: {ch['changed']}")
            if 'reason' in ch:
                lines.append(f"    变更原因: {ch['reason']}")
            lines.append("")
    else:
        lines.append("  （请填写具体变更内容）")
        lines.append("  变更部位: ")
        lines.append("  原设计: ")
        lines.append("  变更后: ")
        lines.append("  变更原因: ")
        lines.append("")

    # 相关规范
    lines.append("三、涉及规范")
    lines.append("-" * 40)
    specs = _collect_specs_for_analysis(analysis)
    if specs:
        for spec in specs[:5]:
            lines.append(f"  {spec['code']}《{spec['name']}》{spec['section']}")
    else:
        lines.append(f"  按 {drawing_type} 专业相关规范执行")
    lines.append("")

    # 影响分析
    lines.append("四、影响分析")
    lines.append("-" * 40)
    lines.append(f"  影响专业: {drawing_type}")
    lines.append(f"  影响图层: {len(layers)} 个")
    lines.append("  工程量影响: （待预算人员核定）")
    lines.append("  工期影响: （待项目经理核定）")
    lines.append("")

    # 签章
    lines.append("五、签章确认")
    lines.append("-" * 40)
    lines.append("  提出人: ____________    日期: ____________")
    lines.append("  审核人: ____________    日期: ____________")
    lines.append("  批准人: ____________    日期: ____________")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def generate_bid_document(analysis: Dict) -> str:
    """生成招投标文件

    基于图纸分析结果生成招标文件概要。

    Args:
        analysis: 图纸分析结果字典

    Returns:
        招投标文件纯文本字符串
    """
    lines: List[str] = []
    now = datetime.now().strftime('%Y年%m月%d日')
    file_name = analysis.get('file_name', '未知图纸')
    drawing_type = _get_drawing_type_name(analysis)
    project_info = analysis.get('project_info', {})
    layers = analysis.get('layers', [])
    blocks = analysis.get('blocks', [])

    # 标题
    lines.append("=" * 60)
    lines.append("招 投 标 文 件（概要）")
    lines.append("=" * 60)
    lines.append(f"图纸名称: {file_name}")
    lines.append(f"专业类别: {drawing_type}")
    lines.append(f"编制日期: {now}")
    lines.append("")

    # 一、招标范围
    lines.append("一、招标范围")
    lines.append("-" * 40)
    proj_name = project_info.get('project_name', '（待填写）')
    lines.append(f"  项目名称: {proj_name}")
    lines.append(f"  招标专业: {drawing_type}")
    lines.append(f"  工程内容: 按 {file_name} 及相关图纸施工")
    if 'building_area' in project_info:
        lines.append(f"  建筑面积: {project_info['building_area']}")
    lines.append("")

    # 二、技术要求
    lines.append("二、技术要求")
    lines.append("-" * 40)
    lines.append("  1) 施工依据：")
    lines.append(f"     - 施工图纸: {file_name}")
    specs = _collect_specs_for_analysis(analysis)
    if specs:
        lines.append("     - 主要规范:")
        for spec in specs[:5]:
            lines.append(f"       {spec['code']}《{spec['name']}》")
    lines.append("")
    lines.append("  2) 主要工程量：")
    qty_est = _estimate_quantities_from_layers(analysis)
    for qty_name, qty_info in qty_est.get('quantities', {}).items():
        val = qty_info['value']
        unit = qty_info['unit']
        if isinstance(val, (int, float)):
            if val >= 1000:
                lines.append(f"     {qty_name}：约{val:,.0f} {unit}")
            else:
                lines.append(f"     {qty_name}：约{val} {unit}")
        else:
            lines.append(f"     {qty_name}：{val} {unit}")
    lines.append("")

    # 三、资质要求
    lines.append("三、投标人资质要求")
    lines.append("-" * 40)
    lines.append("  1) 具备相应专业施工资质")
    lines.append("  2) 项目经理须具备相应资格")
    lines.append("  3) 近三年同类工程业绩不少于 2 项")
    lines.append("  4) 具备有效的安全生产许可证")
    lines.append("")

    # 四、评标办法
    lines.append("四、评标办法")
    lines.append("-" * 40)
    lines.append("  1) 评标方式: 综合评估法")
    lines.append("  2) 评分权重:")
    lines.append("     - 投标报价: 40%")
    lines.append("     - 施工组织设计: 30%")
    lines.append("     - 企业业绩: 15%")
    lines.append("     - 项目管理机构: 15%")
    lines.append("")

    # 五、其他
    lines.append("五、其他要求")
    lines.append("-" * 40)
    lines.append("  1) 投标截止时间: （待确定）")
    lines.append("  2) 开标时间: （待确定）")
    lines.append("  3) 工期要求: （待确定）")
    lines.append("  4) 质量标准: 合格")
    lines.append("")
    lines.append("=" * 60)
    lines.append("本招标文件概要基于图纸分析自动生成，正式文件以招标人发布为准。")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_full_document_set(analysis: Dict) -> Dict[str, Any]:
    """生成完整文档集

    基于图纸分析结果一次性生成所有5种工程文档。

    Args:
        analysis: 图纸分析结果字典

    Returns:
        字典，包含:
        - success: bool
        - analysis: 原始分析结果
        - documents: {design_description, technical_disclosure, quantity_list,
                      change_request, bid_document}
    """
    file_name = analysis.get('file_name', '未知图纸')

    print(f"正在分析图纸: {file_name}")
    drawing_type = _get_drawing_type_name(analysis)
    layers = analysis.get('layers', [])
    blocks = analysis.get('blocks', [])
    print(f"图纸类型: {drawing_type}")
    print(f"图层数量: {len(layers)}")
    print(f"块数量: {len(blocks)}")

    print("正在生成设计说明...")
    design_desc = generate_design_description(analysis)

    print("正在生成工程量清单...")
    qty_list = generate_quantity_list(analysis)

    print("正在生成施工技术交底...")
    tech_disclosure = generate_technical_disclosure(analysis)

    print("正在生成技术核定单...")
    change_req = generate_change_request(analysis)

    print("正在生成招投标文件...")
    bid_doc = generate_bid_document(analysis)

    documents = {
        'design_description': design_desc,
        'quantity_list': qty_list,
        'technical_disclosure': tech_disclosure,
        'change_request': change_req,
        'bid_document': bid_doc,
    }

    return {
        'success': True,
        'analysis': analysis,
        'documents': documents,
    }
