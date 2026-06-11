"""
src/blueprint/ai/inference.py - 图纸语义推理引擎

从 blueprint-ai/inference.py 迁移并增强。
提供：
- 图层语义推理（规则引擎）
- 图纸类型识别（规则+LLM双引擎）
- 工程信息提取（规则+LLM双引擎）
- 设计原则和施工要求推断
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
LLM_API_URL = f"{OLLAMA_BASE_URL}/api/generate"


# ── Drawing-type Keywords ─────────────────────────────────────
DRAWING_TYPE_KEYWORDS = {
    '建筑': ['WALL', 'DOOR', 'WINDOW', 'FLOOR', 'CEILING', 'STAIR', 'RAILING', 'CURTAIN', 'ARCH'],
    '结构': ['COLUMN', 'BEAM', 'SLAB', 'FOUNDATION', 'FOOTING', 'REBAR', 'STEEL', 'SECTION'],
    '机电': ['MECHANICAL', 'ELECTRICAL', 'PLUMBING', 'HVAC', 'MEP', 'EQUIPMENT'],
    '给排水': ['PLUMBING', 'WATER', 'DRAIN', 'SEWER', 'PIPE', 'VALVE'],
    '暖通': ['HVAC', 'AIR', 'DUCT', 'VENT', 'CHILLER', 'BOILER', 'AHU', 'FAN', 'COIL'],
    '电气': ['ELECTRICAL', 'POWER', 'LIGHTING', 'CABLE', 'PANEL', 'CIRCUIT', 'SWITCH'],
    '消防': ['FIRE', 'SPRINKLER', 'ALARM', 'SMOKE', 'EXIT', 'FIRE_DOOR'],
    '景观': ['LANDSCAPE', 'PLANT', 'TREE', 'LAWN', 'PATH', 'WALKWAY'],
    '总图': ['GRID', 'TOPO', 'SURVEY', 'ROAD', 'PARKING', 'GREEN'],
    '精装': ['DECOR', 'FINISH', 'FURNITURE', 'SIGNAGE'],
}

# ── Layer Semantics ───────────────────────────────────────────
LAYER_SEMANTICS = {
    'AXIS': ('axis', '定位轴线', '施工定位依据'),
    'WALL': ('wall', '墙体', '建筑围护结构'),
    'DOOR': ('door', '门窗', '建筑开口'),
    'WINDOW': ('window', '窗户', '建筑采光通风'),
    'STAIR': ('stair', '楼梯', '垂直交通'),
    'COLUMN': ('column', '柱子', '结构竖向构件'),
    'BEAM': ('beam', '梁', '结构水平构件'),
    'SLAB': ('slab', '板', '结构水平构件'),
    'HATCH': ('hatch', '填充图案', '材料或区域标识'),
    'DIM': ('dimension', '尺寸标注', '施工测量依据'),
    'TEXT': ('text', '文字标注', '说明和指引'),
    'TITLE': ('title', '标题栏', '图纸信息'),
    'CENTER': ('centerline', '中心线', '定位参考'),
    'HIDDEN': ('hidden', '虚线/隐藏线', '不可见轮廓'),
    'DASHED': ('dashed', '虚线', '辅助线'),
    'SECTION': ('section', '剖面', '内部构造'),
    'ELEVATION': ('elevation', '立面', '外观设计'),
    'PLAN': ('plan', '平面图', '平面布局'),
    'DETAIL': ('detail', '详图', '局部放大'),
    'FIRE': ('fire', '消防', '消防安全设施'),
    'ELECTRICAL': ('electrical', '电气', '电力系统'),
    'PLUMBING': ('plumb', '给排水', '水管系统'),
    'HVAC': ('hvac', '暖通', '空气调节系统'),
    'MECHANICAL': ('mechanical', '机电', '机械系统'),
    'FOUNDATION': ('foundation', '基础', '地基结构'),
    'FOOTING': ('footing', '独立基础', '柱下基础'),
    'REBAR': ('rebar', '钢筋', '混凝土配筋'),
    'STEEL': ('steel', '钢结构', '钢构件'),
    'PIPE': ('pipe', '管道', '管线系统'),
    'DUCT': ('duct', '风管', '通风管道'),
    'EQUIP': ('equipment', '设备', '工艺设备'),
    'RAILING': ('railing', '栏杆', '安全防护'),
    'RAMP': ('ramp', '坡道', '无障碍通道'),
    'LANDSCAPE': ('landscape', '景观', '绿化园林'),
    'GRID': ('grid', '网格线', '轴网系统'),
    'PARKING': ('parking', '车位', '停车场'),
    'TOPO': ('topography', '地形', '竖向设计'),
    'SURVEY': ('survey', '测量', '地形测绘'),
}

# ── Chinese Layer Keywords ────────────────────────────────────
CHINESE_LAYER_KEYWORDS = {
    '墙体': ('wall', '墙体', '建筑围护结构'),
    '墙': ('wall', '墙体', '建筑围护结构'),
    '轴线': ('axis', '定位轴线', '施工定位依据'),
    '轴网': ('axis', '定位轴线', '轴网系统'),
    '标注': ('dimension', '尺寸标注', '施工测量依据'),
    '尺寸': ('dimension', '尺寸标注', '施工测量依据'),
    '门窗': ('door', '门窗', '建筑开口'),
    '门': ('door', '门', '建筑开口'),
    '窗': ('window', '窗户', '建筑采光通风'),
    '楼梯': ('stair', '楼梯', '垂直交通'),
    '扶手': ('railing', '栏杆/扶手', '安全防护'),
    '栏杆': ('railing', '栏杆', '安全防护'),
    '坡道': ('ramp', '坡道', '无障碍通道'),
    '幕墙': ('curtain', '幕墙', '建筑外装饰'),
    '雨棚': ('canopy', '雨棚/挑檐', '建筑入口遮挡'),
    '吊顶': ('ceiling', '吊顶/天花', '建筑内部装饰'),
    '地面': ('floor', '地面/楼面', '建筑饰面'),
    '防水': ('waterproof', '防水层', '建筑防水构造'),
    '保温': ('insulation', '保温层', '建筑节能构造'),
    '防火': ('fire', '防火', '消防安全设施'),
    '疏散': ('fire', '消防疏散', '安全疏散设施'),
    '消防': ('fire', '消防', '消防安全设施'),
    '电气': ('electrical', '电气', '电力系统'),
    '照明': ('light', '照明', '电气照明系统'),
    '配电': ('panel', '配电', '电气配电系统'),
    '插座': ('socket', '插座', '电气插座系统'),
    '给排水': ('plumb', '给排水', '水管系统'),
    '给水': ('plumb', '给水', '供水系统'),
    '排水': ('drain', '排水', '排水系统'),
    '污水': ('drain', '污水', '污废水系统'),
    '雨水': ('drain', '雨水', '雨水排放系统'),
    '喷淋': ('sprinkler', '喷淋', '消防喷淋系统'),
    '消火栓': ('fire', '消火栓', '消防设施'),
    '暖通': ('hvac', '暖通', '空气调节系统'),
    '通风': ('duct', '通风', '通风管道系统'),
    '风管': ('duct', '风管', '通风管道'),
    '空调': ('hvac', '空调', '空气调节'),
    '风机': ('fan', '风机', '通风设备'),
    '风口': ('diffuser', '风口', '送回风口'),
    '水管': ('pipe', '管道', '管线系统'),
    '管道': ('pipe', '管道', '管线系统'),
    '阀门': ('valve', '阀门', '管道控制'),
    '设备': ('equipment', '设备', '工艺设备'),
    '柱子': ('column', '柱', '结构竖向构件'),
    '柱': ('column', '柱', '结构竖向构件'),
    '梁': ('beam', '梁', '结构水平构件'),
    '板': ('slab', '板', '结构水平构件'),
    '楼板': ('slab', '楼板', '结构水平构件'),
    '基础': ('foundation', '基础', '地基结构'),
    '钢筋': ('rebar', '钢筋', '混凝土配筋'),
    '钢结构': ('steel', '钢结构', '钢构件'),
    '钢柱': ('steel', '钢柱', '钢结构竖向构件'),
    '钢梁': ('steel', '钢梁', '钢结构水平构件'),
    '节点': ('detail', '节点', '局部构造详图'),
    '详图': ('detail', '详图', '局部放大'),
    '剖面': ('section', '剖面', '内部构造'),
    '立面': ('elevation', '立面', '外观设计'),
    '节点大样': ('detail', '节点大样', '局部构造详图'),
    '标高': ('elevation', '标高', '竖向高度标注'),
    '房间': ('room', '房间', '功能分区'),
    '面积': ('area', '面积', '面积计算标注'),
    '总图': ('landscape', '总图/景观', '室外工程'),
    '景观': ('landscape', '景观', '绿化园林'),
    '绿化': ('landscape', '绿化', '景观绿化'),
    '道路': ('road', '道路', '室外道路'),
    '停车': ('parking', '车位', '停车场'),
    '场地': ('site', '场地', '室外场地'),
    '填充': ('hatch', '填充', '材料填充图案'),
    '轮廓': ('outline', '轮廓线', '边界轮廓线'),
    '中心线': ('centerline', '中心线', '定位参考'),
    '虚线': ('hidden', '虚线/隐藏线', '不可见轮廓'),
    '折断线': ('breakline', '折断线', '断裂省略线'),
    '索引': ('detail', '索引/详图', '详图索引号'),
    '图例': ('legend', '图例', '符号说明'),
    '图框': ('title', '图框', '图纸边框'),
    '标题': ('title', '标题', '图纸标题'),
}

# ── TArch Layer Prefix Categories ────────────────────────────
LAYER_PREFIX_CATEGORY = {
    'S': ('structural', '结构'),
    'C': ('structural', '结构'),
    'A': ('architectural', '建筑'),
    'E': ('electrical', '电气'),
    'M': ('mechanical', '机电'),
    'P': ('plumbing', '给排水'),
    'W': ('plumbing', '给排水'),
    'H': ('hvac', '暖通'),
    'F': ('fire', '消防'),
    'D': ('dimension', '建筑'),
    'X': ('dimension', '建筑'),
    'T': ('title', '建筑'),
    'G': ('general', '总图'),
}

# ── Chinese Filename → Drawing Type ───────────────────────────
CHINESE_FILENAME_TYPE_MAP = {
    '总平面布置图': '总图', '总平面图': '总图', '总图': '总图',
    '管线综合图': '总图', '管线综合': '总图', '道路平面图': '总图',
    '绿化平面图': '景观', '景观平面图': '景观',
    '建筑平面图': '建筑', '平面图': '建筑',
    '建筑立面图': '建筑', '立面图': '建筑',
    '建筑剖面图': '建筑', '剖面图': '建筑',
    '建筑详图': '建筑', '详图': '建筑',
    '楼梯详图': '建筑', '节点详图': '建筑',
    '结构平面图': '结构', '结构图': '结构',
    '梁配筋图': '结构', '板配筋图': '结构', '柱配筋图': '结构',
    '基础图': '结构', '结构大样图': '结构',
    '给排水系统图': '给排水', '给排水平面图': '给排水',
    '消防系统图': '消防', '喷淋系统图': '消防', '消火栓系统图': '消防',
    'P&ID': '工艺', 'P&ID图': '工艺', '管道仪表图': '工艺', '工艺流程图': '工艺',
    '系统图': '机电',
    '暖通平面图': '暖通', '空调平面图': '暖通', '通风平面图': '暖通',
    '暖通系统图': '暖通', '空调系统图': '暖通', '风管平面图': '暖通',
    '电气系统图': '电气', '电气平面图': '电气', '配电系统图': '电气',
    '照明平面图': '电气', '强弱电平面图': '电气',
    '装修平面图': '精装', '室内平面图': '精装', '吊顶平面图': '精装',
}


# ═══════════════════════════════════════════════════════════════
# LLM Helpers
# ═══════════════════════════════════════════════════════════════

def call_llm(prompt: str, fallback: str = "", timeout: float = 10.0) -> str:
    """Call Ollama LLM. Returns fallback on timeout/error (never blocks)."""
    import urllib.request, urllib.error, json, socket
    socket_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        payload = json_dumps({"model": LLM_MODEL, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            LLM_API_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json_loads(resp.read())
            text = result.get("response", "").strip()
            return text if text else fallback
    except Exception:
        return fallback
    finally:
        socket.setdefaulttimeout(socket_timeout)


# ═══════════════════════════════════════════════════════════════
# Rule Engine: Layer Semantics
# ═══════════════════════════════════════════════════════════════

def infer_layer_semantics(layer_name: str) -> Dict[str, Any]:
    """
    推断单个图层的语义含义
    返回: { confidence, english, chinese, usage, matched_by }
    """
    name = layer_name.upper()

    # 1. Exact match in LAYER_SEMANTICS
    for pattern, (eng, chn, usage) in LAYER_SEMANTICS.items():
        if pattern in name:
            return {
                'confidence': 'high',
                'english': eng,
                'chinese': chn,
                'usage': usage,
                'matched_by': 'exact',
            }

    # 2. Chinese keyword match
    for kw, (eng, chn, usage) in CHINESE_LAYER_KEYWORDS.items():
        if kw in layer_name:
            return {
                'confidence': 'medium',
                'english': eng,
                'chinese': chn,
                'usage': usage,
                'matched_by': 'chinese',
            }

    # 3. Prefix match (TArch encoding)
    prefix = name[0] if name and name[0].isalpha() else ''
    if prefix in LAYER_PREFIX_CATEGORY:
        eng, chn = LAYER_PREFIX_CATEGORY[prefix]
        return {
            'confidence': 'prefix',
            'english': eng,
            'chinese': chn,
            'usage': f'{chn}专业图层',
            'matched_by': 'prefix',
        }

    return {
        'confidence': 'none',
        'english': 'unknown',
        'chinese': '未知',
        'usage': '未识别图层',
        'matched_by': 'none',
    }


def analyze_layers(layers: List[str]) -> List[Dict[str, Any]]:
    """分析所有图层，返回语义分析结果"""
    results = []
    for name in layers:
        sem = infer_layer_semantics(name)
        sem['name'] = name
        results.append(sem)
    return results


# ═══════════════════════════════════════════════════════════════
# Rule Engine: Drawing Type Inference
# ═══════════════════════════════════════════════════════════════

def infer_drawing_type(
    layers: List[str],
    blocks: List[str] = None,
    raw_text: str = "",
    file_name: str = "",
) -> Dict[str, Any]:
    """
    规则引擎：从图层/块名/文件名推断图纸类型
    返回: { primary, confidence, categories, method, prefix_counts }
    """
    blocks = blocks or []
    scores: Dict[str, int] = {}

    # ── Step 1: Layer prefix distribution (TArch encoding) ──
    prefix_counts: Dict[str, int] = {}
    for lname in layers:
        prefix = lname[0].upper() if lname and lname[0].isalpha() else ''
        if prefix in LAYER_PREFIX_CATEGORY:
            cat = LAYER_PREFIX_CATEGORY[prefix][1]
            prefix_counts[cat] = prefix_counts.get(cat, 0) + 1

    for cat, cnt in prefix_counts.items():
        scores[cat] = scores.get(cat, 0) + cnt

    # ── Step 2: Keyword matching ──
    combined = ' '.join(layers + blocks).upper()
    for category, keywords in DRAWING_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.upper() in combined)
        if score > 0:
            scores[category] = scores.get(category, 0) + score

    # ── Step 3: Filename matching (longest-match-first) ──
    if file_name:
        for pattern, dtype in sorted(CHINESE_FILENAME_TYPE_MAP.items(), key=lambda x: -len(x[0])):
            if pattern in file_name:
                scores[dtype] = scores.get(dtype, 0) + 5  # filename match is strong signal
                break

    if not scores:
        return {
            'primary': 'unknown',
            'confidence': 0,
            'categories': [],
            'method': 'none',
            'prefix_counts': prefix_counts,
        }

    # ── Final scoring ──
    primary = max(scores, key=scores.get)
    total = sum(scores.values())
    primary_score = scores[primary]
    confidence = min(primary_score / max(total, 1), 1.0)

    # Normalize confidence
    if confidence > 0.6:
        confidence = min(confidence * 1.2, 0.95)
    elif confidence < 0.2:
        confidence = 0.2

    categories = sorted(scores.items(), key=lambda x: -x[1])

    return {
        'primary': primary,
        'confidence': round(confidence, 2),
        'categories': categories,
        'method': 'rule_engine',
        'prefix_counts': prefix_counts,
    }


# ═══════════════════════════════════════════════════════════════
# Rule Engine: Design Principles
# ═══════════════════════════════════════════════════════════════

def infer_design_principles(
    drawing_type: str,
    layers: List[str],
    raw_text: str = "",
) -> List[Dict[str, str]]:
    """从图纸类型和图层推断设计原则"""
    principles = []

    type_principles = {
        '建筑': [
            {'type': '防火设计', 'description': '应符合《建筑设计防火规范》GB 50016要求', 'source': 'drawing_type'},
            {'type': '无障碍设计', 'description': '公共建筑应满足无障碍设计规范', 'source': 'drawing_type'},
        ],
        '结构': [
            {'type': '抗震设计', 'description': '应符合《建筑抗震设计规范》GB 50011要求', 'source': 'drawing_type'},
            {'type': '荷载设计', 'description': '荷载取值应符合《建筑结构荷载规范》GB 50009', 'source': 'drawing_type'},
        ],
        '给排水': [
            {'type': '节水设计', 'description': '应采用节水型器具，符合《建筑给水排水设计标准》', 'source': 'drawing_type'},
        ],
        '暖通': [
            {'type': '节能设计', 'description': '应符合《公共建筑节能设计标准》GB 50189', 'source': 'drawing_type'},
        ],
        '电气': [
            {'type': '安全设计', 'description': '电气设计应符合《民用建筑电气设计标准》GB 51348', 'source': 'drawing_type'},
        ],
        '消防': [
            {'type': '防火安全', 'description': '消防设计应符合《建筑设计防火规范》GB 50016', 'source': 'drawing_type'},
        ],
    }

    if drawing_type in type_principles:
        principles.extend(type_principles[drawing_type])

    # Layer-based principles
    layer_str = ' '.join(layers).upper()
    if any(kw in layer_str for kw in ['FIRE', 'SPRINKLER', '消防', '喷淋']):
        principles.append({'type': '消防专项', 'description': '图纸包含消防系统，需专项审查', 'source': 'layer'})
    if any(kw in layer_str for kw in ['SEISMIC', '抗震']):
        principles.append({'type': '抗震专项', 'description': '涉及抗震构造，需满足抗震等级要求', 'source': 'layer'})
    if any(kw in layer_str for kw in ['GREEN', '绿化', '景观']):
        principles.append({'type': '绿色建筑', 'description': '涉及景观设计，宜考虑绿色建筑要求', 'source': 'layer'})

    return principles


# ═══════════════════════════════════════════════════════════════
# Rule Engine: Construction Requirements
# ═══════════════════════════════════════════════════════════════

def infer_construction_requirements(
    drawing_type: str,
    layers: List[str],
    raw_text: str = "",
) -> List[Dict[str, str]]:
    """推断施工要求"""
    requirements = []

    if drawing_type == '建筑':
        requirements.extend([
            {'category': '墙体', 'description': '砌体墙需设置构造柱和圈梁', 'note': '按抗震要求'},
            {'category': '防水', 'description': '卫生间/屋面防水层施工后需做蓄水试验', 'note': '不少于24h'},
        ])
    elif drawing_type == '结构':
        requirements.extend([
            {'category': '钢筋', 'description': '钢筋连接方式和锚固长度须符合设计要求', 'note': '按16G101图集'},
            {'category': '混凝土', 'description': '混凝土强度等级需满足设计要求，养护不少于7天', 'note': ''},
        ])
    elif drawing_type == '给排水':
        requirements.extend([
            {'category': '管道', 'description': '管道安装完成后需做通水/通球试验', 'note': ''},
            {'category': '试压', 'description': '给水管道需做压力试验，试验压力为工作压力1.5倍', 'note': ''},
        ])
    elif drawing_type == '暖通':
        requirements.extend([
            {'category': '风管', 'description': '风管安装后需做漏光/漏风试验', 'note': ''},
            {'category': '保温', 'description': '保温层施工应在管道试压合格后进行', 'note': ''},
        ])
    elif drawing_type == '电气':
        requirements.extend([
            {'category': '接地', 'description': '接地电阻测试值须符合设计要求', 'note': '一般≤4Ω'},
            {'category': '绝缘', 'description': '电缆敷设后需做绝缘电阻测试', 'note': ''},
        ])

    return requirements


# ═══════════════════════════════════════════════════════════════
# Rule Engine: Project Info Extraction
# ═══════════════════════════════════════════════════════════════

def extract_project_info(
    layers: List[str],
    raw_text: str = "",
    file_name: str = "",
    metadata: Dict = None,
) -> Dict[str, Any]:
    """
    从图纸中提取项目信息（规则引擎）
    返回结构化项目信息
    """
    info = {}

    # ── Extract from filename ──
    if file_name:
        # Project name (before first underscore or dash)
        stem = Path(file_name).stem
        # Common patterns: "XX项目_建筑平面图", "XX工程-结构图"
        for sep in ['_', '-', '——', '—']:
            if sep in stem:
                info['project_name'] = stem.split(sep)[0].strip()
                break

    # ── Extract from raw text ──
    if raw_text:
        # Building area
        area_match = re.search(r'建筑面积[：:]\s*([\d,]+\.?\d*)\s*㎡', raw_text)
        if area_match:
            info['building_area'] = area_match.group(1).replace(',', '') + ' ㎡'

        # Number of floors
        floor_match = re.search(r'层数[：:]\s*(\d+)\s*层', raw_text)
        if floor_match:
            info['floor_count'] = floor_match.group(1) + ' 层'

        # Structure type
        struct_match = re.search(r'结构形式[：:]\s*(.+)', raw_text)
        if struct_match:
            info['structure_type'] = struct_match.group(1).strip()

        # Design unit
        design_match = re.search(r'设计单位[：:]\s*(.+)', raw_text)
        if design_match:
            info['design_unit'] = design_match.group(1).strip()

        # Project number
        proj_match = re.search(r'工程编号[：:]\s*([\w\-]+)', raw_text)
        if proj_match:
            info['project_number'] = proj_match.group(1)

        # Drawing number
        dwg_match = re.search(r'图号[：:]\s*([\w\-/\.]+)', raw_text)
        if dwg_match:
            info['drawing_number'] = dwg_match.group(1)

    # ── Extract from metadata ──
    if metadata:
        if 'dwg_version' in metadata:
            info['dwg_version'] = metadata['dwg_version']
        if 'file_size' in metadata:
            size = metadata['file_size']
            if size > 1024 * 1024:
                info['file_size'] = f"{size / 1024 / 1024:.1f} MB"
            else:
                info['file_size'] = f"{size / 1024:.1f} KB"

    return info


# ═══════════════════════════════════════════════════════════════
# Full Analysis Pipeline (Rule-based)
# ═══════════════════════════════════════════════════════════════

def analyze_blueprint(
    layers: List[str],
    blocks: List[str] = None,
    raw_text: str = "",
    file_name: str = "",
    metadata: Dict = None,
) -> Dict[str, Any]:
    """
    完整的图纸分析流水线（规则引擎）
    返回结构化分析结果
    """
    blocks = blocks or []

    # 1. Drawing type
    drawing_type = infer_drawing_type(layers, blocks, raw_text, file_name)

    # 2. Layer semantics
    layer_analysis = analyze_layers(layers)

    # 3. Design principles
    design_principles = infer_design_principles(drawing_type['primary'], layers, raw_text)

    # 4. Construction requirements
    construction_requirements = infer_construction_requirements(drawing_type['primary'], layers, raw_text)

    # 5. Project info
    project_info = extract_project_info(layers, raw_text, file_name, metadata)

    return {
        'drawing_type': drawing_type,
        'layers_analyzed': layer_analysis,
        'total_layers': len(layers),
        'total_blocks': len(blocks),
        'design_principles': design_principles,
        'construction_requirements': construction_requirements,
        'project_info': project_info,
    }
