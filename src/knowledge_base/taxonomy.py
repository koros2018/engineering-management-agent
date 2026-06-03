"""
knowledge_base/taxonomy.py — 标准分类体系 + 核心标准清单

从第一性原理构建：
1. 三级分类：领域(domain) → 类别(category) → 专业(specialty)
2. 标准层级：GB(强制性) > GB/T(推荐性) > 行业标准 > 地标 > 团标
3. 覆盖勘察设计全专业：建筑/结构/给排水/暖通/电气/消防/市政/勘察
"""

from typing import Dict, List

from .schema import EngineeringDomain, MandatoryLevel, StandardLevel, Standard


# ═══════════════════════════════════════════════════════════════
# 分类树
# ═══════════════════════════════════════════════════════════════

DOMAIN_CATEGORIES: Dict[str, List[str]] = {
    "architecture": ["建筑设计", "建筑防火", "建筑节能", "建筑幕墙", "建筑无障碍"],
    "structure": ["结构设计", "地基基础", "抗震设计", "钢结构", "混凝土结构", "砌体结构", "木结构"],
    "fire_protection": ["消防给水", "自动灭火", "火灾报警", "防排烟", "消防电气"],
    "hvac": ["供暖通风", "空调制冷", "除尘净化", "热能动力"],
    "water_supply": ["建筑给水", "建筑排水", "热水系统", "中水回用"],
    "electrical": ["供配电", "照明", "防雷接地", "电气安全"],
    "intelligent": ["弱电系统", "楼宇自控", "安防系统", "综合布线"],
    "road": ["道路路线", "路基路面", "交通工程", "道路排水"],
    "bridge": ["桥梁结构", "桥涵水文", "桥梁抗震"],
    "tunnel": ["隧道结构", "隧道通风", "隧道照明"],
    "geotechnical": ["岩土勘察", "地基处理", "边坡工程", "基坑工程"],
    "survey": ["工程测量", "摄影测量", "地籍测绘"],
    "municipal_water": ["水源工程", "给水管网", "排水管网", "污水处理"],
    "municipal_drain": ["雨水工程", "污水工程", "防洪排涝"],
    "gas": ["燃气输配", "燃气储存", "燃气应用"],
    "heating": ["集中供热", "热力管网", "换热站"],
    "environment": ["大气环境", "水环境", "噪声控制", "固废处理"],
    "pipeline": ["工业管道", "压力管道", "管道防腐"],
    "equipment": ["通用设备", "特种设备", "起重设备"],
    "power": ["锅炉", "汽轮机", "发电机组", "热力系统"],
    "petrochem": ["石油储运", "化工工艺", "安全防护"],
    "construction_mgmt": ["施工组织", "质量验收", "进度管理", "竣工验收"],
    "cost": ["工程量清单", "计价规范", "概预算", "结算审核"],
    "quality": ["质量管理体系", "检测标准", "试验方法"],
    "safety_mgmt": ["施工安全", "职业健康", "应急预案"],
    "bim": ["BIM模型", "信息交换", "协同设计"],
    "green": ["绿色建筑", "建筑节能", "可再生能源"],
}


# ═══════════════════════════════════════════════════════════════
# 核心标准清单（扩展版：建筑/结构/消防/给排水/暖通/电气/市政/勘察）
# ═══════════════════════════════════════════════════════════════

CORE_STANDARDS: List[Standard] = [
    # ═══════════════════════════════════════════════════
    # 建筑专业
    # ═══════════════════════════════════════════════════
    Standard(id="gb50016", code="GB 50016-2014", name="建筑设计防火规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.ARCHITECTURE, EngineeringDomain.FIRE_PROTECTION],
             keywords=["防火", "疏散", "耐火等级", "防火分区", "消防车道"],
             summary="建筑防火设计的核心规范，涵盖总平面布局、防火分区、安全疏散、消防设施等强制性要求",
             current_version=2018, issuing_body="住房和城乡建设部+国家质量监督检验检疫总局"),

    Standard(id="gb50352", code="GB 50352-2019", name="民用建筑设计统一标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ARCHITECTURE],
             keywords=["民用建筑", "设计原则", "建筑模数", "无障碍"],
             current_version=2019, issuing_body="住房和城乡建设部"),

    Standard(id="gb50099", code="GB 50099-2011", name="中小学校设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ARCHITECTURE],
             keywords=["学校", "教室", "采光", "疏散"],
             current_version=2011),

    Standard(id="gb51039", code="GB 51039-2014", name="综合医院建筑设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ARCHITECTURE],
             keywords=["医院", "洁净", "医技", "病房"],
             current_version=2014),

    Standard(id="gb50038", code="GB 50038-2005", name="人民防空地下室设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.ARCHITECTURE, EngineeringDomain.STRUCTURE],
             keywords=["人防", "地下室", "防护"],
             current_version=2005),

    Standard(id="jgj100", code="JGJ 100-2015", name="车库建筑设计规范",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ARCHITECTURE],
             keywords=["车库", "停车", "坡道", "车位"],
             current_version=2015, issuing_body="住房和城乡建设部"),

    Standard(id="gb50763", code="GB 50763-2012", name="无障碍设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.ARCHITECTURE],
             keywords=["无障碍", "坡道", "电梯", "盲道"],
             current_version=2012),

    # ═══════════════════════════════════════════════════
    # 结构专业
    # ═══════════════════════════════════════════════════
    Standard(id="gb50009", code="GB 50009-2012", name="建筑结构荷载规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE],
             keywords=["荷载", "风荷载", "雪荷载", "地震作用"],
             summary="结构设计基础规范，规定各类荷载取值和组合方法",
             current_version=2012),

    Standard(id="gb50010", code="GB 50010-2010", name="混凝土结构设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE],
             keywords=["混凝土", "配筋", "裂缝", "挠度"],
             current_version=2015, issuing_body="住房和城乡建设部"),

    Standard(id="gb50011", code="GB 50011-2010", name="建筑抗震设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE],
             keywords=["抗震", "设防烈度", "场地类别", "结构体系"],
             summary="建筑抗震设计的核心规范，涵盖地震作用计算、结构抗震措施、隔震减震技术",
             current_version=2016),

    Standard(id="gb50017", code="GB 50017-2017", name="钢结构设计标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE],
             keywords=["钢结构", "焊缝", "螺栓", "稳定"],
             current_version=2017),

    Standard(id="gb50003", code="GB 50003-2011", name="砌体结构设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE],
             keywords=["砌体", "砖墙", "构造柱", "圈梁"],
             current_version=2011),

    Standard(id="gb50007", code="GB 50007-2011", name="建筑地基基础设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE, EngineeringDomain.GEOTECHNICAL],
             keywords=["地基", "基础", "承载力", "沉降"],
             current_version=2011),

    Standard(id="gb50005", code="GB 50005-2017", name="木结构设计标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE],
             keywords=["木结构", "胶合木", "连接"],
             current_version=2017),

    Standard(id="gb50135", code="GB 50135-2019", name="高耸结构设计标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE],
             keywords=["高耸", "塔桅", "烟囱", "风振"],
             current_version=2019),

    Standard(id="jgj3", code="JGJ 3-2010", name="高层建筑混凝土结构技术规程",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE],
             keywords=["高层", "剪力墙", "框筒", "侧移"],
             current_version=2010),

    Standard(id="jgj79", code="JGJ 79-2012", name="建筑地基处理技术规范",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.STRUCTURE, EngineeringDomain.GEOTECHNICAL],
             keywords=["地基处理", "桩基", "复合地基"],
             current_version=2012),

    # ═══════════════════════════════════════════════════
    # 消防专业
    # ═══════════════════════════════════════════════════
    Standard(id="gb50084", code="GB 50084-2017", name="自动喷水灭火系统设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.FIRE_PROTECTION],
             keywords=["喷淋", "灭火", "喷头", "报警阀"],
             current_version=2017),

    Standard(id="gb50116", code="GB 50116-2013", name="火灾自动报警系统设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.FIRE_PROTECTION, EngineeringDomain.INTELLIGENT],
             keywords=["报警", "探测器", "联动", "消防控制室"],
             current_version=2013),

    Standard(id="gb50974", code="GB 50974-2014", name="消防给水及消火栓系统技术规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.FIRE_PROTECTION, EngineeringDomain.WATER_SUPPLY],
             keywords=["消火栓", "消防泵", "消防水池", "稳压"],
             current_version=2014),

    Standard(id="gb51251", code="GB 51251-2017", name="建筑防烟排烟系统技术标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.FIRE_PROTECTION, EngineeringDomain.HVAC],
             keywords=["防烟", "排烟", "加压送风", "排烟量"],
             current_version=2017),

    Standard(id="gb50067", code="GB 50067-2014", name="汽车库、修车库、停车场设计防火规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.FIRE_PROTECTION, EngineeringDomain.ARCHITECTURE],
             keywords=["车库", "防火分区", "疏散"],
             current_version=2014),

    Standard(id="gb50222", code="GB 50222-2017", name="建筑内部装修设计防火规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.FIRE_PROTECTION, EngineeringDomain.ARCHITECTURE],
             keywords=["装修", "材料", "燃烧性能"],
             current_version=2017),

    # ═══════════════════════════════════════════════════
    # 给排水专业
    # ═══════════════════════════════════════════════════
    Standard(id="gb50015", code="GB 50015-2019", name="建筑给水排水设计标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.WATER_SUPPLY],
             keywords=["给水", "排水", "热水", "雨水"],
             summary="建筑给排水的核心规范，涵盖生活给水、排水、热水、雨水、中水系统设计",
             current_version=2019),

    Standard(id="gb50013", code="GB 50013-2018", name="室外给水设计标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.MUNICIPAL_WATER],
             keywords=["给水", "管网", "水厂", "泵站"],
             current_version=2018),

    Standard(id="gb50014", code="GB 50014-2021", name="室外排水设计标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.MUNICIPAL_DRAIN],
             keywords=["排水", "污水", "雨水", "管网"],
             current_version=2021),

    Standard(id="gb50268", code="GB 50268-2008", name="给水排水管道工程施工及验收规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.WATER_SUPPLY, EngineeringDomain.CONSTRUCTION_MGMT],
             keywords=["管道", "施工", "验收"],
             current_version=2008),

    # ═══════════════════════════════════════════════════
    # 暖通专业
    # ═══════════════════════════════════════════════════
    Standard(id="gb50736", code="GB 50736-2012", name="民用建筑供暖通风与空气调节设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.HVAC],
             keywords=["供暖", "通风", "空调", "冷热源"],
             summary="暖通空调核心规范，涵盖室内外设计参数、负荷计算、系统设计、节能要求",
             current_version=2012),

    Standard(id="gb50019", code="GB 50019-2015", name="工业建筑供暖通风与空气调节设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.HVAC],
             keywords=["工业", "供暖", "除尘", "通风"],
             current_version=2015),

    Standard(id="gb50189", code="GB 50189-2015", name="公共建筑节能设计标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.HVAC, EngineeringDomain.GREEN],
             keywords=["节能", "围护结构", "能效", "COP"],
             current_version=2015),

    Standard(id="gb50243", code="GB 50243-2016", name="通风与空调工程施工质量验收规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.HVAC, EngineeringDomain.CONSTRUCTION_MGMT],
             keywords=["风管", "安装", "调试"],
             current_version=2016),

    # ═══════════════════════════════════════════════════
    # 电气专业
    # ═══════════════════════════════════════════════════
    Standard(id="gb50052", code="GB 50052-2009", name="供配电系统设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.ELECTRICAL],
             keywords=["供配电", "负荷等级", "变配电所"],
             current_version=2009),

    Standard(id="gb50054", code="GB 50054-2011", name="低压配电设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.ELECTRICAL],
             keywords=["低压", "配电", "保护", "线缆"],
             current_version=2011),

    Standard(id="gb50057", code="GB 50057-2010", name="建筑物防雷设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.ELECTRICAL],
             keywords=["防雷", "接闪器", "引下线", "接地"],
             current_version=2010),

    Standard(id="gb50303", code="GB 50303-2015", name="建筑电气工程施工质量验收规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ELECTRICAL, EngineeringDomain.CONSTRUCTION_MGMT],
             keywords=["电气安装", "验收"],
             current_version=2015),

    Standard(id="gb50174", code="GB 50174-2017", name="数据中心设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ELECTRICAL, EngineeringDomain.INTELLIGENT],
             keywords=["数据中心", "空调", "供电", "等级"],
             current_version=2017),

    Standard(id="jgj16", code="JGJ 16-2008", name="民用建筑电气设计规范",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ELECTRICAL],
             keywords=["电气", "照明", "配电"],
             current_version=2008),

    # ═══════════════════════════════════════════════════
    # 市政/勘察
    # ═══════════════════════════════════════════════════
    Standard(id="gb50021", code="GB 50021-2001", name="岩土工程勘察规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.GEOTECHNICAL],
             keywords=["勘察", "钻探", "取样", "试验"],
             current_version=2009, issuing_body="住房和城乡建设部"),

    Standard(id="gb50026", code="GB 50026-2020", name="工程测量标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.SURVEY],
             keywords=["测量", "GPS", "水准", "地形图"],
             current_version=2020),

    Standard(id="cj37", code="CJJ 37-2012", name="城市道路工程设计规范",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ROAD],
             keywords=["城市道路", "横断面", "交叉口"],
             current_version=2016),

    Standard(id="jtgd20", code="JTG D20-2017", name="公路路线设计规范",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ROAD],
             keywords=["公路", "线形", "视距"],
             current_version=2017),

    Standard(id="jtgd60", code="JTG D60-2015", name="公路桥涵设计通用规范",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.BRIDGE],
             keywords=["桥涵", "荷载", "设计基准期"],
             current_version=2015),

    Standard(id="jtg3370", code="JTG 3370.1-2018", name="公路隧道设计规范 第一册 土建工程",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.TUNNEL],
             keywords=["隧道", "围岩", "衬砌"],
             current_version=2018),

    Standard(id="cjj1", code="CJJ 1-2008", name="城镇道路工程施工与质量验收规范",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.ROAD, EngineeringDomain.CONSTRUCTION_MGMT],
             keywords=["道路", "路基", "路面", "验收"],
             current_version=2008),

    # ═══════════════════════════════════════════════════
    # 施工管理/安全
    # ═══════════════════════════════════════════════════
    Standard(id="gb50300", code="GB 50300-2013", name="建筑工程施工质量验收统一标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.CONSTRUCTION_MGMT],
             keywords=["质量验收", "检验批", "分项", "分部"],
             summary="建筑工程质量验收的纲领性标准，规定检验批、分项、分部、单位工程的划分和验收程序",
             current_version=2013),

    Standard(id="jgj59", code="JGJ 59-2011", name="建筑施工安全检查标准",
             level=StandardLevel.INDUSTRY, mandatory_level=MandatoryLevel.PARTIAL_MANDATORY,
             domains=[EngineeringDomain.SAFETY_MGMT],
             keywords=["安全检查", "评分", "隐患"],
             current_version=2011),

    Standard(id="gb50870", code="GB 50870-2013", name="建筑施工安全技术统一规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.SAFETY_MGMT],
             keywords=["安全", "危险源", "防护"],
             current_version=2013),

    # ═══════════════════════════════════════════════════
    # 造价/BIM
    # ═══════════════════════════════════════════════════
    Standard(id="gb50500", code="GB 50500-2013", name="建设工程工程量清单计价规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.COST],
             keywords=["工程量清单", "计价", "综合单价"],
             summary="工程造价核心规范，规定工程量清单编制、招标控制价、投标报价、竣工结算的计价规则",
             current_version=2013),

    Standard(id="gbt51212", code="GB/T 51212-2016", name="建筑信息模型应用统一标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.RECOMMENDED,
             domains=[EngineeringDomain.BIM],
             keywords=["BIM", "模型", "信息交换", "协同"],
             current_version=2016),

    Standard(id="gbt50378", code="GB/T 50378-2019", name="绿色建筑评价标准",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.RECOMMENDED,
             domains=[EngineeringDomain.GREEN],
             keywords=["绿色建筑", "评价", "星级"],
             current_version=2019),

    # ═══════════════════════════════════════════════════
    # 燃气/压力管道/工业
    # ═══════════════════════════════════════════════════
    Standard(id="gb50028", code="GB 50028-2006", name="城镇燃气设计规范",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.FULL_MANDATORY,
             domains=[EngineeringDomain.GAS],
             keywords=["燃气", "管道", "调压", "储配"],
             current_version=2020),

    Standard(id="gb20801", code="GB/T 20801-2020", name="压力管道规范 工业管道",
             level=StandardLevel.NATIONAL, mandatory_level=MandatoryLevel.RECOMMENDED,
             domains=[EngineeringDomain.PIPELINE],
             keywords=["压力管道", "工业管道", "材料", "检验"],
             current_version=2020),
]


# ═══════════════════════════════════════════════════════════════
# 标准数量统计
# ═══════════════════════════════════════════════════════════════

CORE_STANDARD_COUNT = len(CORE_STANDARDS)
CORE_DOMAINS_COVERED = len(set(d for s in CORE_STANDARDS for d in s.domains))
CORE_MANDATORY_COUNT = len([s for s in CORE_STANDARDS if s.mandatory_level.is_mandatory])


def get_standards_by_domain(domain: EngineeringDomain) -> List[Standard]:
    return [s for s in CORE_STANDARDS if domain in s.domains]


def get_mandatory_standards() -> List[Standard]:
    return [s for s in CORE_STANDARDS if s.mandatory_level.is_mandatory]


def get_standards_by_level(level: StandardLevel) -> List[Standard]:
    return [s for s in CORE_STANDARDS if s.level == level]
