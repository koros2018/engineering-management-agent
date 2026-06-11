"""
src/blueprint/ai/extractor.py - 工程信息智能提取器

从图纸解析结果中提取结构化工程信息：
- 项目名称、工程编号
- 建筑面积、层数、高度
- 结构形式、基础类型
- 设计单位、图号
- 材料规格、设计参数

双引擎：规则提取（正则）+ LLM增强（语义理解）
"""

import os
import re
from src.utils import json_dumps, json_loads
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from .inference import call_llm

# ── 配置 ─────────────────────────────────────────────────────

LLM_TIMEOUT_EXTRACT = float(os.environ.get("BLUEPRINT_EXTRACT_TIMEOUT", "20"))
LLM_ENABLED = os.environ.get("BLUEPRINT_LLM_ENABLED", "true").lower() == "true"

# ── 正则提取规则 ─────────────────────────────────────────────

# 建筑面积
AREA_PATTERNS = [
    r'建筑面积[：:\s]*([\d,]+\.?\d*)\s*[㎡m²]',
    r'建筑总面积[：:\s]*([\d,]+\.?\d*)\s*[㎡m²]',
    r'总建筑面积[：:\s]*([\d,]+\.?\d*)\s*[㎡m²]',
    r'建筑面积[：:\s]*([\d,]+\.?\d*)',
    r'面积[：:\s]*([\d,]+\.?\d*)\s*[㎡m²]',
    r'占地面积[：:\s]*([\d,]+\.?\d*)\s*[㎡m²]',
]

# 层数
FLOOR_PATTERNS = [
    r'层数[：:\s]*(\d+)\s*层',
    r'地上(\d+)层',
    r'地下(\d+)层',
    r'共(\d+)层',
    r'(\d+)\s*层\s*建筑',
    r'建筑层数[：:\s]*(\d+)',
]

# 建筑高度
HEIGHT_PATTERNS = [
    r'建筑高度[：:\s]*([\d,]+\.?\d*)\s*[米m]',
    r'高度[：:\s]*([\d,]+\.?\d*)\s*[米m]',
    r'檐口高度[：:\s]*([\d,]+\.?\d*)',
]

# 结构形式
STRUCTURE_PATTERNS = [
    r'结构形式[：:\s]*([^\n，。,]+)',
    r'结构类型[：:\s]*([^\n，。,]+)',
    r'基础形式[：:\s]*([^\n，。,]+)',
    r'基础类型[：:\s]*([^\n，。,]+)',
]

# 设计单位
DESIGN_UNIT_PATTERNS = [
    r'设计单位[：:\s]*([^\n，。,]+)',
    r'设计院[：:\s]*([^\n，。,]+)',
    r'设计院[：:\s]*([^\n，。,]+)',
]

# 图号
DRAWING_NO_PATTERNS = [
    r'图号[：:\s]*([^\n\s]+)',
    r'图纸编号[：:\s]*([^\n\s]+)',
    r'图\s*号[：:\s]*([^\n\s]+)',
]

# 工程编号
PROJECT_NO_PATTERNS = [
    r'工程编号[：:\s]*([^\n\s]+)',
    r'项目编号[：:\s]*([^\n\s]+)',
    r'项目号[：:\s]*([^\n\s]+)',
]

# 项目名称（从文件名）
PROJECT_NAME_SEPARATORS = ['_', '-', '——', '—', '·', ' ']


def _regex_extract(patterns: List[str], text: str) -> Optional[str]:
    """用一组正则模式提取第一个匹配"""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def rule_extract(raw_text: str, file_name: str = "") -> Dict[str, Any]:
    """
    规则提取：用正则从文本中提取工程信息
    """
    info = {}

    # 建筑面积
    area = _regex_extract(AREA_PATTERNS, raw_text)
    if area:
        info['building_area'] = area.replace(',', '') + ' ㎡'

    # 层数
    floors = _regex_extract(FLOOR_PATTERNS, raw_text)
    if floors:
        info['floor_count'] = floors + ' 层'

    # 高度
    height = _regex_extract(HEIGHT_PATTERNS, raw_text)
    if height:
        info['building_height'] = height.replace(',', '') + ' m'

    # 结构形式
    struct = _regex_extract(STRUCTURE_PATTERNS, raw_text)
    if struct:
        info['structure_type'] = struct

    # 设计单位
    design = _regex_extract(DESIGN_UNIT_PATTERNS, raw_text)
    if design:
        info['design_unit'] = design

    # 图号
    dwg_no = _regex_extract(DRAWING_NO_PATTERNS, raw_text)
    if dwg_no:
        info['drawing_number'] = dwg_no

    # 工程编号
    proj_no = _regex_extract(PROJECT_NO_PATTERNS, raw_text)
    if proj_no:
        info['project_number'] = proj_no

    # 项目名称（从文件名推断）
    if file_name:
        stem = Path(file_name).stem
        for sep in PROJECT_NAME_SEPARATORS:
            if sep in stem:
                name = stem.split(sep)[0].strip()
                if len(name) >= 2:
                    info['project_name'] = name
                    break
        else:
            # 无分隔符，取整个文件名（去掉常见后缀）
            clean = re.sub(r'(平面图|立面图|剖面图|详图|大样|系统图|配筋图).*$', '', stem)
            if len(clean) >= 2:
                info['project_name'] = clean

    return info


# ═══════════════════════════════════════════════════════════════
# LLM Enhanced Extraction
# ═══════════════════════════════════════════════════════════════

def _build_extraction_prompt(
    raw_text: str,
    file_name: str,
    drawing_type: str,
    layers_sample: List[str],
) -> str:
    """构建 LLM 提取提示"""
    text_snippet = raw_text[:2000] if raw_text else "无"
    layers_str = ', '.join(layers_sample[:30]) if layers_sample else "无"

    return f"""你是一个建筑工程信息提取专家。请从以下CAD图纸信息中提取结构化工程信息。

## 图纸类型
{drawing_type}

## 文件名
{file_name or "未提供"}

## 图层列表（前30个）
{layers_str}

## 提取的文本内容
{text_snippet}

请提取以下字段，返回JSON格式（只返回JSON，不要其他文字）：
{{
  "project_name": "项目名称",
  "project_number": "工程编号",
  "building_area": "建筑面积（含单位）",
  "floor_count": "层数（含单位）",
  "building_height": "建筑高度（含单位）",
  "structure_type": "结构形式",
  "foundation_type": "基础类型",
  "design_unit": "设计单位",
  "drawing_number": "图号",
  "design_basis": "设计依据（规范名称）",
  "fire_resistance_rating": "耐火等级",
  "seismic_intensity": "抗震设防烈度",
  "service使用年限": "设计使用年限",
  "note": "其他值得注意的信息"
}}

如果某项信息不存在，请返回空字符串""。"""


def llm_extract(
    raw_text: str,
    file_name: str = "",
    drawing_type: str = "",
    layers: List[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    使用 LLM 进行工程信息提取
    失败时返回 None（调用方降级到规则引擎）
    """
    if not LLM_ENABLED:
        return None

    layers = layers or []
    prompt = _build_extraction_prompt(raw_text, file_name, drawing_type, layers)

    start = time.time()
    response = call_llm(prompt, fallback="", timeout=LLM_TIMEOUT_EXTRACT)
    elapsed = time.time() - start

    if not response:
        return None

    # 解析 JSON
    text = response.strip()
    try:
        data = json_loads(text)
        result = _normalize_extraction(data)
        result['extraction_method'] = 'llm'
        result['llm_time'] = round(elapsed, 2)
        return result
    except Exception:
        pass

    # 尝试提取 JSON 块
    start_idx = text.find('{')
    end_idx = text.rfind('}') + 1
    if start_idx >= 0 and end_idx > start_idx:
        try:
            data = json_loads(text[start_idx:end_idx])
            result = _normalize_extraction(data)
            result['extraction_method'] = 'llm'
            result['llm_time'] = round(elapsed, 2)
            return result
        except Exception:
            pass

    return None


def _normalize_extraction(data: Dict) -> Dict[str, Any]:
    """标准化提取结果"""
    fields = [
        'project_name', 'project_number', 'building_area', 'floor_count',
        'building_height', 'structure_type', 'foundation_type', 'design_unit',
        'drawing_number', 'design_basis', 'fire_resistance_rating',
        'seismic_intensity', 'service使用年限', 'note',
    ]
    result = {}
    for field in fields:
        val = data.get(field, '')
        result[field] = str(val).strip() if val else ''

    # 兼容旧字段名
    if not result.get('service使用年限') and data.get('design_service_life'):
        result['service使用年限'] = str(data['design_service_life']).strip()

    return result


# ═══════════════════════════════════════════════════════════════
# Smart Extraction: Rule + LLM Fusion
# ═══════════════════════════════════════════════════════════════

def smart_extract(
    raw_text: str,
    file_name: str = "",
    drawing_type: str = "",
    layers: List[str] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    智能工程信息提取：规则 + LLM 双引擎融合

    策略：
    1. 规则引擎先提取（快速、确定性高）
    2. LLM 补充提取（语义理解强，处理模糊情况）
    3. 融合：规则优先（精确匹配），LLM 补充（语义推断）

    返回: {
        project_name, building_area, floor_count, ...,
        extraction_method, rule_result, llm_result
    }
    """
    layers = layers or []

    # ── Step 1: Rule extraction ──
    rule_result = rule_extract(raw_text, file_name)

    # ── Step 2: LLM extraction ──
    llm_result = None
    if use_llm and LLM_ENABLED and (raw_text or file_name):
        llm_result = llm_extract(raw_text, file_name, drawing_type, layers)

    # ── Step 3: Fuse results ──
    fused = dict(rule_result)  # Start with rule result

    if llm_result:
        # LLM 补充规则未提取到的字段
        for key, value in llm_result.items():
            if key in ('extraction_method', 'llm_time'):
                continue
            # LLM 补充：规则没有的字段，LLM 有 → 采用 LLM
            if not fused.get(key) and value:
                fused[key] = value
            # 规则有但 LLM 为空 → 保持规则
            # 两者都有 → 规则优先（正则更精确）

        method = 'rule+llm_fusion'
    else:
        method = 'rule_only'

    fused['extraction_method'] = method
    fused['rule_fields_count'] = len(rule_result)
    fused['llm_fields_count'] = len([v for k, v in llm_result.items() if v and k not in ('extraction_method', 'llm_time')]) if llm_result else 0

    return fused


# ═══════════════════════════════════════════════════════════════
# Material Specification Extraction
# ═══════════════════════════════════════════════════════════════

def extract_material_specs(raw_text: str) -> List[Dict[str, str]]:
    """
    从文本中提取材料规格信息
    返回: [{ material, specification, unit, note }, ...]
    """
    specs = []

    # 常见材料规格模式
    material_patterns = [
        (r'混凝土[：:\s]*([^\n，。,]+)', '混凝土'),
        (r'钢筋[：:\s]*([^\n，。,]+)', '钢筋'),
        (r'砌体[：:\s]*([^\n，。,]+)', '砌体'),
        (r'砂浆[：:\s]*([^\n，。,]+)', '砂浆'),
        (r'防水材料[：:\s]*([^\n，。,]+)', '防水材料'),
        (r'保温材料[：:\s]*([^\n，。,]+)', '保温材料'),
        (r'钢材[：:\s]*([^\n，。,]+)', '钢材'),
        (r'水泥[：:\s]*([^\n，。,]+)', '水泥'),
    ]

    for pattern, material_type in material_patterns:
        match = re.search(pattern, raw_text)
        if match:
            spec = match.group(1).strip()
            if spec and len(spec) < 100:  # 过滤过长匹配
                specs.append({
                    'material': material_type,
                    'specification': spec,
                    'source': 'text_extraction',
                })

    return specs


# ═══════════════════════════════════════════════════════════════
# Design Parameter Extraction
# ═══════════════════════════════════════════════════════════════

def extract_design_params(raw_text: str) -> Dict[str, str]:
    """
    提取设计参数（荷载、强度等级等）
    """
    params = {}

    # 荷载
    load_match = re.search(r'活荷载[：:\s]*([\d.]+)\s*kN/㎡', raw_text)
    if load_match:
        params['live_load'] = load_match.group(1) + ' kN/㎡'

    # 混凝土强度
    conc_match = re.search(r'混凝土强度[等级]*[：:\s]*([^\n，。,]+)', raw_text)
    if conc_match:
        params['concrete_strength'] = conc_match.group(1).strip()

    # 钢筋等级
    steel_match = re.search(r'钢筋[等级]*[：:\s]*([^\n，。,]+)', raw_text)
    if steel_match:
        params['steel_grade'] = steel_match.group(1).strip()

    # 抗震等级
    seismic_match = re.search(r'抗震[设防]*烈度[：:\s]*([^\n，。,]+)', raw_text)
    if seismic_match:
        params['seismic_intensity'] = seismic_match.group(1).strip()

    # 耐火等级
    fire_match = re.search(r'耐火等级[：:\s]*([^\n，。,]+)', raw_text)
    if fire_match:
        params['fire_resistance_rating'] = fire_match.group(1).strip()

    # 设计使用年限
    life_match = re.search(r'设计使用年限[：:\s]*([^\n，。,]+)', raw_text)
    if life_match:
        params['design_service_life'] = life_match.group(1).strip()

    return params
