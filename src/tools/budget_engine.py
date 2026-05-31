"""
src/tools/budget_engine.py - EMA 成本预算引擎

Phase 21: 工程量清单 + 单价匹配 + 总造价计算 + 导出

核心能力：
1. 从图纸分析结果提取工程量（实体计数 + 图层语义）
2. 匹配单价库（unit_prices.json）
3. 计算分部分项工程费 + 措施费 + 规费税金
4. 生成工程量清单报告（JSON/文本）
5. 与 LCC 模块联动（建设费用输入）
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# ── 路径 ─────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.parent
UNIT_PRICES_PATH = PROJECT_ROOT / "data" / "unit_prices.json"

# ── 默认参数 ──────────────────────────────────────────────────

DEFAULT_MEASURE_RATE = 0.035       # 措施费率 3.5%
DEFAULT_REGULATION_FEE_RATE = 0.06  # 规费率 6%（按人工费）
DEFAULT_VAT_RATE = 0.09            # 增值税率 9%
DEFAULT_PROFIT_RATE = 0.05         # 利润率 5%
DEFAULT_MANAGEMENT_RATE = 0.08     # 管理费率 8%

# ── 工程量提取规则 ───────────────────────────────────────────

# 图层关键词 → 工程量项目映射
LAYER_TO_ITEM = {
    # 土建
    'WALL': {'item': '墙体砌筑', 'category': '土建工程', 'extract': 'area'},
    '墙体': {'item': '墙体砌筑', 'category': '土建工程', 'extract': 'area'},
    '抹灰': {'item': '墙体抹灰', 'category': '土建工程', 'extract': 'area'},
    'COLUMN': {'item': '混凝土浇筑', 'category': '土建工程', 'extract': 'volume'},
    '柱子': {'item': '混凝土浇筑', 'category': '土建工程', 'extract': 'volume'},
    'BEAM': {'item': '混凝土浇筑', 'category': '土建工程', 'extract': 'volume'},
    '梁': {'item': '混凝土浇筑', 'category': '土建工程', 'extract': 'volume'},
    'SLAB': {'item': '楼板浇筑', 'category': '土建工程', 'extract': 'volume'},
    '板': {'item': '楼板浇筑', 'category': '土建工程', 'extract': 'volume'},
    'REBAR': {'item': '钢筋制安', 'category': '土建工程', 'extract': 'weight'},
    '钢筋': {'item': '钢筋制安', 'category': '土建工程', 'extract': 'weight'},
    'FOUNDATION': {'item': '基础浇筑', 'category': '土建工程', 'extract': 'volume'},
    '基础': {'item': '基础浇筑', 'category': '土建工程', 'extract': 'volume'},
    '模板': {'item': '模板工程', 'category': '土建工程', 'extract': 'area'},
    '土方': {'item': '基础开挖', 'category': '土建工程', 'extract': 'volume'},
    '脚手架': {'item': '脚手架', 'category': '土建工程', 'extract': 'area'},
    # 门窗
    'DOOR': {'item': '木门', 'category': '门窗工程', 'extract': 'count'},
    '门': {'item': '木门', 'category': '门窗工程', 'extract': 'count'},
    'WINDOW': {'item': '铝合金窗', 'category': '门窗工程', 'extract': 'area'},
    '窗': {'item': '铝合金窗', 'category': '门窗工程', 'extract': 'area'},
    '防火门': {'item': '钢质防火门', 'category': '门窗工程', 'extract': 'area'},
    '幕墙': {'item': '玻璃幕墙', 'category': '门窗工程', 'extract': 'area'},
    # 装饰
    '涂料': {'item': '内墙涂料', 'category': '装饰工程', 'extract': 'area'},
    '地砖': {'item': '地砖铺贴', 'category': '装饰工程', 'extract': 'area'},
    '地板': {'item': '地板铺贴', 'category': '装饰工程', 'extract': 'area'},
    '吊顶': {'item': '吊顶', 'category': '装饰工程', 'extract': 'area'},
    '保温': {'item': '外墙保温', 'category': '装饰工程', 'extract': 'area'},
    '石材': {'item': '石材幕墙', 'category': '装饰工程', 'extract': 'area'},
    # 安装
    '给水': {'item': '给排水管道', 'category': '安装工程', 'extract': 'length'},
    '排水': {'item': '排水管道', 'category': '安装工程', 'extract': 'length'},
    '电气': {'item': '电气配管', 'category': '安装工程', 'extract': 'length'},
    '配线': {'item': '电气配线', 'category': '安装工程', 'extract': 'length'},
    '配电': {'item': '配电箱', 'category': '安装工程', 'extract': 'count'},
    '灯具': {'item': '灯具安装', 'category': '安装工程', 'extract': 'count'},
    '开关': {'item': '开关插座', 'category': '安装工程', 'extract': 'count'},
    '喷淋': {'item': '消防喷淋', 'category': '安装工程', 'extract': 'count'},
    '消防管': {'item': '消防管道', 'category': '安装工程', 'extract': 'length'},
    '风管': {'item': '通风管道', 'category': '安装工程', 'extract': 'area'},
    '暖通': {'item': '通风管道', 'category': '安装工程', 'extract': 'area'},
}

# 实体类型 → 工程量项目映射
ENTITY_TO_ITEM = {
    'LINE': {'item': '电气配线', 'category': '安装工程', 'unit': 'm', 'length_factor': 1.0},
    'LWPOLYLINE': {'item': '电气配线', 'category': '安装工程', 'unit': 'm', 'length_factor': 1.0},
    'CIRCLE': {'item': '灯具安装', 'category': '安装工程', 'unit': '套', 'count_factor': 1},
    'INSERT': {'item': '配电箱', 'category': '安装工程', 'unit': '台', 'count_factor': 1},
    'TEXT': None,  # 文本不直接映射工程量
    'MTEXT': None,
}

# 图纸类型 → 单位面积造价（元/m²）
UNIT_COST_PER_SQM = {
    "建筑": 3500,
    "结构": 3200,
    "给排水": 2800,
    "暖通": 3800,
    "电气": 3000,
    "消防": 2500,
    "景观": 1500,
    "市政": 2000,
    "总图": 1800,
    "精装": 4000,
}

# 地区造价系数
REGION_FACTOR = {
    "北京": 1.25, "上海": 1.22, "广州": 1.12, "深圳": 1.18,
    "杭州": 1.10, "南京": 1.08, "成都": 0.95, "武汉": 0.92,
    "重庆": 0.90, "西安": 0.88, "长沙": 0.85, "郑州": 0.82,
    "青岛": 1.02, "大连": 0.98, "厦门": 1.05, "苏州": 1.08,
    "default": 1.0,
}


# ── 单价库加载 ────────────────────────────────────────────────

def load_unit_prices() -> Dict:
    """加载单价库"""
    if UNIT_PRICES_PATH.exists():
        with open(UNIT_PRICES_PATH, encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_unit_price(prices: Dict, item_name: str) -> Optional[Dict]:
    """从单价库查找项目单价"""
    for category, items in prices.items():
        if category.startswith('_'):
            continue
        if item_name in items:
            return items[item_name]
    return None


# ── 工程量提取 ────────────────────────────────────────────────

def extract_quantities_from_analysis(analysis: Dict) -> List[Dict]:
    """
    从图纸分析结果提取工程量清单
    
    策略：
    1. 图层匹配：根据图层名称匹配工程量项目
    2. 实体计数：统计各类型实体数量
    3. 面积估算：根据建筑面积估算面积类工程量
    4. 长度估算：根据管线类图层估算长度
    """
    quantities = []
    prices = load_unit_prices()

    # 获取分析数据
    ai_analysis = analysis.get('ai_analysis', {})
    parse_result = analysis.get('parse_result', {})
    drawing_type = ai_analysis.get('drawing_type', {})
    project_info = ai_analysis.get('project_info', {})
    layer_analysis = ai_analysis.get('layer_analysis', {})

    layers = parse_result.get('layers', [])
    entities = parse_result.get('entities', [])
    metadata = parse_result.get('metadata', {})

    # 建筑面积
    area_sqm = _parse_area(project_info.get('building_area', ''))

    # 已匹配项目（避免重复）
    matched_items = set()

    # ── Step 1: 图层匹配 ──────────────────────────────────
    for layer in layers:
        layer_name = layer.get('name', '')
        if not layer_name:
            continue

        # 检查图层名是否匹配工程量项目
        for keyword, mapping in LAYER_TO_ITEM.items():
            if keyword.upper() in layer_name.upper() or keyword in layer_name:
                item_name = mapping['item']
                if item_name in matched_items:
                    continue
                matched_items.add(item_name)

                # 获取单价
                price_info = get_unit_price(prices, item_name)

                # 估算工程量
                qty = _estimate_quantity(mapping, entities, area_sqm, layer_name)

                quantities.append({
                    'item_name': item_name,
                    'category': mapping['category'],
                    'unit': price_info.get('unit', '㎡') if price_info else '㎡',
                    'quantity': qty,
                    'unit_price': price_info.get('unit_price', 0) if price_info else 0,
                    'total_price': round(qty * (price_info.get('unit_price', 0) if price_info else 0), 2),
                    'source': f'图层:{layer_name}',
                    'note': price_info.get('note', '') if price_info else '',
                })

    # ── Step 2: 实体计数补充 ──────────────────────────────
    entity_counts = _count_entities(entities)
    for entity_type, count in entity_counts.items():
        mapping = ENTITY_TO_ITEM.get(entity_type)
        if not mapping:
            continue

        item_name = mapping['item']
        if item_name in matched_items:
            continue
        matched_items.add(item_name)

        price_info = get_unit_price(prices, item_name)
        qty = count * mapping.get('count_factor', 1)

        quantities.append({
            'item_name': item_name,
            'category': mapping['category'],
            'unit': mapping.get('unit', '个'),
            'quantity': qty,
            'unit_price': price_info.get('unit_price', 0) if price_info else 0,
            'total_price': round(qty * (price_info.get('unit_price', 0) if price_info else 0), 2),
            'source': f'实体:{entity_type}×{count}',
            'note': price_info.get('note', '') if price_info else '',
        })

    # ── Step 3: 按建筑面积估算（补充大类）──────────────────
    if area_sqm > 0:
        # 根据图纸类型补充大类工程量
        dtype = drawing_type.get('primary', '建筑') if isinstance(drawing_type, dict) else str(drawing_type)
        supplementary = _supplementary_quantities(dtype, area_sqm, prices, matched_items)
        quantities.extend(supplementary)

    # 按类别排序
    category_order = ['土建工程', '门窗工程', '装饰工程', '安装工程', '措施费', '规费税金']
    quantities.sort(key=lambda x: category_order.index(x['category']) if x['category'] in category_order else 99)

    return quantities


def _estimate_quantity(mapping: Dict, entities: List[Dict], area_sqm: float, layer_name: str) -> float:
    """估算单个工程量项目的数量"""
    extract_type = mapping.get('extract', 'count')

    if extract_type == 'area':
        # 面积类：根据建筑面积的一定比例
        if area_sqm > 0:
            # 墙体面积约建筑面积的 2.5 倍，抹灰约 3 倍
            if '抹灰' in mapping['item']:
                return round(area_sqm * 3.0, 2)
            elif '涂料' in mapping['item']:
                return round(area_sqm * 2.8, 2)
            elif '保温' in mapping['item']:
                return round(area_sqm * 0.6, 2)
            elif '地砖' in mapping['item'] or '地板' in mapping['item']:
                return round(area_sqm * 0.7, 2)
            elif '吊顶' in mapping['item']:
                return round(area_sqm * 0.5, 2)
            elif '脚手架' in mapping['item']:
                return round(area_sqm * 1.0, 2)
            else:
                return round(area_sqm * 2.5, 2)
        return 100.0  # 默认值

    elif extract_type == 'volume':
        # 体积类：根据建筑面积估算
        if area_sqm > 0:
            if '基础' in mapping['item']:
                return round(area_sqm * 0.15, 2)  # 基础约 15% 建筑面积
            elif '土方' in mapping['item']:
                return round(area_sqm * 0.3, 2)
            else:
                return round(area_sqm * 0.35, 2)  # 混凝土约 0.35m³/m²
        return 50.0

    elif extract_type == 'weight':
        # 重量类：钢筋 kg/m²
        if area_sqm > 0:
            return round(area_sqm * 50, 2)  # 约 50kg/m²
        return 5000.0

    elif extract_type == 'length':
        # 长度类：管线长度
        if area_sqm > 0:
            if '电气' in mapping['item']:
                return round(area_sqm * 3.5, 2)  # 电气管线约 3.5m/m²
            elif '给排水' in mapping['item'] or '排水' in mapping['item']:
                return round(area_sqm * 0.8, 2)
            elif '消防' in mapping['item']:
                return round(area_sqm * 1.2, 2)
            else:
                return round(area_sqm * 2.0, 2)
        return 200.0

    elif extract_type == 'count':
        # 个数类：门/窗/灯具等
        # 统计对应实体数量
        count = _count_layer_entities(entities, layer_name)
        if count > 0:
            return count
        # 根据面积估算
        if area_sqm > 0:
            if '门' in mapping['item']:
                return max(1, round(area_sqm / 100))  # 约 100m²/樘
            elif '窗' in mapping['item']:
                return max(1, round(area_sqm / 50))
            elif '配电箱' in mapping['item']:
                return max(1, round(area_sqm / 2000))
            elif '灯具' in mapping['item']:
                return max(1, round(area_sqm / 30))
            elif '开关' in mapping['item']:
                return max(1, round(area_sqm / 80))
            elif '喷淋' in mapping['item']:
                return max(1, round(area_sqm / 15))
        return 1.0

    return 1.0


def _supplementary_quantities(drawing_type: str, area_sqm: float, prices: Dict, matched_items: set) -> List[Dict]:
    """根据图纸类型补充大类工程量"""
    supplementary = []

    if drawing_type == '建筑' and area_sqm > 0:
        # 补充土建大类
        defaults = [
            ('混凝土浇筑', '土建工程', 'm³', area_sqm * 0.35),
            ('钢筋制安', '土建工程', 't', area_sqm * 0.005),
            ('模板工程', '土建工程', '㎡', area_sqm * 2.5),
        ]
        for item_name, category, unit, qty in defaults:
            if item_name not in matched_items:
                price_info = get_unit_price(prices, item_name)
                supplementary.append({
                    'item_name': item_name,
                    'category': category,
                    'unit': unit,
                    'quantity': round(qty, 2),
                    'unit_price': price_info.get('unit_price', 0) if price_info else 0,
                    'total_price': round(qty * (price_info.get('unit_price', 0) if price_info else 0), 2),
                    'source': f'估算:按建筑面积({area_sqm}㎡)',
                    'note': price_info.get('note', '') if price_info else '',
                })

    return supplementary


def _count_entities(entities: List[Dict]) -> Dict[str, int]:
    """统计各类型实体数量"""
    counts = {}
    for ent in entities:
        etype = ent.get('type', 'UNKNOWN')
        counts[etype] = counts.get(etype, 0) + 1
    return counts


def _count_layer_entities(entities: List[Dict], layer_name: str) -> int:
    """统计指定图层的实体数量"""
    count = 0
    for ent in entities:
        if ent.get('layer', '').upper() == layer_name.upper():
            count += 1
    return count


def _parse_area(area_str: str) -> float:
    """解析建筑面积字符串"""
    if not area_str:
        return 0
    match = re.search(r'([\d,]+\.?\d*)', str(area_str))
    if match:
        return float(match.group(1).replace(',', ''))
    return 0


# ── 造价计算 ──────────────────────────────────────────────────

def calculate_budget(
    quantities: List[Dict],
    area_sqm: float = 0,
    city: str = "",
    project_name: str = "",
    drawing_type: str = "建筑",
) -> Dict[str, Any]:
    """
    计算工程总造价
    
    费用构成：
    1. 分部分项工程费 = Σ(工程量 × 单价)
    2. 措施费 = 分部分项工程费 × 措施费率
    3. 规费 = 人工费 × 规费率（简化：按分部分项的 30% 为人工费）
    4. 税金 = (分部分项 + 措施费 + 规费) × 增值税率
    5. 总造价 = 分部分项 + 措施费 + 规费 + 税金
    """
    prices = load_unit_prices()

    # ── 分部分项工程费 ─────────────────────────────────────
    subtotals = {}  # 按类别汇总
    total_direct = 0.0

    for q in quantities:
        cat = q['category']
        if cat not in subtotals:
            subtotals[cat] = 0.0
        subtotals[cat] += q['total_price']
        total_direct += q['total_price']

    # 地区系数
    region_factor = REGION_FACTOR.get(city, REGION_FACTOR.get('default', 1.0))
    if region_factor != 1.0:
        total_direct *= region_factor
        for cat in subtotals:
            subtotals[cat] = round(subtotals[cat] * region_factor, 2)

    # ── 措施费 ─────────────────────────────────────────────
    measure_fee = total_direct * DEFAULT_MEASURE_RATE

    # ── 规费 ───────────────────────────────────────────────
    # 简化：人工费按分部分项的 30% 估算
    labor_cost = total_direct * 0.30
    regulation_fee = labor_cost * DEFAULT_REGULATION_FEE_RATE

    # ── 税金 ───────────────────────────────────────────────
    pre_tax = total_direct + measure_fee + regulation_fee
    vat = pre_tax * DEFAULT_VAT_RATE
    additional_tax = vat * 0.12  # 附加税

    # ── 总造价 ─────────────────────────────────────────────
    total_cost = pre_tax + vat + additional_tax

    # ── 单位造价 ───────────────────────────────────────────
    cost_per_sqm = total_cost / area_sqm if area_sqm > 0 else 0

    return {
        'project_name': project_name,
        'drawing_type': drawing_type,
        'area_sqm': area_sqm,
        'city': city,
        'region_factor': region_factor,
        'quantities': quantities,
        'subtotals': {k: round(v, 2) for k, v in subtotals.items()},
        'summary': {
            'direct_cost': round(total_direct, 2),
            'measure_fee': round(measure_fee, 2),
            'regulation_fee': round(regulation_fee, 2),
            'vat': round(vat, 2),
            'additional_tax': round(additional_tax, 2),
            'total_cost': round(total_cost, 2),
            'cost_per_sqm': round(cost_per_sqm, 2),
        },
        'rates': {
            'measure_rate': DEFAULT_MEASURE_RATE,
            'regulation_rate': DEFAULT_REGULATION_FEE_RATE,
            'vat_rate': DEFAULT_VAT_RATE,
        },
        'generated_at': datetime.now().isoformat(),
    }


# ── 完整预算流程 ──────────────────────────────────────────────

def generate_budget_from_analysis(
    analysis: Dict,
    city: str = "",
    project_name: str = "",
) -> Dict[str, Any]:
    """
    从图纸分析结果生成完整预算
    
    一键流程：分析结果 → 工程量提取 → 单价匹配 → 造价计算
    """
    ai_analysis = analysis.get('ai_analysis', {})
    drawing_type = ai_analysis.get('drawing_type', {})
    project_info = ai_analysis.get('project_info', {})

    dtype = drawing_type.get('primary', '建筑') if isinstance(drawing_type, dict) else str(drawing_type)
    area_sqm = _parse_area(project_info.get('building_area', ''))

    # 如果面积未提取到，根据图层估算
    if area_sqm <= 0:
        parse_result = analysis.get('parse_result', {})
        layers = parse_result.get('layers', [])
        if isinstance(layers, list) and len(layers) > 0:
            area_sqm = max(1000, len(layers) * 100)

    pname = project_name or project_info.get('project_name', '') or analysis.get('file_name', '未命名项目')

    # 提取工程量
    quantities = extract_quantities_from_analysis(analysis)

    # 如果没有提取到任何工程量，生成默认清单
    if not quantities:
        quantities = _generate_default_quantities(dtype, area_sqm)

    # 计算造价
    budget = calculate_budget(
        quantities=quantities,
        area_sqm=area_sqm,
        city=city,
        project_name=pname,
        drawing_type=dtype,
    )

    return budget


def _generate_default_quantities(drawing_type: str, area_sqm: float) -> List[Dict]:
    """生成默认工程量清单（当无法从图纸提取时）"""
    prices = load_unit_prices()
    defaults = []

    if area_sqm <= 0:
        area_sqm = 5000  # 默认 5000㎡

    if drawing_type in ('建筑', '结构'):
        items = [
            ('混凝土浇筑', '土建工程', 'm³', area_sqm * 0.35),
            ('钢筋制安', '土建工程', 't', area_sqm * 0.005),
            ('模板工程', '土建工程', '㎡', area_sqm * 2.5),
            ('墙体砌筑', '土建工程', 'm³', area_sqm * 0.25),
            ('墙体抹灰', '土建工程', '㎡', area_sqm * 3.0),
        ]
    elif drawing_type in ('给排水', '暖通', '电气', '消防'):
        items = [
            ('给排水管道', '安装工程', 'm', area_sqm * 0.8),
            ('电气配管', '安装工程', 'm', area_sqm * 3.5),
            ('电气配线', '安装工程', 'm', area_sqm * 5.0),
            ('配电箱', '安装工程', '台', max(1, round(area_sqm / 2000))),
            ('灯具安装', '安装工程', '套', max(1, round(area_sqm / 30))),
        ]
    else:
        items = [
            ('混凝土浇筑', '土建工程', 'm³', area_sqm * 0.35),
            ('钢筋制安', '土建工程', 't', area_sqm * 0.005),
            ('模板工程', '土建工程', '㎡', area_sqm * 2.5),
        ]

    for item_name, category, unit, qty in items:
        price_info = get_unit_price(prices, item_name)
        defaults.append({
            'item_name': item_name,
            'category': category,
            'unit': unit,
            'quantity': round(qty, 2),
            'unit_price': price_info.get('unit_price', 0) if price_info else 0,
            'total_price': round(qty * (price_info.get('unit_price', 0) if price_info else 0), 2),
            'source': '默认估算',
            'note': price_info.get('note', '') if price_info else '',
        })

    return defaults


# ── 报告生成 ──────────────────────────────────────────────────

def generate_budget_report(budget: Dict) -> str:
    """生成预算报告文本"""
    lines = []
    lines.append("=" * 72)
    lines.append(" " * 20 + "工程预算书")
    lines.append(" " * 18 + "Construction Budget Report")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"项目名称：{budget['project_name']}")
    lines.append(f"工程类型：{budget['drawing_type']}")
    lines.append(f"建筑面积：{budget['area_sqm']:,.2f} m²")
    if budget.get('city'):
        lines.append(f"工程地点：{budget['city']}（地区系数 {budget['region_factor']}）")
    lines.append("")
    lines.append("-" * 72)
    lines.append("一、分部分项工程量清单")
    lines.append("-" * 72)
    lines.append(f"{'序号':<4} {'项目':<14} {'类别':<8} {'单位':<6} {'数量':>10} {'单价':>10} {'合价':>12}")
    lines.append("-" * 72)

    idx = 0
    current_category = ""
    for q in budget['quantities']:
        if q['category'] != current_category:
            current_category = q['category']
            lines.append(f"  【{current_category}】")
        idx += 1
        lines.append(
            f"{idx:<4} {q['item_name']:<14} {q['category']:<8} {q['unit']:<6} "
            f"{q['quantity']:>10.2f} {q['unit_price']:>10.2f} {q['total_price']:>12.2f}"
        )

    lines.append("-" * 72)

    # 类别汇总
    lines.append("")
    lines.append("二、分部分项工程费汇总")
    lines.append("-" * 50)
    for cat, subtotal in budget['subtotals'].items():
        lines.append(f"  {cat}：{subtotal:>14,.2f} 元")
    lines.append("-" * 50)
    lines.append(f"  分部分项工程费合计：{budget['summary']['direct_cost']:>14,.2f} 元")

    # 总造价汇总
    s = budget['summary']
    rates = budget.get('rates', {'measure_rate': 0.035, 'regulation_rate': 0.06, 'vat_rate': 0.09})
    lines.append("")
    lines.append("三、总造价汇总")
    lines.append("-" * 50)
    lines.append(f"  分部分项工程费：{s['direct_cost']:>14,.2f} 元")
    lines.append(f"  措施费（{rates['measure_rate']*100:.1f}%）：{s['measure_fee']:>14,.2f} 元")
    lines.append(f"  规费（{rates['regulation_rate']*100:.1f}%）：{s['regulation_fee']:>14,.2f} 元")
    lines.append(f"  增值税（{rates['vat_rate']*100:.0f}%）：{s['vat']:>14,.2f} 元")
    lines.append(f"  附加税（12%）：{s['additional_tax']:>14,.2f} 元")
    lines.append("-" * 50)
    lines.append(f"  ★ 总造价：{s['total_cost']:>14,.2f} 元")
    lines.append(f"  ★ 单位造价：{s['cost_per_sqm']:>10,.2f} 元/m²")
    lines.append("")
    lines.append("=" * 72)
    lines.append(f"报告生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append("=" * 72)
    lines.append("")
    lines.append("注：本预算基于图纸工程量估算，实际造价以施工图预算为准。")
    lines.append("    单价参考《建设工程工程量清单计价规范》GB 50500-2013。")

    return "\n".join(lines)


# ── 导出 ──────────────────────────────────────────────────────

def export_budget_json(budget: Dict, output_path: str) -> str:
    """导出预算为 JSON 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(budget, f, ensure_ascii=False, indent=2)
    return output_path


def export_budget_report(budget: Dict, output_path: str) -> str:
    """导出预算报告为文本文件"""
    report = generate_budget_report(budget)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    return output_path


# ── 单例 ──────────────────────────────────────────────────────

_budget_engine = None

def get_budget_engine():
    """获取预算引擎单例"""
    global _budget_engine
    if _budget_engine is None:
        _budget_engine = BudgetEngine()
    return _budget_engine


class BudgetEngine:
    """预算引擎（兼容旧接口）"""

    def __init__(self):
        self.prices = load_unit_prices()

    def generate_budget(self, analysis: Dict, city: str = "", project_name: str = "") -> Dict:
        return generate_budget_from_analysis(analysis, city, project_name)

    def generate_report(self, budget: Dict) -> str:
        return generate_budget_report(budget)

    def export_json(self, budget: Dict, path: str) -> str:
        return export_budget_json(budget, path)

    def export_report(self, budget: Dict, path: str) -> str:
        return export_budget_report(budget, path)
