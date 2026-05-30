"""
mop.py - 维护作业程序 (Maintenance Operating Procedures)

制定设备设施的日常维护、定期保养、检修程序，延长资产寿命。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


def generate_mop_document(
    analysis: Dict,
    project_name: str = "",
    facility_type: str = "建筑",
    equipment_list: List[Dict] = None,
) -> str:
    """
    生成维护作业程序(MOP)文档

    Args:
        analysis: 图纸分析结果
        project_name: 项目名称
        facility_type: 设施类型
        equipment_list: 设备清单（如不提供则自动生成）

    Returns:
        MOP文档文本
    """
    if equipment_list is None:
        equipment_list = _auto_generate_equipment(analysis)

    lines = []
    lines.append("=" * 72)
    lines.append(" " * 20 + "维护作业程序 (MOP)")
    lines.append(" " * 18 + "Maintenance Operating Procedures")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"文档编号：MOP-{datetime.now().strftime('%Y%m%d')}-001")
    lines.append(f"编制日期：{datetime.now().strftime('%Y年%m月%d日')}")
    lines.append(f"项目名称：{project_name or analysis.get('file_name', '未命名项目')}")
    lines.append(f"设施类型：{facility_type}")
    lines.append("")
    lines.append("编制单位：________________________")
    lines.append("审核人：________________________")
    lines.append("批准人：________________________")
    lines.append("")
    lines.append("=" * 72)
    lines.append("")

    # 一、总则
    lines.append("一、总则")
    lines.append("-" * 60)
    lines.append("1.1 目的")
    lines.append("    规范设备设施的维护管理，建立预防性维护体系，")
    lines.append("    延长设备使用寿命，降低故障率和维修成本。")
    lines.append("")
    lines.append("1.2 适用范围")
    lines.append(f"    适用于{facility_type}内所有机电设备、建筑设施及配套系统的维护保养。")
    lines.append("")
    lines.append("1.3 维护原则")
    lines.append("    · 预防为主：按计划执行预防性维护，避免事后维修")
    lines.append("    · 安全第一：维护作业必须遵守安全规程，确保人员和设备安全")
    lines.append("    · 质量为本：维护后设备性能必须恢复到规定标准")
    lines.append("    · 记录完整：每次维护必须填写记录，建立设备档案")
    lines.append("")

    # 二、设备清单
    lines.append("二、设备清单与维护周期")
    lines.append("-" * 60)
    lines.append(f"{'序号':<4}{'设备名称':<16}{'位置':<12}{'维护周期':<10}{'责任人':<10}")
    lines.append("-" * 60)
    for i, eq in enumerate(equipment_list, 1):
        name = eq.get('name', '未知设备')[:14]
        loc = eq.get('location', '-')[:10]
        cycle = eq.get('cycle', '每月')[:8]
        resp = eq.get('responsible', '维护技师')[:8]
        lines.append(f"{i:<4}{name:<16}{loc:<12}{cycle:<10}{resp:<10}")
    lines.append("")

    # 三、维护计划
    lines.append("三、年度维护计划")
    lines.append("-" * 60)
    lines.append(f"{'月份':<6}{'维护项目':<30}{'重点内容':<24}")
    lines.append("-" * 60)
    annual_plan = [
        ("1月", "消防系统年度检测", "火灾报警、喷淋、消火栓全面检测"),
        ("2月", "空调系统换季保养", "清洗过滤网、检查冷媒、润滑风机"),
        ("3月", "电梯年度检验", "安全钳、限速器、缓冲器检验"),
        ("4月", "给排水系统检修", "水泵保养、管路检查、阀门维护"),
        ("5月", "电气系统预防性试验", "绝缘测试、接地电阻、继保校验"),
        ("6月", "防雷接地检测", "避雷针、接地网、SPD检测"),
        ("7月", "空调系统 peak season 保障", "冷却塔清洗、主机保养"),
        ("8月", "电梯中期保养", "曳引机、控制柜、门机系统"),
        ("9月", "消防系统季度检查", "灭火器换药、应急照明测试"),
        ("10月", "供暖系统启动前检查", "锅炉、换热器、管路保温"),
        ("11月", "门窗密封检查", "密封条更换、五金件维护"),
        ("12月", "年度综合评估", "设备状态评估、下年度维护计划"),
    ]
    for month, item, detail in annual_plan:
        lines.append(f"{month:<6}{item:<30}{detail:<24}")
    lines.append("")

    # 四、维护作业程序
    lines.append("四、典型维护作业程序")
    lines.append("-" * 60)

    # 选择3个典型设备生成详细程序
    typical_equipment = equipment_list[:3] if len(equipment_list) >= 3 else equipment_list
    for i, eq in enumerate(typical_equipment, 1):
        lines.append("")
        lines.append(f"4.{i} {eq.get('name', '设备')}维护程序")
        lines.append("~" * 60)
        content = _generate_maintenance_procedure(eq, analysis)
        lines.extend(content)

    # 五、备件管理
    lines.append("")
    lines.append("五、备件与材料管理")
    lines.append("-" * 60)
    lines.append("5.1 备件清单")
    lines.append("    建立《关键备件清单》，包括：")
    lines.append("    · 易损件（密封圈、轴承、皮带、保险丝等）")
    lines.append("    · 关键件（电机、控制器、传感器、阀门等）")
    lines.append("    · 耗材（润滑油、清洗剂、绝缘胶带等）")
    lines.append("")
    lines.append("5.2 库存管理")
    lines.append("    · 安全库存：关键备件保持1-2件安全库存")
    lines.append("    · 最低库存：设定最低库存量，低于时自动预警")
    lines.append("    · 先进先出：备件按入库时间顺序使用")
    lines.append("    · 定期盘点：每季度盘点一次，账物相符")
    lines.append("")
    lines.append("5.3 供应商管理")
    lines.append("    · 建立合格供应商名录（至少2家/类）")
    lines.append("    · 关键备件采购周期：≤7个工作日")
    lines.append("    · 紧急备件24小时内到场")
    lines.append("")

    # 六、故障处理
    lines.append("六、故障应急处理")
    lines.append("-" * 60)
    lines.append("6.1 故障分级")
    lines.append("    Ⅰ级（紧急）：威胁人身安全或重大财产损失")
    lines.append("              → 立即停机，启动应急预案，2小时内响应")
    lines.append("    Ⅱ级（重要）：影响主要功能或大面积停用")
    lines.append("              → 4小时内响应，24小时内恢复")
    lines.append("    Ⅲ级（一般）：局部功能异常，不影响主体运行")
    lines.append("              → 24小时内响应，72小时内恢复")
    lines.append("")
    lines.append("6.2 故障处理流程")
    lines.append("    发现故障 → 报告值班人员 → 现场确认 → 制定方案")
    lines.append("    → 组织实施 → 验收确认 → 记录归档")
    lines.append("")

    # 七、记录与评估
    lines.append("七、维护记录与绩效评估")
    lines.append("-" * 60)
    lines.append("7.1 维护记录内容")
    lines.append("    · 设备名称/编号、维护日期、维护人员")
    lines.append("    · 维护项目、更换部件、使用材料")
    lines.append("    · 维护前后参数对比")
    lines.append("    · 遗留问题和建议")
    lines.append("")
    lines.append("7.2 绩效指标")
    lines.append("    · 设备完好率：≥98%")
    lines.append("    · 计划维护完成率：≥95%")
    lines.append("    · 故障响应时间：Ⅰ级≤2h，Ⅱ级≤4h，Ⅲ级≤24h")
    lines.append("    · 平均修复时间(MTTR)：≤4h")
    lines.append("    · 平均无故障时间(MTBF)：≥2000h")
    lines.append("")

    # 附录
    lines.append("")
    lines.append("附录：维护记录表模板")
    lines.append("-" * 60)
    lines.append(f"  设备名称：__________  设备编号：__________")
    lines.append(f"  维护日期：__________  维护人员：__________")
    lines.append(f"  维护类型：□日常  □定期  □故障  □其他")
    lines.append(f"  维护内容：")
    lines.append(f"  ____________________________________________")
    lines.append(f"  更换部件：__________________________________")
    lines.append(f"  维护结果：□正常  □异常（说明：____________）")
    lines.append(f"  验收人：__________  日期：__________")
    lines.append("")
    lines.append("=" * 72)

    return "\n".join(lines)


def _auto_generate_equipment(analysis: Dict) -> List[Dict]:
    """根据图纸分析自动生成设备清单"""
    drawing_type = analysis.get('drawing_type', {})
    if isinstance(drawing_type, dict):
        dtype = drawing_type.get('primary', '建筑')
    else:
        dtype = str(drawing_type)

    # 基础设备清单
    base_equipment = [
        {"name": "电梯", "location": "井道", "cycle": "半月", "responsible": "电梯维保"},
        {"name": "消防泵", "location": "泵房", "cycle": "每周", "responsible": "消防维保"},
        {"name": "生活水泵", "location": "泵房", "cycle": "每月", "responsible": "给排水"},
        {"name": "空调主机", "location": "机房", "cycle": "每月", "responsible": "暖通"},
        {"name": "新风机组", "location": "机房", "cycle": "每季", "responsible": "暖通"},
        {"name": "配电柜", "location": "配电室", "cycle": "每月", "responsible": "电气"},
        {"name": "变压器", "location": "变电所", "cycle": "每季", "responsible": "电气"},
        {"name": "应急发电机", "location": "发电机房", "cycle": "每月", "responsible": "电气"},
        {"name": "火灾报警控制器", "location": "消控室", "cycle": "每日", "responsible": "消防"},
        {"name": "排烟风机", "location": "屋顶", "cycle": "每季", "responsible": "暖通"},
        {"name": "污水处理设备", "location": "地下", "cycle": "每月", "responsible": "给排水"},
        {"name": "门禁系统", "location": "出入口", "cycle": "每月", "responsible": "弱电"},
    ]

    # 根据图纸类型增减
    if dtype == '给排水':
        base_equipment.extend([
            {"name": "雨水泵", "location": "集水坑", "cycle": "每月", "responsible": "给排水"},
            {"name": "中水回用设备", "location": "设备间", "cycle": "每月", "responsible": "给排水"},
        ])
    elif dtype == '电气':
        base_equipment.extend([
            {"name": "UPS", "location": "机房", "cycle": "每月", "responsible": "电气"},
            {"name": "配电箱", "location": "各楼层", "cycle": "每季", "responsible": "电气"},
        ])
    elif dtype == '暖通':
        base_equipment.extend([
            {"name": "冷却塔", "location": "屋顶", "cycle": "每月", "responsible": "暖通"},
            {"name": "风机盘管", "location": "各房间", "cycle": "每季", "responsible": "暖通"},
        ])

    return base_equipment


def _generate_maintenance_procedure(equipment: Dict, analysis: Dict) -> List[str]:
    """生成单个设备的维护程序"""
    name = equipment.get('name', '设备')
    cycle = equipment.get('cycle', '每月')

    return [
        f"【{name} - {cycle}维护程序】",
        "",
        "维护前准备：",
        f"  1. 准备{ name }专用维护工具包",
        "  2. 查阅上次维护记录，了解设备状态",
        "  3. 准备安全防护用品（绝缘手套、安全帽等）",
        "  4. 确认设备已停机并挂牌",
        "",
        "维护步骤：",
        "  1. 外观检查",
        "     · 检查设备外观有无损伤、变形、锈蚀",
        "     · 检查连接件有无松动",
        "     · 检查管路有无渗漏",
        "",
        "  2. 清洁保养",
        "     · 清除设备表面灰尘和油污",
        "     · 清洁过滤器/滤网",
        "     · 清理周边环境",
        "",
        "  3. 功能检测",
        "     · 手动盘车，检查转动灵活",
        "     · 测量绝缘电阻（电气设备）",
        "     · 检查密封性能",
        "",
        "  4. 润滑保养",
        "     · 按规定补充或更换润滑油",
        "     · 检查油位、油质",
        "     · 润滑运动部件",
        "",
        "  5. 紧固调整",
        "     · 紧固松动的螺栓",
        "     · 调整皮带张紧度",
        "     · 校准仪表读数",
        "",
        "维护后确认：",
        "  · 恢复设备运行状态",
        "  · 观察运行30分钟，确认无异常",
        "  · 填写维护记录",
        "  · 清理现场",
        "",
    ]


def generate_mop_summary(analysis: Dict) -> Dict[str, Any]:
    """生成MOP文档摘要信息"""
    equipment = _auto_generate_equipment(analysis)
    return {
        "document_type": "MOP",
        "title": "维护作业程序",
        "english_title": "Maintenance Operating Procedures",
        "version": "v1.0",
        "generated_at": datetime.now().isoformat(),
        "applicable_facility": analysis.get('drawing_type', {}).get('primary', '建筑'),
        "total_equipment": len(equipment),
        "equipment_categories": list(set(eq.get('responsible', '其他') for eq in equipment)),
        "status": "generated",
    }
