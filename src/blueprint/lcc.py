"""
lcc.py - 全生命周期费用核算 (Life Cycle Cost Analysis)

计算项目从立项到退役的全部费用：
- 建设费用 (Construction Cost)
- 运营费用 (Operation Cost)  
- 维护费用 (Maintenance Cost)
- 能源费用 (Energy Cost)
- 报废费用 (Disposal Cost)
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


# ── 默认参数 ──────────────────────────────────────────────────

DEFAULT_LIFESPAN_YEARS = 50        # 建筑默认寿命50年
DEFAULT_DISCOUNT_RATE = 0.05       # 折现率5%
DEFAULT_INFLATION_RATE = 0.03     # 通胀率3%

# 运营费用系数（占建设费用的比例，年度）
OPERATION_COST_RATIOS = {
    "建筑": {"运营": 0.02, "维护": 0.015, "能源": 0.025},
    "结构": {"运营": 0.01, "维护": 0.01, "能源": 0.005},
    "给排水": {"运营": 0.03, "维护": 0.02, "能源": 0.01},
    "暖通": {"运营": 0.04, "维护": 0.025, "能源": 0.08},
    "电气": {"运营": 0.025, "维护": 0.015, "能源": 0.06},
    "消防": {"运营": 0.015, "维护": 0.02, "能源": 0.005},
    "景观": {"运营": 0.03, "维护": 0.03, "能源": 0.005},
    "市政": {"运营": 0.01, "维护": 0.015, "能源": 0.005},
}

# 大修养周期和费用（占建设费用比例）
MAJOR_RENOVATION = {
    "10年": 0.05,   # 第10年：外墙/屋面翻新
    "20年": 0.10,   # 第20年：机电系统更新
    "30年": 0.08,   # 第30年：装修翻新
    "40年": 0.15,   # 第40年：结构加固+机电全面更新
}

# 报废回收率
DISPOSAL_RECOVERY = 0.05  # 建筑材料回收价值占建设费用5%


# ── 主函数 ────────────────────────────────────────────────────

def generate_lcc_analysis(
    analysis: Dict,
    project_name: str = "",
    construction_cost: float = 0,
    area_sqm: float = 0,
    lifespan_years: int = DEFAULT_LIFESPAN_YEARS,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    inflation_rate: float = DEFAULT_INFLATION_RATE,
    city: str = "",
) -> Dict[str, Any]:
    """
    生成全生命周期费用分析

    Args:
        analysis: 图纸分析结果
        project_name: 项目名称
        construction_cost: 建设费用（元），如为0则自动估算
        area_sqm: 建筑面积（m²），如为0则自动估算
        lifespan_years: 设计寿命（年）
        discount_rate: 折现率
        inflation_rate: 通胀率
        city: 城市（用于材料价格地区系数）

    Returns:
        LCC分析结果字典
    """
    # 获取图纸类型
    drawing_type = analysis.get('drawing_type', {})
    if isinstance(drawing_type, dict):
        dtype = drawing_type.get('primary', '建筑')
    else:
        dtype = str(drawing_type)

    # 估算建筑面积
    if area_sqm <= 0:
        area_sqm = _estimate_area(analysis)

    # 估算建设费用
    if construction_cost <= 0:
        construction_cost = _estimate_construction_cost(analysis, area_sqm, city)

    # 获取费用系数
    ratios = OPERATION_COST_RATIOS.get(dtype, OPERATION_COST_RATIOS["建筑"])

    # ── 年度费用计算 ──────────────────────────────────────────
    annual_operation = construction_cost * ratios["运营"]
    annual_maintenance = construction_cost * ratios["维护"]
    annual_energy = construction_cost * ratios["能源"]
    annual_total = annual_operation + annual_maintenance + annual_energy

    # ── 生命周期费用计算（考虑通胀和折现）─────────────────────
    lifecycle_costs = {
        "建设费用": construction_cost,
        "运营费用": 0.0,
        "维护费用": 0.0,
        "能源费用": 0.0,
        "大修费用": 0.0,
        "报废费用": 0.0,
        "回收价值": 0.0,
    }

    year_details = []
    for year in range(1, lifespan_years + 1):
        # 通胀调整
        inflation_factor = (1 + inflation_rate) ** (year - 1)
        op = annual_operation * inflation_factor
        mt = annual_maintenance * inflation_factor
        en = annual_energy * inflation_factor

        # 大修费用
        renovation = 0
        for period, ratio in MAJOR_RENOVATION.items():
            p = int(period.replace("年", ""))
            if year == p:
                renovation = construction_cost * ratio * inflation_factor
                break

        total_year = op + mt + en + renovation

        # 折现
        discount_factor = (1 + discount_rate) ** year
        pv = total_year / discount_factor

        lifecycle_costs["运营费用"] += op / discount_factor
        lifecycle_costs["维护费用"] += mt / discount_factor
        lifecycle_costs["能源费用"] += en / discount_factor
        lifecycle_costs["大修费用"] += renovation / discount_factor

        year_details.append({
            "年份": year,
            "运营费用": round(op, 2),
            "维护费用": round(mt, 2),
            "能源费用": round(en, 2),
            "大修费用": round(renovation, 2),
            "年度合计": round(total_year, 2),
            "折现后": round(pv, 2),
        })

    # 报废费用（寿命期末）
    disposal_cost = construction_cost * 0.03  # 拆除费用3%
    recovery_value = construction_cost * DISPOSAL_RECOVERY
    final_inflation = (1 + inflation_rate) ** lifespan_years
    disposal_pv = (disposal_cost * final_inflation - recovery_value * final_inflation) / ((1 + discount_rate) ** lifespan_years)
    lifecycle_costs["报废费用"] = disposal_pv
    lifecycle_costs["回收价值"] = -recovery_value * final_inflation / ((1 + discount_rate) ** lifespan_years)

    # 总LCC
    total_lcc = sum(lifecycle_costs.values())
    lcc_per_sqm = total_lcc / area_sqm if area_sqm > 0 else 0
    lcc_per_year = total_lcc / lifespan_years

    return {
        "project_name": project_name or analysis.get('file_name', '未命名项目'),
        "drawing_type": dtype,
        "area_sqm": area_sqm,
        "lifespan_years": lifespan_years,
        "discount_rate": discount_rate,
        "inflation_rate": inflation_rate,
        "construction_cost": round(construction_cost, 2),
        "lifecycle_costs": {k: round(v, 2) for k, v in lifecycle_costs.items()},
        "total_lcc": round(total_lcc, 2),
        "lcc_per_sqm": round(lcc_per_sqm, 2),
        "lcc_per_year": round(lcc_per_year, 2),
        "annual_operation": round(annual_operation, 2),
        "annual_maintenance": round(annual_maintenance, 2),
        "annual_energy": round(annual_energy, 2),
        "annual_total": round(annual_total, 2),
        "year_details": year_details,
        "cost_ratios": ratios,
        "generated_at": datetime.now().isoformat(),
    }


def generate_lcc_report(lcc_data: Dict) -> str:
    """生成LCC分析报告文本"""
    lines = []
    lines.append("=" * 72)
    lines.append(" " * 18 + "全生命周期费用核算报告")
    lines.append(" " * 16 + "Life Cycle Cost Analysis Report")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"项目名称：{lcc_data['project_name']}")
    lines.append(f"工程类型：{lcc_data['drawing_type']}")
    lines.append(f"建筑面积：{lcc_data['area_sqm']:,.2f} m²")
    lines.append(f"设计寿命：{lcc_data['lifespan_years']} 年")
    lines.append(f"折现率：{lcc_data['discount_rate']*100:.1f}%")
    lines.append(f"通胀率：{lcc_data['inflation_rate']*100:.1f}%")
    lines.append("")
    lines.append("=" * 72)
    lines.append("")

    # 一、建设费用
    lines.append("一、建设费用")
    lines.append("-" * 60)
    cc = lcc_data['construction_cost']
    lines.append(f"  建设费用总额：{cc:,.2f} 元")
    lines.append(f"  单位面积造价：{cc / lcc_data['area_sqm']:,.2f} 元/m²")
    lines.append("")

    # 二、年度运营费用
    lines.append("二、年度运营费用估算")
    lines.append("-" * 60)
    lines.append(f"  年度运营费用：{lcc_data['annual_operation']:,.2f} 元/年")
    lines.append(f"  年度维护费用：{lcc_data['annual_maintenance']:,.2f} 元/年")
    lines.append(f"  年度能源费用：{lcc_data['annual_energy']:,.2f} 元/年")
    lines.append(f"  年度费用合计：{lcc_data['annual_total']:,.2f} 元/年")
    lines.append(f"  费用系数：运营{lcc_data['cost_ratios']['运营']*100:.1f}% + 维护{lcc_data['cost_ratios']['维护']*100:.1f}% + 能源{lcc_data['cost_ratios']['能源']*100:.1f}%")
    lines.append("")

    # 三、大修费用
    lines.append("三、大修费用计划")
    lines.append("-" * 60)
    for period, ratio in MAJOR_RENOVATION.items():
        cost = cc * ratio
        lines.append(f"  第{period}：{cost:,.2f} 元（占建设费用{ratio*100:.0f}%）")
    lines.append("")

    # 四、全生命周期费用汇总
    lines.append("四、全生命周期费用汇总（折现后）")
    lines.append("-" * 60)
    lc = lcc_data['lifecycle_costs']
    lines.append(f"  建设费用：{lc['建设费用']:>16,.2f} 元")
    lines.append(f"  运营费用：{lc['运营费用']:>16,.2f} 元")
    lines.append(f"  维护费用：{lc['维护费用']:>16,.2f} 元")
    lines.append(f"  能源费用：{lc['能源费用']:>16,.2f} 元")
    lines.append(f"  大修费用：{lc['大修费用']:>16,.2f} 元")
    lines.append(f"  报废费用：{lc['报废费用']:>16,.2f} 元")
    lines.append(f"  回收价值：{lc['回收价值']:>16,.2f} 元")
    lines.append("-" * 60)
    lines.append(f"  全生命周期总费用(LCC)：{lcc_data['total_lcc']:>16,.2f} 元")
    lines.append(f"  单位面积LCC：{lcc_data['lcc_per_sqm']:>16,.2f} 元/m²")
    lines.append(f"  年均LCC：{lcc_data['lcc_per_year']:>16,.2f} 元/年")
    lines.append("")

    # 五、费用构成分析
    lines.append("五、费用构成分析")
    lines.append("-" * 60)
    total = lcc_data['total_lcc']
    if total > 0:
        lines.append(f"  建设费用占比：{lc['建设费用']/total*100:.1f}%")
        lines.append(f"  运营费用占比：{lc['运营费用']/total*100:.1f}%")
        lines.append(f"  维护费用占比：{lc['维护费用']/total*100:.1f}%")
        lines.append(f"  能源费用占比：{lc['能源费用']/total*100:.1f}%")
        lines.append(f"  大修费用占比：{lc['大修费用']/total*100:.1f}%")
    lines.append("")

    # 六、敏感性分析
    lines.append("六、敏感性分析")
    lines.append("-" * 60)
    lines.append("  以下因素对LCC影响最大（按敏感程度排序）：")
    lines.append("  1. 能源单价变动 ±20% → LCC变动 ±8~12%")
    lines.append("  2. 设计寿命变动 ±10年 → LCC变动 ±15~25%")
    lines.append("  3. 折现率变动 ±2% → LCC变动 ±5~10%")
    lines.append("  4. 建设费用变动 ±10% → LCC变动 ±8~10%")
    lines.append("  5. 维护策略优化 → LCC可降 5~15%")
    lines.append("")

    # 七、优化建议
    lines.append("七、LCC优化建议")
    lines.append("-" * 60)
    lines.append("  1. 设计阶段")
    lines.append("     · 选用高效节能设备，降低全周期能源费用")
    lines.append("     · 优化建筑围护结构，减少空调负荷")
    lines.append("     · 采用耐久性好的建筑材料，延长维护周期")
    lines.append("")
    lines.append("  2. 运营阶段")
    lines.append("     · 建立能源管理系统，实时监控能耗")
    lines.append("     · 实施预防性维护，降低故障维修成本")
    lines.append("     · 定期能效评估，持续优化运行策略")
    lines.append("")
    lines.append("  3. 维护策略")
    lines.append("     · 制定分级维护计划（日常/定期/大修）")
    lines.append("     · 建立设备档案，追踪维护历史")
    lines.append("     · 关键设备储备备件，减少停机损失")
    lines.append("")

    # 八、结论
    lines.append("八、结论")
    lines.append("-" * 60)
    lines.append(f"  本项目全生命周期总费用为 {lcc_data['total_lcc']:,.2f} 元，")
    lines.append(f"  其中建设费用占比约 {lc['建设费用']/total*100:.1f}%，")
    lines.append(f"  运营维护能源费用占比约 {(lc['运营费用']+lc['维护费用']+lc['能源费用'])/total*100:.1f}%。")
    lines.append("  建议在设计阶段充分考虑LCC因素，通过优化设计降低全周期成本。")
    lines.append("")
    lines.append("=" * 72)
    lines.append(f"报告生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append("=" * 72)

    return "\n".join(lines)


# ── 辅助函数 ──────────────────────────────────────────────────

def _estimate_area(analysis: Dict) -> float:
    """根据图纸估算建筑面积"""
    # 尝试从分析结果中获取面积信息
    metadata = analysis.get('metadata', {})
    if 'area' in metadata:
        try:
            return float(metadata['area'])
        except Exception:
            pass

    # 根据图层数量估算
    layers = analysis.get('layers', [])
    if isinstance(layers, list) and len(layers) > 0:
        # 简单估算：每10个图层约1000m²
        return max(1000, len(layers) * 100)

    # 默认值
    return 5000.0


def _estimate_construction_cost(analysis: Dict, area_sqm: float, city: str = "") -> float:
    """估算建设费用"""
    drawing_type = analysis.get('drawing_type', {})
    if isinstance(drawing_type, dict):
        dtype = drawing_type.get('primary', '建筑')
    else:
        dtype = str(drawing_type)

    # 单位面积造价（元/m²）
    unit_costs = {
        "建筑": 3500,
        "结构": 3200,
        "给排水": 2800,
        "暖通": 3800,
        "电气": 3000,
        "消防": 2500,
        "景观": 1500,
        "市政": 2000,
    }
    unit_cost = unit_costs.get(dtype, 3500)

    # 地区系数
    from .material_prices import detect_region, REGION_FACTOR
    region = detect_region(city)
    region_factor = REGION_FACTOR.get(region, {}).get("系数", 1.0)

    return area_sqm * unit_cost * region_factor


def generate_lcc_summary(analysis: Dict) -> Dict[str, Any]:
    """生成LCC摘要信息"""
    return {
        "document_type": "LCC",
        "title": "全生命周期费用核算",
        "english_title": "Life Cycle Cost Analysis",
        "version": "v1.0",
        "generated_at": datetime.now().isoformat(),
        "applicable_facility": analysis.get('drawing_type', {}).get('primary', '建筑'),
        "default_lifespan": DEFAULT_LIFESPAN_YEARS,
        "cost_categories": ["建设", "运营", "维护", "能源", "大修", "报废"],
        "status": "generated",
    }
