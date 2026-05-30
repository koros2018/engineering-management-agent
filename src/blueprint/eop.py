"""
eop.py - 紧急操作程序 (Emergency Operating Procedures)

应对火灾、自然灾害、设备故障等紧急情况的标准响应程序。
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


def generate_eop_document(
    analysis: Dict,
    project_name: str = "",
    facility_type: str = "建筑",
    emergency_types: List[str] = None,
) -> str:
    """
    生成紧急操作程序(EOP)文档

    Args:
        analysis: 图纸分析结果
        project_name: 项目名称
        facility_type: 设施类型
        emergency_types: 需要包含的紧急情况类型

    Returns:
        EOP文档文本
    """
    if emergency_types is None:
        emergency_types = ["火灾", "地震", "电梯困人", "停电", "水管爆裂", "燃气泄漏"]

    lines = []
    lines.append("=" * 72)
    lines.append(" " * 20 + "紧急操作程序 (EOP)")
    lines.append(" " * 18 + "Emergency Operating Procedures")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"文档编号：EOP-{datetime.now().strftime('%Y%m%d')}-001")
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
    lines.append("    为应对各类突发事件，规范紧急操作流程，")
    lines.append("    最大限度保障人员生命安全和减少财产损失。")
    lines.append("")
    lines.append("1.2 适用范围")
    lines.append(f"    适用于{facility_type}内发生的各类紧急情况的应急处置。")
    lines.append("")
    lines.append("1.3 基本原则")
    lines.append("    · 生命至上：优先保障人员生命安全")
    lines.append("    · 快速响应：发现险情立即启动应急预案")
    lines.append("    · 分级处置：根据事件级别采取相应措施")
    lines.append("    · 协同配合：各部门协调联动，统一指挥")
    lines.append("    · 信息通畅：确保通信畅通，信息传递及时准确")
    lines.append("")

    # 二、应急组织
    lines.append("二、应急组织体系")
    lines.append("-" * 60)
    lines.append("2.1 应急指挥中心")
    lines.append("    总指挥：设施经理/项目负责人")
    lines.append("    副指挥：安全主管/运行工程师")
    lines.append("    成员：各部门负责人、维保单位代表")
    lines.append("    联络方式：内部对讲机频道1 / 手机群组")
    lines.append("")
    lines.append("2.2 应急小组")
    lines.append("    · 疏散引导组：负责人员疏散和清点")
    lines.append("    · 抢险救援组：负责现场抢险和设备抢修")
    lines.append("    · 医疗救护组：负责伤员急救和转运")
    lines.append("    · 安全警戒组：负责现场警戒和交通管制")
    lines.append("    · 后勤保障组：负责物资供应和通讯保障")
    lines.append("    · 信息报送组：负责信息收集和对外联络")
    lines.append("")

    # 三、应急资源
    lines.append("三、应急资源与装备")
    lines.append("-" * 60)
    lines.append("3.1 消防设施")
    lines.append("    · 消防栓：分布于各楼层楼梯间旁")
    lines.append("    · 灭火器：每50m²至少1具，重点区域加密")
    lines.append("    · 自动喷淋：覆盖全部区域")
    lines.append("    · 防排烟系统：楼梯间/走廊正压送风")
    lines.append("")
    lines.append("3.2 疏散设施")
    lines.append("    · 疏散楼梯：封闭楼梯间，防烟前室")
    lines.append("    · 应急照明：持续供电≥90分钟")
    lines.append("    · 疏散指示：LED指示灯，蓄光型标识")
    lines.append("    · 广播系统：覆盖全部区域")
    lines.append("")
    lines.append("3.3 通讯设备")
    lines.append("    · 对讲机：各部门配备（频道1通用/频道2专用）")
    lines.append("    · 应急电话：消控室、配电室、水泵房各1部")
    lines.append("    · 手机：应急通讯录全员覆盖")
    lines.append("")

    # 四、应急响应程序
    lines.append("四、应急响应程序")
    lines.append("-" * 60)

    eop_templates = {
        "火灾": _generate_fire_emergency,
        "地震": _generate_earthquake_emergency,
        "电梯困人": _generate_elevator_emergency,
        "停电": _generate_power_outage,
        "水管爆裂": _generate_water_burst,
        "燃气泄漏": _generate_gas_leak,
        "台风": _generate_typhoon_emergency,
        "设备故障": _generate_equipment_failure,
    }

    for i, emergency in enumerate(emergency_types, 1):
        lines.append("")
        lines.append(f"4.{i} {emergency}应急处置")
        lines.append("~" * 60)

        template_fn = eop_templates.get(emergency, _generate_generic_emergency)
        content = template_fn(analysis)
        lines.extend(content)
        lines.append("")

    # 五、善后与恢复
    lines.append("")
    lines.append("五、善后处理与恢复运营")
    lines.append("-" * 60)
    lines.append("5.1 善后处理")
    lines.append("    · 清点人员，确认伤亡情况")
    lines.append("    · 保护现场，配合事故调查")
    lines.append("    · 安抚受影响人员及家属")
    lines.append("    · 评估财产损失，启动保险理赔")
    lines.append("")
    lines.append("5.2 恢复运营")
    lines.append("    · 组织设备设施全面检查")
    lines.append("    · 排除安全隐患后方可恢复使用")
    lines.append("    · 受损设备修复或更换")
    lines.append("    · 恢复运营前经安全评估合格")
    lines.append("")
    lines.append("5.3 总结改进")
    lines.append("    · 编写事故调查报告")
    lines.append("    · 召开复盘会议，总结经验教训")
    lines.append("    · 修订完善应急预案")
    lines.append("    · 组织针对性应急演练")
    lines.append("")

    # 六、培训与演练
    lines.append("六、培训与演练计划")
    lines.append("-" * 60)
    lines.append("6.1 培训要求")
    lines.append("    · 新员工入职培训：EOP基础知识（≥2小时）")
    lines.append("    · 年度复训：全员EOP复训（≥4小时）")
    lines.append("    · 专项培训：消防器材使用、急救技能（≥8小时）")
    lines.append("")
    lines.append("6.2 演练计划")
    lines.append("    · 消防疏散演练：每半年一次")
    lines.append("    · 电梯困人演练：每年一次")
    lines.append("    · 停电应急演练：每年一次")
    lines.append("    · 综合应急演练：每年一次")
    lines.append("    · 演练后评估：24小时内完成评估报告")
    lines.append("")

    # 附录
    lines.append("")
    lines.append("附录A：应急联系电话")
    lines.append("-" * 60)
    lines.append("  应急指挥中心：__________")
    lines.append("  消防中控室：__________")
    lines.append("  物业值班室：__________")
    lines.append("  电梯维保：__________")
    lines.append("  电力抢修：__________")
    lines.append("  给排水抢修：__________")
    lines.append("  燃气公司：__________")
    lines.append("  急救电话：120")
    lines.append("  火警电话：119")
    lines.append("  报警电话：110")
    lines.append("")
    lines.append("附录B：应急物资清单")
    lines.append("-" * 60)
    lines.append("  □ 应急照明灯（≥20个）")
    lines.append("  □ 手持对讲机（≥10部）")
    lines.append("  □ 急救箱（≥5套）")
    lines.append("  □ 防烟面罩（≥50个）")
    lines.append("  □ 反光背心（≥30件）")
    lines.append("  □ 警戒带（≥10卷）")
    lines.append("  □ 扩音器（≥3个）")
    lines.append("  □ 手电筒（≥20个）")
    lines.append("")
    lines.append("=" * 72)

    return "\n".join(lines)


# ── 各紧急情况模板 ────────────────────────────────────────────

def _generate_fire_emergency(analysis: Dict) -> List[str]:
    return [
        "【发现火情】",
        "  1. 发现火情立即拨打内部火警电话或119",
        "  2. 按下就近手动火灾报警按钮",
        "  3. 大声呼喊'着火了'，提醒周围人员",
        "",
        "【初期灭火】（仅限小火且安全时）",
        "  1. 使用就近灭火器扑救",
        "  2. 电器火灾使用CO2或干粉灭火器，严禁用水",
        "  3. 油锅火灾使用灭火毯覆盖",
        "  4. 若火势无法控制，立即撤离",
        "",
        "【人员疏散】",
        "  1. 听从疏散引导组指挥，有序撤离",
        "  2. 走疏散楼梯，严禁乘坐电梯",
        "  3. 弯腰低姿前行，用湿毛巾捂住口鼻",
        "  4. 到指定集合地点集合，清点人数",
        "  5. 发现有人员未撤离，立即报告",
        "",
        "【配合救援】",
        "  · 引导消防车辆进入",
        "  · 提供建筑平面图",
        "  · 说明火源位置和受困人员情况",
        "  · 切断非消防电源",
    ]


def _generate_earthquake_emergency(analysis: Dict) -> List[str]:
    return [
        "【地震发生时】",
        "  1. 如在室内：",
        "     · 立即躲避在坚固家具旁或墙角",
        "     · 远离玻璃窗、吊灯、货架",
        "     · 保护头部，蹲下或趴下",
        "  2. 如在室外：",
        "     · 远离建筑物、电线杆、广告牌",
        "     · 到空旷地带蹲下",
        "  3. 如在电梯中：",
        "     · 按下所有楼层按钮",
        "     · 电梯停稳后迅速离开",
        "",
        "【地震停止后】",
        "  1. 不要立即返回室内",
        "  2. 检查人员受伤情况，进行简单救护",
        "  3. 切断电源、燃气，防止次生灾害",
        "  4. 通过广播获取官方信息",
        "  5. 听从指挥，有序疏散或原地待命",
        "",
        "【震后检查】",
        "  · 检查建筑结构有无裂缝、变形",
        "  · 检查设备有无移位、损坏",
        "  · 检查管线有无破裂、泄漏",
        "  · 专业人员评估后方可恢复使用",
    ]


def _generate_elevator_emergency(analysis: Dict) -> List[str]:
    return [
        "【发现困人】",
        "  1. 被困人员：",
        "     · 保持冷静，不要扒门或撬门",
        "     · 按下紧急呼叫按钮或拨打应急电话",
        "     · 远离轿厢门，背靠轿厢壁等待",
        "     · 如手机有信号，拨打救援电话",
        "  2. 现场人员：",
        "     · 立即通知消控室和电梯维保单位",
        "     · 安抚被困人员情绪",
        "     · 在电梯外设置警示标识",
        "     · 严禁自行撬门救援",
        "",
        "【救援操作】",
        "  1. 电梯维保人员到场后：",
        "     · 确认轿厢位置",
        "     · 使用盘车装置或紧急开锁",
        "     · 轿厢与楼层平层后开启轿门",
        "     · 协助被困人员安全撤离",
        "  2. 医疗检查：",
        "     · 检查被困人员身体状况",
        "     · 如有不适立即送医",
        "",
        "【事后处理】",
        "  · 查明困人原因，排除故障",
        "  · 填写《电梯困人事件记录》",
        "  · 向监管部门报告（困人≥30分钟）",
        "  · 故障排除后方可恢复运行",
    ]


def _generate_power_outage(analysis: Dict) -> List[str]:
    return [
        "【停电发生】",
        "  1. 立即检查：",
        "     · 确认是局部停电还是全面停电",
        "     · 检查配电室状态，有无异响异味",
        "     · 检查应急照明是否启动",
        "  2. 启动备用电源：",
        "     · 柴油发电机自动启动（如配置）",
        "     · UPS不间断电源保障关键设备",
        "     · 检查发电机运行参数",
        "",
        "【应急处置】",
        "  1. 重要负荷保障：",
        "     · 消防系统优先供电",
        "     · 应急照明和疏散指示",
        "     · 电梯迫降（如有人员被困）",
        "     · 安防监控和门禁系统",
        "  2. 人员安全：",
        "     · 启动应急照明，确保通道可见",
        "     · 电梯迫降至最近楼层，开门放人",
        "     · 疏散重点区域人员",
        "",
        "【恢复供电】",
        "  1. 确认市电恢复",
        "  2. 按顺序恢复供电（先照明后动力）",
        "  3. 检查各系统运行状态",
        "  4. 关闭备用发电机",
        "  5. 记录停电时间和影响范围",
    ]


def _generate_water_burst(analysis: Dict) -> List[str]:
    return [
        "【发现爆管】",
        "  1. 立即关闭相应阀门：",
        "     · 给水管：关闭最近阀门",
        "     · 消防管：关闭报警阀组控制阀",
        "     · 无法确定时关闭总阀",
        "  2. 切断电源：",
        "     · 关闭受影响区域的电气开关",
        "     · 防止触电事故",
        "  3. 排水抢险：",
        "     · 启动排水泵",
        "     · 使用吸水设备清理积水",
        "     · 保护重要设备和档案",
        "",
        "【信息上报】",
        "  · 通知给排水抢修单位",
        "  · 报告物业和设施经理",
        "  · 如影响消防系统，报告消防部门",
        "  · 记录爆管位置和初步原因",
        "",
        "【修复后】",
        "  · 修复管路，进行压力试验",
        "  · 检查电气设备绝缘",
        "  · 全面清洁，消除积水",
        "  · 评估结构有无受损",
    ]


def _generate_gas_leak(analysis: Dict) -> List[str]:
    return [
        "【发现泄漏】",
        "  1. 切勿触动任何电器开关",
        "  2. 切勿使用手机或明火",
        "  3. 立即打开门窗通风",
        "  4. 关闭燃气总阀",
        "  5. 迅速撤离到室外安全区域",
        "",
        "【报警求助】",
        "  · 拨打燃气公司抢修电话",
        "  · 拨打119（如闻到浓重气味）",
        "  · 通知物业和安全部门",
        "  · 在安全区域等待救援",
        "",
        "【警戒疏散】",
        "  · 设立警戒区，禁止无关人员进入",
        "  · 疏散泄漏区域及下风方向人员",
        "  · 禁止使用明火和电器",
        "  · 禁止车辆进入",
        "",
        "【修复后】",
        "  · 专业人员检测确认无泄漏",
        "  · 检查燃气管道和设备",
        "  · 通风换气，消除残留气体",
        "  · 检测可燃气体浓度合格后恢复供气",
    ]


def _generate_typhoon_emergency(analysis: Dict) -> List[str]:
    return [
        "【台风预警】",
        "  1. 关注气象预警信息",
        "  2. 检查门窗关闭情况",
        "  3. 加固户外设施（广告牌、围挡等）",
        "  4. 清理屋顶排水口",
        "  5. 准备应急物资（手电、对讲机、急救箱）",
        "",
        "【台风期间】",
        "  1. 停止一切户外作业",
        "  2. 人员留在室内安全区域",
        "  3. 远离玻璃窗和外墙",
        "  4. 关闭非必要电源",
        "  5. 如发现漏水，及时排水",
        "",
        "【台风过后】",
        "  1. 检查建筑结构有无损坏",
        "  2. 检查设备设施运行状态",
        "  3. 清理积水和 debris",
        "  4. 修复受损设施",
        "  5. 评估后方可恢复正常运营",
    ]


def _generate_equipment_failure(analysis: Dict) -> List[str]:
    return [
        "【发现故障】",
        "  1. 立即停机，切断电源",
        "  2. 挂'故障停用'标识",
        "  3. 报告运行工程师和设施经理",
        "  4. 保护现场，保留故障状态",
        "",
        "【故障排查】",
        "  1. 初步判断故障原因",
        "  2. 查阅设备档案和维护记录",
        "  3. 联系维保单位技术支持",
        "  4. 如需更换部件，确认备件库存",
        "",
        "【修复与恢复】",
        "  1. 专业人员进行维修",
        "  2. 修复后进行功能测试",
        "  3. 确认运行参数正常",
        "  4. 填写《设备故障维修记录》",
        "  5. 故障分析，制定预防措施",
    ]


def _generate_generic_emergency(analysis: Dict) -> List[str]:
    return [
        "【发现险情】",
        "  1. 保持冷静，评估危险程度",
        "  2. 立即报告应急指挥中心",
        "  3. 启动相应级别的应急响应",
        "",
        "【人员安全】",
        "  1. 优先确保人员安全",
        "  2. 必要时组织疏散",
        "  3. 清点人数，确认无人员滞留",
        "  4. 对伤员进行急救",
        "",
        "【现场处置】",
        "  1. 控制危险源，防止事态扩大",
        "  2. 配合专业救援力量",
        "  3. 保护现场证据",
        "  4. 持续监控事态发展",
    ]


def generate_eop_summary(analysis: Dict) -> Dict[str, Any]:
    """生成EOP文档摘要信息"""
    return {
        "document_type": "EOP",
        "title": "紧急操作程序",
        "english_title": "Emergency Operating Procedures",
        "version": "v1.0",
        "generated_at": datetime.now().isoformat(),
        "applicable_facility": analysis.get('drawing_type', {}).get('primary', '建筑'),
        "total_scenarios": 6,
        "scenarios": ["火灾", "地震", "电梯困人", "停电", "水管爆裂", "燃气泄漏"],
        "status": "generated",
    }
