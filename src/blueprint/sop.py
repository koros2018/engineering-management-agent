"""
sop.py - 标准作业程序 (Standard Operating Procedures)

生成建筑/设施的标准操作步骤文档，确保操作一致性、安全性和效率。
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


def generate_sop_document(
    analysis: Dict,
    project_name: str = "",
    facility_type: str = "建筑",
    operations: List[str] = None,
) -> str:
    """
    生成标准作业程序(SOP)文档

    Args:
        analysis: 图纸分析结果
        project_name: 项目名称
        facility_type: 设施类型（建筑/厂房/机房等）
        operations: 需要包含的作业项目列表

    Returns:
        SOP文档文本
    """
    if operations is None:
        operations = ["日常巡检", "设备启停", "清洁维护", "安全巡查", "能源管理"]

    lines = []
    lines.append("=" * 72)
    lines.append(" " * 20 + "标准作业程序 (SOP)")
    lines.append(" " * 18 + "Standard Operating Procedures")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"文档编号：SOP-{datetime.now().strftime('%Y%m%d')}-001")
    lines.append(f"编制日期：{datetime.now().strftime('%Y年%m月%d日')}")
    lines.append(f"项目名称：{project_name or analysis.get('file_name', '未命名项目')}")
    lines.append(f"设施类型：{facility_type}")
    lines.append(f"适用对象：{analysis.get('drawing_type', {}).get('primary', '建筑')}工程")
    lines.append("")
    lines.append("编制单位：________________________")
    lines.append("审核人：________________________")
    lines.append("批准人：________________________")
    lines.append("")
    lines.append("=" * 72)
    lines.append("")

    # 一、目的与范围
    lines.append("一、目的与范围")
    lines.append("-" * 60)
    lines.append("1.1 目的")
    lines.append("    规范本设施的日常操作程序，确保操作过程安全、高效、标准化，")
    lines.append("    降低人为操作失误导致的安全事故和设备损坏风险。")
    lines.append("")
    lines.append("1.2 适用范围")
    lines.append(f"    适用于{facility_type}的日常运行、维护和管理操作。")
    lines.append("    所有操作人员必须经过培训并考核合格后，方可独立执行本SOP。")
    lines.append("")
    lines.append("1.3 引用标准")
    lines.append("    · 《建筑设计防火规范》GB 50016-2014")
    lines.append("    · 《建筑电气工程施工质量验收规范》GB 50303-2015")
    lines.append("    · 《建筑给水排水及采暖工程施工质量验收规范》GB 50242-2002")
    lines.append("    · 《智能建筑工程质量验收规范》GB 50339-2013")
    lines.append("")

    # 二、职责分工
    lines.append("二、职责分工")
    lines.append("-" * 60)
    roles = [
        ("设施经理", "全面负责设施运营管理和SOP执行监督"),
        ("运行工程师", "负责设备运行监控、参数调整和异常处理"),
        ("维护技师", "负责日常维护、巡检和故障排查"),
        ("安全员", "负责安全检查、隐患排查和应急协调"),
        ("操作人员", "按SOP执行具体操作，如实记录运行数据"),
    ]
    for role, duty in roles:
        lines.append(f"    {role}：{duty}")
    lines.append("")

    # 三、作业程序
    lines.append("三、标准作业程序")
    lines.append("-" * 60)

    sop_templates = {
        "日常巡检": _generate_daily_inspection,
        "设备启停": _generate_equipment_operation,
        "清洁维护": _generate_cleaning_maintenance,
        "安全巡查": _generate_safety_patrol,
        "能源管理": _generate_energy_management,
        "消防检查": _generate_fire_inspection,
        "电梯运行": _generate_elevator_operation,
        "空调系统": _generate_hvac_operation,
        "给排水系统": _generate_plumbing_operation,
        "电气系统": _generate_electrical_operation,
    }

    for i, op_name in enumerate(operations, 1):
        lines.append("")
        lines.append(f"3.{i} {op_name}")
        lines.append("~" * 60)

        template_fn = sop_templates.get(op_name, _generate_generic_operation)
        content = template_fn(analysis)
        lines.extend(content)
        lines.append("")

    # 四、记录与归档
    lines.append("")
    lines.append("四、记录与归档")
    lines.append("-" * 60)
    lines.append("4.1 运行记录")
    lines.append("    每次操作完成后，操作人员须填写《运行记录表》，包括：")
    lines.append("    · 操作时间、操作人员签名")
    lines.append("    · 操作内容简述")
    lines.append("    · 设备运行参数（温度/压力/电流等）")
    lines.append("    · 异常情况描述及处理措施")
    lines.append("    · 交接班注意事项")
    lines.append("")
    lines.append("4.2 归档要求")
    lines.append("    · 运行记录保存期限：不少于2年")
    lines.append("    · 重大故障记录永久保存")
    lines.append("    · 电子记录每日备份，纸质记录按月归档")
    lines.append("")

    # 五、修订历史
    lines.append("")
    lines.append("五、修订历史")
    lines.append("-" * 60)
    lines.append(f"  版本  日期          修订内容          修订人")
    lines.append(f"  v1.0  {datetime.now().strftime('%Y-%m-%d')}    初始发布          __________")
    lines.append("")

    # 附录
    lines.append("")
    lines.append("附录A：应急联系电话")
    lines.append("-" * 60)
    lines.append("  设施经理：__________    运行工程师：__________")
    lines.append("  维护技师：__________    安全员：__________")
    lines.append("  消防中控：__________    物业值班：__________")
    lines.append("  急救电话：120          火警电话：119")
    lines.append("")
    lines.append("=" * 72)

    return "\n".join(lines)


# ── 各作业程序模板 ────────────────────────────────────────────

def _generate_daily_inspection(analysis: Dict) -> List[str]:
    return [
        "【作业前准备】",
        "  1. 穿戴劳动防护用品（安全帽、工作服、绝缘鞋）",
        "  2. 携带巡检工具包（测温枪、照度计、万用表、手电筒）",
        "  3. 确认巡检路线和检查清单",
        "",
        "【作业步骤】",
        "  1. 外观检查",
        "     · 建筑外立面：检查裂缝、渗漏、脱落",
        "     · 屋面：检查防水层、排水口、避雷带",
        "     · 门窗：检查启闭灵活、密封完好",
        "",
        "  2. 设备间巡检",
        "     · 配电室：电压/电流正常，无异味异响",
        "     · 水泵房：水压稳定，无跑冒滴漏",
        "     · 空调机房：运行参数正常，过滤网清洁",
        "",
        "  3. 公共区域检查",
        "     · 走廊/楼梯：照明完好，疏散标识清晰",
        "     · 电梯：运行平稳，紧急呼叫有效",
        "     · 消防器材：压力正常，在有效期内",
        "",
        "【作业后确认】",
        "  · 填写巡检记录，异常情况立即上报",
        "  · 将巡检工具归位",
        "  · 向接班人员交接注意事项",
    ]


def _generate_equipment_operation(analysis: Dict) -> List[str]:
    return [
        "【作业前准备】",
        "  1. 确认设备状态正常，无检修标识",
        "  2. 检查安全防护装置完好",
        "  3. 熟悉设备操作规程和紧急停机按钮位置",
        "",
        "【启动步骤】",
        "  1. 按顺序闭合电源开关（总闸→分闸→设备）",
        "  2. 观察设备启动过程，确认无异常声响",
        "  3. 检查运行参数（电压、电流、转速、温度）",
        "  4. 设备运行稳定后，记录启动时间",
        "",
        "【运行监控】",
        "  · 每2小时记录一次运行参数",
        "  · 监听设备运行声音，发现异响立即检查",
        "  · 注意温升变化，超过阈值立即停机",
        "",
        "【停机步骤】",
        "  1. 按规程逐步降低负载",
        "  2. 按下停机按钮，观察停机过程",
        "  3. 切断电源，挂'已停机'标识",
        "  4. 填写运行记录",
    ]


def _generate_cleaning_maintenance(analysis: Dict) -> List[str]:
    return [
        "【作业前准备】",
        "  1. 确认清洁区域无带电危险",
        "  2. 准备清洁工具和用品",
        "  3. 设置警示标识，防止人员误入",
        "",
        "【日常清洁】",
        "  1. 地面清洁：每日清扫，每周拖洗",
        "  2. 设备表面：每周擦拭，保持无积尘",
        "  3. 通风口/过滤网：每月清洗，保持畅通",
        "  4. 玻璃/镜面：每周清洁，保持通透",
        "",
        "【定期维护】",
        "  · 每月：检查并紧固松动的螺栓",
        "  · 每季度：润滑活动部件",
        "  · 每半年：检查密封件，更换老化件",
        "  · 每年：全面检修，出具维护报告",
    ]


def _generate_safety_patrol(analysis: Dict) -> List[str]:
    return [
        "【作业前准备】",
        "  1. 穿戴反光背心，携带对讲机",
        "  2. 准备检查清单和记录表",
        "  3. 确认紧急联系渠道畅通",
        "",
        "【巡查内容】",
        "  1. 消防安全",
        "     · 消防栓/灭火器：在位、完好、未过期",
        "     · 疏散通道：畅通、无杂物堆放",
        "     · 应急照明：功能正常",
        "     · 防火门：闭门器完好，常闭状态",
        "",
        "  2. 电气安全",
        "     · 配电箱：门锁完好，标识清晰",
        "     · 电缆线路：无裸露、无过热",
        "     · 临时用电：合规，有保护措施",
        "",
        "  3. 结构安全",
        "     · 墙体/楼板：无新增裂缝",
        "     · 栏杆/扶手：牢固可靠",
        "     · 地面：无破损、无积水",
    ]


def _generate_energy_management(analysis: Dict) -> List[str]:
    return [
        "【管理目标】",
        "  · 年综合能耗同比下降≥5%",
        "  · 单位面积能耗控制在行业标准以内",
        "  · 可再生能源使用比例≥10%",
        "",
        "【日常管理】",
        "  1. 抄表记录",
        "     · 每日记录电/水/气/热用量",
        "     · 对比历史数据，发现异常及时排查",
        "",
        "  2. 用能优化",
        "     · 空调：夏季26℃/冬季20℃，定时启停",
        "     · 照明：充分利用自然光，人走灯灭",
        "     · 电梯：低峰期减少运行台数",
        "     · 供水：定期检查管网，杜绝跑冒滴漏",
        "",
        "  3. 节能改造",
        "     · LED照明替换（每年完成20%）",
        "     · 变频技术应用（水泵/风机）",
        "     · 智能控制系统升级",
    ]


def _generate_fire_inspection(analysis: Dict) -> List[str]:
    return [
        "【检查频次】",
        "  · 日常巡查：每日一次",
        "  · 月度检查：每月一次",
        "  · 年度检测：每年委托专业机构检测",
        "",
        "【检查内容】",
        "  1. 火灾自动报警系统",
        "     · 探测器外观清洁，无遮挡",
        "     · 手动报警按钮完好",
        "     · 声光报警器功能正常",
        "",
        "  2. 自动灭火系统",
        "     · 喷头外观完好，无遮挡",
        "     · 管网压力正常",
        "     · 水泵启动功能正常",
        "",
        "  3. 消防给水系统",
        "     · 消防水池/水箱水位正常",
        "     · 消防水泵能正常启动",
        "     · 消火栓出水压力符合要求",
    ]


def _generate_elevator_operation(analysis: Dict) -> List[str]:
    return [
        "【日常操作】",
        "  1. 开梯前检查",
        "     · 确认轿厢内照明/通风正常",
        "     · 检查按钮面板功能完好",
        "     · 确认对讲系统有效",
        "",
        "  2. 运行监控",
        "     · 监听运行有无异响",
        "     · 观察平层精度",
        "     · 记录每日运行次数",
        "",
        "  3. 关梯操作",
        "     · 确认轿厢内无人",
        "     · 关闭照明，锁梯",
        "     · 记录当日运行状况",
        "",
        "【应急处理】",
        "  · 困人：安抚乘客，立即通知维保单位",
        "  · 故障：停用电梯，挂故障标识",
        "  · 维保记录：保存至少4年",
    ]


def _generate_hvac_operation(analysis: Dict) -> List[str]:
    return [
        "【启动前检查】",
        "  1. 检查冷却水/冷冻水系统压力",
        "  2. 确认过滤器清洁",
        "  3. 检查皮带张紧度",
        "  4. 确认阀门开关状态正确",
        "",
        "【运行参数】",
        "  · 夏季：冷冻水出水7-9℃，回水12-14℃",
        "  · 冬季：热水出水45-55℃，回水40-50℃",
        "  · 新风量：人均≥30m³/h",
        "  · 室内CO₂浓度：≤1000ppm",
        "",
        "【换季保养】",
        "  · 春季：清洗冷却塔，检查风机",
        "  · 秋季：清洗换热器，检查管路保温",
        "  · 全年：每月清洗过滤网",
    ]


def _generate_plumbing_operation(analysis: Dict) -> List[str]:
    return [
        "【日常巡检】",
        "  1. 水泵房",
        "     · 水泵运行声音正常，无振动",
        "     · 水池水位正常，水质清澈",
        "     · 压力表读数在正常范围",
        "",
        "  2. 排水系统",
        "     · 排水通畅，无堵塞",
        "     · 检查井无积水",
        "     · 化粪池定期清掏",
        "",
        "  3. 给水管网",
        "     · 水压稳定，满足使用要求",
        "     · 无跑冒滴漏",
        "     · 阀门启闭灵活",
        "",
        "【应急处理】",
        "  · 爆管：立即关闭总阀，组织抢修",
        "  · 堵塞：疏通管道，查明原因",
        "  · 污染：停止供水，取样检测",
    ]


def _generate_electrical_operation(analysis: Dict) -> List[str]:
    return [
        "【日常巡检】",
        "  1. 配电室",
        "     · 温度≤40℃，湿度≤80%",
        "     · 仪表读数正常",
        "     · 无异味、异响",
        "",
        "  2. 变压器",
        "     · 油位正常，无渗漏",
        "     · 绕组温度≤105℃",
        "     · 冷却系统运行正常",
        "",
        "  3. 应急电源",
        "     · 蓄电池电压正常",
        "     · 每月放电测试一次",
        "     · 每年全面维护一次",
        "",
        "【安全规定】",
        "  · 高压操作须两人以上执行",
        "  · 操作前验电，挂接地线",
        "  · 严禁带负荷拉闸",
    ]


def _generate_generic_operation(analysis: Dict) -> List[str]:
    return [
        "【作业前准备】",
        "  1. 确认作业环境和条件符合要求",
        "  2. 准备必要的工具和设备",
        "  3. 阅读相关技术文件和安全规程",
        "",
        "【作业步骤】",
        "  1. 按标准流程逐步执行",
        "  2. 每步完成后自查确认",
        "  3. 发现异常立即停止，报告上级",
        "",
        "【作业后确认】",
        "  · 清理现场，工具归位",
        "  · 填写作业记录",
        "  · 交接班时说明完成情况",
    ]


def generate_sop_summary(analysis: Dict) -> Dict[str, Any]:
    """生成SOP文档摘要信息（用于前端展示）"""
    return {
        "document_type": "SOP",
        "title": "标准作业程序",
        "english_title": "Standard Operating Procedures",
        "version": "v1.0",
        "generated_at": datetime.now().isoformat(),
        "applicable_facility": analysis.get('drawing_type', {}).get('primary', '建筑'),
        "total_procedures": 5,
        "procedures": ["日常巡检", "设备启停", "清洁维护", "安全巡查", "能源管理"],
        "status": "generated",
    }
