"""EMA自研规范映射库 - 从blueprint-ai/spec_mapper.py迁移 (Phase 7+1-C, 2026-05-28)"""

from typing import Dict, List, Any, Optional
try:
    from ..ai.inference import LAYER_PREFIX_CATEGORY
except ImportError:
    from inference import LAYER_PREFIX_CATEGORY  # type: ignore


# 图层/块名 → 规范条目映射
LAYER_TO_SPECS = {
    # 防火疏散
    'FIRE': [
        {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '7.4 疏散楼梯', 'requirement': '疏散楼梯净宽≥1.1m'},
        {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '5.5 疏散出口', 'requirement': '疏散距离满足要求'},
    ],
    'EXIT': [
        {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '6.4 安全出口', 'requirement': '安全出口数量≥2个'},
    ],
    'STAIR': [
        {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '6.4 疏散楼梯', 'requirement': '楼梯间耐火极限≥1h'},
        {'code': 'JGJ 67-2019', 'name': '办公建筑设计规范', 'section': '4.4 楼梯', 'requirement': '楼梯踏步高宽比≤1:2'},
    ],
    'SMOKE': [
        {'code': 'GB 50016-2014', 'name': '建筑设计防火规范', 'section': '8.5 防烟排烟', 'requirement': '防烟楼梯间设置机械加压送风'},
    ],

    # 结构设计
    'COLUMN': [
        {'code': 'GB 50010-2010', 'name': '混凝土结构设计规范', 'section': '6.3 受压构件', 'requirement': '轴压比限值满足抗震要求'},
        {'code': 'GB 50011-2010', 'name': '建筑抗震设计规范', 'section': '3.9 结构材料', 'requirement': '混凝土强度等级≥C30'},
    ],
    'BEAM': [
        {'code': 'GB 50010-2010', 'name': '混凝土结构设计规范', 'section': '6.2 受弯构件', 'requirement': '正截面承载力计算'},
    ],
    'SLAB': [
        {'code': 'GB 50010-2010', 'name': '混凝土结构设计规范', 'section': '9.1 板', 'requirement': '双向板最小厚度≥80mm'},
    ],
    'FOUNDATION': [
        {'code': 'GB 50007-2011', 'name': '建筑地基基础设计规范', 'section': '8.2 基础设计', 'requirement': '地基承载力特征值确定'},
    ],
    'REBAR': [
        {'code': 'GB 50010-2010', 'name': '混凝土结构设计规范', 'section': '8.4 钢筋连接', 'requirement': '钢筋锚固长度≥lae'},
    ],

    # 建筑防水
    'WATERPROOF': [
        {'code': 'GB 50108-2008', 'name': '地下工程防水技术规范', 'section': '4.3 防水混凝土', 'requirement': '抗渗等级≥P6'},
    ],
    'ROOF': [
        {'code': 'GB 50693-2011', 'name': '屋面工程技术规范', 'section': '3.0 屋面工程', 'requirement': '防水等级≥Ⅰ级'},
    ],

    # 建筑节能
    'INSULATION': [
        {'code': 'JGJ 26-2018', 'name': '严寒和寒冷地区居住建筑节能设计标准', 'section': '5.2 围护结构', 'requirement': '外墙传热系数≤0.60'},
    ],
    'WINDOW': [
        {'code': 'JGJ 151-2008', 'name': '建筑门窗洞口和外墙节能标准', 'section': '4.1 门窗', 'requirement': '气密性≥6级'},
    ],

    # 机电安装
    'HVAC': [
        {'code': 'GB 50736-2012', 'name': '民用建筑供暖通风与空气调节设计规范', 'section': '5.6 风管设计', 'requirement': '风管风速≤8m/s'},
    ],
    'DUCT': [
        {'code': 'GB 50243-2016', 'name': '通风与空调工程施工质量验收规范', 'section': '6.0 风管制作', 'requirement': '风管板材厚度按风压选择'},
    ],
    'ELECTRICAL': [
        {'code': 'GB 50052-2009', 'name': '供配电系统设计规范', 'section': '5.0 低压配电', 'requirement': '低压配电半径≤200m'},
    ],
    'POWER': [
        {'code': 'GB 50054-2011', 'name': '低压配电设计规范', 'section': '3.2 配电设备', 'requirement': '配电柜距地1.4-1.8m'},
    ],
    'LIGHTING': [
        {'code': 'GB 50034-2013', 'name': '建筑照明设计标准', 'section': '6.1 照度标准', 'requirement': '办公室照度≥300lx'},
    ],
    'PLUMBING': [
        {'code': 'GB 50015-2019', 'name': '建筑给水排水设计规范', 'section': '3.5 管道', 'requirement': '给水管流速≤2.0m/s'},
    ],
    'PIPE': [
        {'code': 'GB 50242-2002', 'name': '建筑给水排水及采暖工程施工质量验收规范', 'section': '4.0 管道安装', 'requirement': '管道坡度符合设计要求'},
    ],
    'FIRE_SPRINKLER': [
        {'code': 'GB 50084-2017', 'name': '自动喷水灭火系统设计规范', 'section': '8.0 喷头布置', 'requirement': '喷头间距≤3.6m'},
    ],

    # 无障碍设计
    'ACCESSIBLE': [
        {'code': 'GB 50763-2012', 'name': '无障碍设计规范', 'section': '3.8 楼梯', 'requirement': '扶手直径30-40mm'},
    ],
    'ELEVATOR': [
        {'code': 'GB 50368-2005', 'name': '住宅建筑规范', 'section': '6.4 电梯', 'requirement': '电梯候梯厅深度≥1.5m'},
    ],

    # 装饰装修
    'CEILING': [
        {'code': 'GB 50222-2017', 'name': '建筑内部装修设计防火规范', 'section': '3.0 装修材料', 'requirement': '顶棚装修材料燃烧性能A级'},
    ],
    'PARTITION': [
        {'code': 'GB 50222-2017', 'name': '建筑内部装修设计防火规范', 'section': '3.0 装修材料', 'requirement': '隔断装修材料燃烧性能≥B1级'},
    ],

    # 地基基础
    'PILE': [
        {'code': 'JGJ 94-2008', 'name': '建筑桩基技术规范', 'section': '6.2 混凝土灌注桩', 'requirement': '桩身混凝土强度≥C25'},
        {'code': 'GB 50007-2011', 'name': '建筑地基基础设计规范', 'section': '8.5 桩基础', 'requirement': '单桩承载力特征值确定'},
    ],
    'RETAINING': [
        {'code': 'GB 50330-2013', 'name': '建筑边坡工程技术规范', 'section': '12.0 挡墙', 'requirement': '挡土墙抗倾覆安全系数≥1.5'},
    ],

    # 机电/气态介质
    'GAS': [
        {'code': 'GB 50028-2006', 'name': '城镇燃气设计规范', 'section': '6.4 室内燃气管道', 'requirement': '燃气管道工作压力≤0.4MPa'},
        {'code': 'GB 50156-2012', 'name': '汽车加油加气站设计与施工规范', 'section': '3.0 设计与施工', 'requirement': '燃气管道与建筑安全间距≥10m'},
    ],
    'MEDICAL_GAS': [
        {'code': 'GB 50751-2012', 'name': '医用气体工程技术规范', 'section': '4.1 医用氧气', 'requirement': '医用气体管道材质为紫铜或无缝钢管'},
    ],
    'BMS': [
        {'code': 'GB 50339-2013', 'name': '智能建筑工程施工规范', 'section': '5.0 建筑设备监控系统', 'requirement': 'BAS系统控制点位数精度≥0.5%'},
    ],

    # 结构荷载/抗震
    'SEISMIC': [
        {'code': 'GB 50011-2010', 'name': '建筑抗震设计规范', 'section': '3.1 地震作用', 'requirement': '抗震设防烈度按当地标准确定'},
        {'code': 'GB 50011-2010', 'name': '建筑抗震设计规范', 'section': '3.2 抗震验算', 'requirement': '结构弹性位移角限值△u/h≤1/550'},
    ],
    'WIND': [
        {'code': 'GB 50009-2012', 'name': '建筑结构荷载规范', 'section': '8.1 基本风压', 'requirement': '基本风压按50年重现期取值'},
    ],
    'SNOW': [
        {'code': 'GB 50009-2012', 'name': '建筑结构荷载规范', 'section': '6.1 雪荷载', 'requirement': '屋面雪荷载按100年重现期取值'},
    ],

    # 工业管道
    'INDUSTRIAL_PIPE': [
        {'code': 'GB 50235-2010', 'name': '工业金属管道工程施工规范', 'section': '5.0 管道加工', 'requirement': '管道切割后应清除毛刺，切口端面倾斜偏差≤管外径1%'},
        {'code': 'GB 50235-2010', 'name': '工业金属管道工程施工规范', 'section': '8.0 管道安装', 'requirement': '管道对焊内壁错边量≤壁厚10%且≤1mm'},
        {'code': 'GB/T 20801.1-2020', 'name': '压力管道规范 工业管道', 'section': '总则', 'requirement': '压力管道分为GC1/GC2/GC3三个等级'},
    ],
    'PRESSURE_PIPE': [
        {'code': 'GB/T 20801.2-2020', 'name': '压力管道规范 工业管道 材料', 'section': '材料选用', 'requirement': '碳钢使用温度下限-20℃'},
        {'code': 'GB/T 20801.3-2020', 'name': '压力管道规范 工业管道 设计和计算', 'section': '设计参数', 'requirement': '设计压力≥最高工作压力'},
        {'code': 'GB/T 20801.4-2020', 'name': '压力管道规范 工业管道 制作与安装', 'section': '焊接', 'requirement': '焊接工艺评定覆盖所有焊接方法'},
        {'code': 'GB/T 20801.5-2020', 'name': '压力管道规范 工业管道 检验与试验', 'section': '压力试验', 'requirement': '强度试验压力=1.5倍设计压力'},
        {'code': 'TSG D0001-2009', 'name': '压力管道安全技术监察规程', 'section': '总则', 'requirement': '压力管道设计需取得相应资质'},
    ],
    'PIPE_WELD': [
        {'code': 'GB 50236-2011', 'name': '现场设备、工业管道焊接工程施工质量验收规范', 'section': '焊接', 'requirement': '焊接接头射线检测比例按设计文件执行'},
        {'code': 'DL/T 869-2021', 'name': '火力发电厂焊接技术规程', 'section': '焊接工艺', 'requirement': '焊工须持有相应项目的资格证书'},
    ],
    'PIPE_SUPPORT': [
        {'code': '03S402', 'name': '室内管道支架及吊架', 'section': '支架选型', 'requirement': '管道支架间距按管径和介质确定'},
        {'code': 'GD2016', 'name': '火力发电厂汽水管道零件及部件典型设计', 'section': '支吊架', 'requirement': '支吊架设计应考虑管道热位移'},
    ],

    # 锅炉
    'BOILER': [
        {'code': 'DL/T 5190.2-2019', 'name': '电力建设施工技术规范 第2部分：锅炉机组', 'section': '锅炉安装', 'requirement': '锅炉钢架安装垂直度偏差≤高度的1/1000'},
        {'code': 'DL/T 5190.5-2019', 'name': '电力建设施工技术规范 第5部分：管道及系统', 'section': '汽水管道', 'requirement': '主蒸汽管道焊接须100%射线检测'},
        {'code': 'DL/T 794-2012', 'name': '火力发电厂锅炉化学清洗导则', 'section': '清洗', 'requirement': '新建锅炉投运前须进行化学清洗'},
        {'code': 'DL/T 819-2019', 'name': '火力发电厂焊接热处理技术规程', 'section': '热处理', 'requirement': '壁厚≥19mm的碳钢管焊后须热处理'},
        {'code': 'GB 12145-2016', 'name': '火力发电机组及蒸汽动力设备水汽质量标准', 'section': '水汽质量', 'requirement': '给水溶解氧≤7μg/L'},
        {'code': 'NB/T 47043-2014', 'name': '锅炉钢结构制造技术规范', 'section': '钢结构', 'requirement': '焊接H型钢翼缘板倾斜≤2mm'},
        {'code': 'DL/T 612-2017', 'name': '电力行业锅炉压力容器安全监督规程', 'section': '安全监督', 'requirement': '锅炉压力容器须进行定期检验'},
    ],
    'BOILER_WELD': [
        {'code': 'GB 50661-2011', 'name': '钢结构焊接规范', 'section': '焊接工艺', 'requirement': '锅炉钢结构焊缝质量等级不低于二级'},
        {'code': 'DL/T 868-2014', 'name': '焊接工艺评定规程', 'section': '评定', 'requirement': '焊接工艺评定须覆盖实际生产条件'},
        {'code': 'JB/T 4730.2', 'name': '承压设备无损检测 射线检测', 'section': '检测', 'requirement': '锅炉焊缝射线检测按NB/T 47013执行'},
        {'code': 'NB/T 47014-2011', 'name': '承压设备用焊接工艺评定', 'section': '评定', 'requirement': '焊接工艺评定报告须审批后生效'},
    ],
    'BOILER_STEEL': [
        {'code': 'NB/T 47043-2014', 'name': '锅炉钢结构制造技术规范', 'section': '制造', 'requirement': '钢架立柱弯曲≤长度的1/1000'},
    ],

    # 设备安装
    'EQUIPMENT_INSTALL': [
        {'code': 'GB 50231-2009', 'name': '机械设备安装工程施工及验收通用规范', 'section': '设备基础', 'requirement': '设备基础混凝土强度≥设计强度的75%'},
        {'code': 'GB 50231-2009', 'name': '机械设备安装工程施工及验收通用规范', 'section': '找平', 'requirement': '设备纵向/横向水平度偏差≤0.1/1000'},
        {'code': 'GB 50270-2010', 'name': '输送设备安装工程施工及验收规范', 'section': '安装', 'requirement': '输送带跑偏量≤带宽5%'},
        {'code': 'GB 50275-2010', 'name': '风机、压缩机、泵安装工程施工及验收规范', 'section': '泵安装', 'requirement': '泵轴与电机轴同心度偏差≤0.05mm'},
        {'code': 'GB 50276-2010', 'name': '破碎粉磨设备安装工程施工及验收规范', 'section': '安装', 'requirement': '磨机筒体轴线倾斜度≤1mm/m'},
        {'code': 'GB 50278-2010', 'name': '起重设备安装工程施工及验收规范', 'section': '安装', 'requirement': '起重机轨道跨距偏差≤±5mm'},
        {'code': 'GB 50256-2014', 'name': '电气装置安装工程 起重机电气装置施工及验收规范', 'section': '电气', 'requirement': '起重机接地电阻≤4Ω'},
        {'code': 'GB 50390-2017', 'name': '焦化机械设备安装验收规范', 'section': '安装', 'requirement': '焦炉炉体标高偏差≤±3mm'},
        {'code': 'GB 50397-2007', 'name': '冶金电气设备工程安装验收规范', 'section': '安装', 'requirement': '电气设备安装前须进行绝缘测试'},
        {'code': 'GB 50566-2010', 'name': '冶金除尘设备工程安装与质量验收规范', 'section': '安装', 'requirement': '除尘器漏风率≤5%'},
    ],
    'CRANE': [
        {'code': 'GB 50256-2014', 'name': '电气装置安装工程 起重机电气装置施工及验收规范', 'section': '电气', 'requirement': '起重机滑触线中心线与轨道偏差≤±10mm'},
        {'code': 'GB 50278-2010', 'name': '起重设备安装工程施工及验收规范', 'section': '试验', 'requirement': '起重机须进行静载和动载试验'},
    ],
    'PUMP': [
        {'code': 'GB 50275-2010', 'name': '风机、压缩机、泵安装工程施工及验收规范', 'section': '泵', 'requirement': '泵试运转轴承温升≤40℃'},
    ],
    'FAN': [
        {'code': 'GB 50275-2010', 'name': '风机、压缩机、泵安装工程施工及验收规范', 'section': '风机', 'requirement': '风机轴承振动速度≤6.3mm/s'},
    ],
    'CONVEYOR': [
        {'code': 'GB 50270-2010', 'name': '输送设备安装工程施工及验收规范', 'section': '输送设备', 'requirement': '输送带接头强度≥带体强度的85%'},
    ],
    'MILL': [
        {'code': 'GB 50276-2010', 'name': '破碎粉磨设备安装工程施工及验收规范', 'section': '粉磨', 'requirement': '磨机主轴承温度≤60℃'},
    ],
    'COKING': [
        {'code': 'GB 50390-2017', 'name': '焦化机械设备安装验收规范', 'section': '焦炉', 'requirement': '焦炉炉墙垂直度≤高度的1/1000'},
    ],
    'METALLURGY': [
        {'code': 'GB 50397-2007', 'name': '冶金电气设备工程安装验收规范', 'section': '电气设备', 'requirement': '高压电气设备交接试验按GB 50150执行'},
        {'code': 'GB 50566-2010', 'name': '冶金除尘设备工程安装与质量验收规范', 'section': '除尘', 'requirement': '除尘效率≥设计值的99%'},
    ],
    'ELECTRICAL_EQUIP': [
        {'code': 'GB 50170-2018', 'name': '电气装置安装工程 旋转电机施工及验收标准', 'section': '电机', 'requirement': '电机绝缘电阻≥0.5MΩ'},
        {'code': 'GB 50397-2007', 'name': '冶金电气设备工程安装验收规范', 'section': '安装', 'requirement': '变压器就位后须进行吊芯检查'},
    ],

    # 防腐保温
    'ANTICORROSION': [
        {'code': 'GB 50126-2008', 'name': '工业设备及管道绝热工程施工规范', 'section': '绝热层', 'requirement': '绝热层厚度按设计值，负偏差≤5mm'},
        {'code': 'GB 50185-2010', 'name': '工业设备及管道绝热工程施工质量验收规范', 'section': '验收', 'requirement': '绝热层表面温度：环境温度≤25℃时，表面温度≤30℃'},
    ],
    'INSULATION_PIPE': [
        {'code': 'GB 50126-2008', 'name': '工业设备及管道绝热工程施工规范', 'section': '管道绝热', 'requirement': '管道绝热层接缝须错开，搭接长度≥100mm'},
        {'code': 'GB 50185-2010', 'name': '工业设备及管道绝热工程施工质量验收规范', 'section': '验收', 'requirement': '防潮层搭接宽度≥50mm'},
    ],
    'INSULATION_EQUIP': [
        {'code': 'GB 50126-2008', 'name': '工业设备及管道绝热工程施工规范', 'section': '设备绝热', 'requirement': '设备绝热层应分层施工，每层厚度≤80mm'},
    ],
    'REFRACTORY': [
        {'code': 'GB 50211-2004', 'name': '工业炉砌筑工程施工及验收规范', 'section': '砌筑', 'requirement': '耐火砖砌筑灰缝≤3mm'},
    ],

    # 零部件/支吊架
    'PIPE_SUPPORT': [
        {'code': '03S402', 'name': '室内管道支架及吊架', 'section': '支架', 'requirement': '支架材料Q235B，焊接E4303焊条'},
        {'code': 'GD2016', 'name': '火力发电厂汽水管道零件及部件典型设计', 'section': '支吊架', 'requirement': '支吊架间距按管道自重和刚度确定'},
    ],
    'PIPE_COMPONENT': [
        {'code': 'GD2016', 'name': '火力发电厂汽水管道零件及部件典型设计', 'section': '零部件', 'requirement': '管道三通、弯头等须按典型设计选用'},
        {'code': 'HG/T 20592-2009', 'name': '钢制管法兰(PN系列)', 'section': '法兰', 'requirement': '法兰密封面形式按介质和压力等级确定'},
    ],
    'FLANGE': [
        {'code': 'HG/T 20592-2009', 'name': '钢制管法兰(PN系列)', 'section': '法兰', 'requirement': '法兰螺栓拧紧力矩按规范执行'},
    ],

    # 特种设备
    'SPECIAL_EQUIP': [
        {'code': 'TSG D0001-2009', 'name': '压力管道安全技术监察规程', 'section': '总则', 'requirement': '压力管道元件须取得特种设备制造许可证'},
        {'code': 'TSG D7006-2020', 'name': '压力管道监督检验规则', 'section': '检验', 'requirement': '压力管道安装过程须进行监督检验'},
    ],

    # 动力管道
    'POWER_PIPE': [
        {'code': 'GB/T 32270-2015', 'name': '动力管道', 'section': '设计', 'requirement': '动力管道设计压力≥工作压力'},
    ],

    # 特种设备目录
    'SPECIAL_CATALOG': [
        {'code': '国务院令第549号', 'name': '特种设备安全监察条例', 'section': '锅炉', 'requirement': '锅炉设计、制造、安装须取得许可证'},
    ],

    # 电力建设
    'POWER_CONSTRUCTION': [
        {'code': 'DL/T 5190.2-2019', 'name': '电力建设施工技术规范 锅炉机组', 'section': '锅炉', 'requirement': '锅炉水压试验压力=1.25倍工作压力'},
        {'code': 'DL/T 5190.4-2019', 'name': '电力建设施工技术规范 热工仪表及控制装置', 'section': '仪表', 'requirement': '热工仪表精度等级≥1.0级'},
        {'code': 'DL/T 5190.5-2019', 'name': '电力建设施工技术规范 管道及系统', 'section': '管道', 'requirement': '主蒸汽管道吹扫靶板冲击痕≤0.8mm'},
    ],

    # 施工组织
    'CONSTRUCTION_ORG': [
        {'code': 'GB/T 50502-2009', 'name': '建筑工程施工组织设计规范', 'section': '编制', 'requirement': '施工组织设计须经审批后实施'},
    ],

    # 混凝土结构施工
    'CONCRETE_WORK': [
        {'code': 'GB 50204-2015', 'name': '混凝土结构工程施工质量验收规范', 'section': '钢筋', 'requirement': '钢筋保护层厚度偏差：梁±5mm，板±3mm'},
        {'code': 'GB 50204-2015', 'name': '混凝土结构工程施工质量验收规范', 'section': '混凝土', 'requirement': '混凝土强度等级须符合设计要求'},
    ],

    # 电气装置安装
    'ELEC_INSTALL': [
        {'code': 'GB 50303-2015', 'name': '建筑电气工程施工质量验收规范', 'section': '配电', 'requirement': '配电箱安装垂直度偏差≤1.5‰'},
        {'code': 'GB 50170-2018', 'name': '电气装置安装工程 旋转电机施工及验收标准', 'section': '电机', 'requirement': '电机试运转2h，轴承温度≤80℃'},
    ],

    # 建筑电气
    'BUILDING_ELEC': [
        {'code': 'GB 50303-2015', 'name': '建筑电气工程施工质量验收规范', 'section': '线路', 'requirement': '导线绝缘电阻≥0.5MΩ'},
    ],

    # 消防系统
    'HYDRANT': [
        {'code': 'GB 50974-2014', 'name': '消防给水及消火栓系统技术规范', 'section': '7.4 室内消火栓', 'requirement': '室内消火栓充实水柱≥10m'},
    ],
    'FOAM': [
        {'code': 'GB 50151-2010', 'name': '泡沫灭火系统设计规范', 'section': '3.0 泡沫液', 'requirement': '储罐区泡沫混合液流量≥24L/s'},
    ],
    'GAS_EXTINGUISH': [
        {'code': 'GB 29376-2012', 'name': '气体灭火系统设计规范', 'section': '3.0 七氟丙烷', 'requirement': 'IG541混合气体设计浓度≥37.5%'},
    ],

    # 绿色建筑/BIM
    'GREEN': [
        {'code': 'GB/T 50378-2019', 'name': '绿色建筑评价标准', 'section': '4.1 安全耐久', 'requirement': '绿色建筑星级≥三星'},
    ],
    'BIM': [
        {'code': 'GB/T 51212-2016', 'name': '建筑信息模型应用统一标准', 'section': '6.0 模型交付', 'requirement': 'BIM模型LOD≥300'},
    ],
    'LEED': [
        {'code': 'USGBC', 'name': 'LEED v4 BD+C', 'section': 'EA credits', 'requirement': '建筑能耗降低≥20%方可参评'},
    ],

    # 电梯/扶梯
    'ESCALATOR': [
        {'code': 'GB 16899-2011', 'name': '自动扶梯和自动人行道的制造与安装安全规范', 'section': '5.2 梯级', 'requirement': '自动扶梯倾斜角≤35°'},
    ],

    # 电气系统
    'LIGHTNING': [
        {'code': 'GB 50057-2013', 'name': '建筑物防雷设计规范', 'section': '4.4 第二类防雷建筑物', 'requirement': '防雷接地冲击电阻≤10Ω'},
    ],
    'UPS': [
        {'code': 'GB 7260.1-2008', 'name': '不间断电源设备', 'section': '1.0 基本要求', 'requirement': 'UPS额定容量按负荷120%选取'},
    ],
    'TVIT': [
        {'code': 'GB 50631-2010', 'name': '住宅小区建筑电气设计与施工规范', 'section': '6.0 信息设施系统', 'requirement': '每户设光纤入户信息配线箱'},
    ],

    # 声学/隔振
    'ACOUSTIC': [
        {'code': 'GB 50118-2010', 'name': '民用建筑隔声设计规范', 'section': '4.0 墙体隔声', 'requirement': '分户墙空气声隔声≥45dB'},
    ],
    'VIBRATION': [
        {'code': 'GB 50411-2007', 'name': '建筑节能工程施工质量验收规范', 'section': '7.0 空调系统', 'requirement': '机房振动≤80dB(A)'},
    ],
}

# 块名 → 构件类型/规格表
BLOCK_TO_COMPONENT = {
    'TCH_OPENING': {
        'type': '预留孔洞',
        'description': '预留设备管道穿墙/穿板孔洞',
        'common_sizes': ['DN50', 'DN100', 'DN150', 'DN200'],
        'reference': '03J502-2 预留孔洞图集',
    },
    'TCH_RADIUSDIM': {
        'type': '弧形标注',
        'description': '圆弧形构件尺寸标注',
        'common': 'R标注',
    },
    'TCH_CROSSSTAIR': {
        'type': '交叉楼梯',
        'description': '平面交叉的楼梯形式',
        'reference': '12J304 民用建筑工程勤察设计文件编制深度规定',
    },
    'TCH_LINESTAIR': {
        'type': '直线楼梯',
        'description': '单跑或双跑直线楼梯',
        'reference': '04J412 楼梯图集',
    },
    'TCH_INDEXPOINTER': {
        'type': '索引符号',
        'description': '详图索引标记系统',
        'reference': '03J501 建筑构造用料做法',
    },
    'PUB_DIM': {
        'type': '尺寸标注',
        'description': '统一尺寸标注样式',
    },
    'PUB_HATCH': {
        'type': '填充图案',
        'description': '统一填充图案系统',
    },
    'PUB_TEXT': {
        'type': '文字样式',
        'description': '统一文字样式（仿宋/黑体）',
    },
    'PUB_WALL': {
        'type': '墙体',
        'description': '标准墙体（200/100/60mm等）',
    },
    'PUB_TITLE': {
        'type': '标题栏',
        'description': '标准图纸标题栏',
        'reference': 'GB/T 50001-2017 总图制图标准',
    },
}


def lookup_specs_for_layer(layer_name: str) -> List[Dict[str, Any]]:
    """查询图层对应的规范条目

    Args:
        layer_name: 图层名称

    Returns:
        匹配到的规范条目列表，未匹配则返回空列表
    """
    layer_upper = layer_name.upper()
    matched_specs = []
    matched_keys = set()

    for key, specs in LAYER_TO_SPECS.items():
        if key in layer_upper:
            if key not in matched_keys:
                matched_specs.extend(specs)
                matched_keys.add(key)

    return matched_specs


def lookup_component_info(block_name: str) -> Optional[Dict[str, Any]]:
    """查询块对应的构件信息

    Args:
        block_name: 块名称

    Returns:
        构件信息字典，未匹配则返回 None
    """
    block_upper = block_name.upper()
    for key, info in BLOCK_TO_COMPONENT.items():
        if key in block_upper:
            return {'block': key, **info}
    return None


# 专业类别关键词映射（用于 get_layer_category）
_CATEGORY_KEYWORDS = {
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
    """识别图层属于哪个专业类别（支持英文命名层和中文CAD编码层）

    Args:
        layer_name: 图层名称

    Returns:
        专业类别字符串（如 '建筑', '结构', '给排水', '其他' 等）
    """
    layer_upper = layer_name.upper()

    # 1. Explicit semantic match (English-named layers)
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in layer_upper:
                return category

    # 2. Coded layer: use first-char prefix (TArch/天正 convention)
    try:
        from ..ai.inference import LAYER_PREFIX_CATEGORY as _LC
    except ImportError:
        from inference import LAYER_PREFIX_CATEGORY as _LC  # type: ignore
    prefix = layer_name[0].upper() if layer_name and layer_name[0].isalpha() else ''
    if prefix in _LC:
        return _LC[prefix][1]  # Chinese category name

    return '其他'
