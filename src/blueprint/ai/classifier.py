"""
src/blueprint/ai/classifier.py - AI增强型图纸分类器

双引擎架构：
1. 规则引擎（inference.py）— 快速、确定性强
2. LLM引擎 — 语义理解更强，处理模糊情况

策略：规则优先 → LLM增强 → 置信度融合
"""

import json
import os
import time
from typing import Dict, List, Any, Optional

from .inference import (
    infer_drawing_type,
    call_llm,
    DRAWING_TYPE_KEYWORDS,
    LAYER_PREFIX_CATEGORY,
)

# ── 分类器配置 ───────────────────────────────────────────────

# 规则引擎置信度阈值：高于此值直接使用规则结果，不调LLM
RULE_CONFIDENCE_THRESHOLD = 0.5

# LLM 超时（秒）
LLM_TIMEOUT = float(os.environ.get("BLUEPRINT_LLM_TIMEOUT", "15"))

# 是否启用 LLM 增强（可关闭以节省资源）
LLM_ENABLED = os.environ.get("BLUEPRINT_LLM_ENABLED", "true").lower() == "true"


def _build_classifier_prompt(
    layers: List[str],
    blocks: List[str],
    file_name: str,
    raw_text_snippet: str = "",
) -> str:
    """构建 LLM 分类提示"""
    layers_sample = layers[:40]
    blocks_sample = blocks[:15]

    prompt = f"""你是一个建筑工程CAD图纸分类专家。请根据以下信息判断图纸类型。

## 文件名
{file_name or "未提供"}

## 图层列表（前{len(layers_sample)}个）
{', '.join(layers_sample)}

## 图块列表（前{len(blocks_sample)}个）
{', '.join(blocks_sample)}

## 提取文本摘要
{raw_text_snippet[:500] if raw_text_snippet else "无"}

## 分类规则
图层名前缀含义：A=建筑, S/C=结构, E=电气, M=机电, P/W=给排水, H=暖通, F=消防, D/X=标注, G=总图
图层名关键词：WALL/DOOR/WINDOW=建筑, COLUMN/BEAM/SLAB=结构, PIPE/DRAIN=给排水, HVAC/DUCT=暖通

## 可选类型
建筑、结构、给排水、暖通、电气、消防、总图、景观、机电、精装、工艺、标注、其他

请返回JSON格式（只返回JSON，不要其他文字）：
{{"primary": "主要类型", "secondary": "次要类型或空字符串", "confidence": 0-100, "reasoning": "简短推理"}}"""

    return prompt


def _parse_llm_response(text: str) -> Optional[Dict[str, Any]]:
    """解析 LLM 返回的 JSON"""
    if not text:
        return None

    text = text.strip()

    # 尝试直接解析
    try:
        data = json.loads(text)
        if "primary" in data:
            return _normalize_result(data)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 块
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end])
            if "primary" in data:
                return _normalize_result(data)
        except json.JSONDecodeError:
            pass

    return None


def _normalize_result(data: Dict) -> Dict[str, Any]:
    """标准化 LLM 返回结果"""
    valid_types = {'建筑', '结构', '给排水', '暖通', '电气', '消防', '总图', '景观', '机电', '精装', '工艺', '标注', '其他', 'unknown'}

    primary = data.get("primary", "unknown")
    if primary not in valid_types:
        # 尝试模糊匹配
        for vt in valid_types:
            if vt in primary or primary in vt:
                primary = vt
                break
        else:
            primary = "unknown"

    confidence = data.get("confidence", 50)
    try:
        confidence = int(confidence)
        confidence = max(0, min(100, confidence))
    except (ValueError, TypeError):
        confidence = 50

    return {
        "primary": primary,
        "secondary": data.get("secondary", ""),
        "confidence": confidence / 100.0,
        "reasoning": data.get("reasoning", ""),
        "source": "llm",
    }


def classify_with_llm(
    layers: List[str],
    blocks: List[str] = None,
    file_name: str = "",
    raw_text: str = "",
) -> Optional[Dict[str, Any]]:
    """使用 LLM 进行图纸分类"""
    if not LLM_ENABLED:
        return None

    blocks = blocks or []
    prompt = _build_classifier_prompt(layers, blocks, file_name, raw_text)

    start = time.time()
    response = call_llm(prompt, fallback="", timeout=LLM_TIMEOUT)
    elapsed = time.time() - start

    if not response:
        return None

    result = _parse_llm_response(response)
    if result:
        result['llm_time'] = round(elapsed, 2)

    return result


def smart_classify(
    layers: List[str],
    blocks: List[str] = None,
    raw_text: str = "",
    file_name: str = "",
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    智能图纸分类：规则引擎 + LLM 双引擎

    策略：
    1. 先跑规则引擎
    2. 规则置信度高 → 直接返回（可选LLM二次确认）
    3. 规则置信度低 → 调 LLM
    4. 融合两部分结果

    返回: {
        primary, confidence, method,
        rule_result, llm_result, layer_distribution
    }
    """
    blocks = blocks or []

    # ── Step 1: Rule engine ──
    rule_result = infer_drawing_type(layers, blocks, raw_text, file_name)

    # ── Step 2: Decide if LLM needed ──
    rule_confidence = rule_result.get('confidence', 0)
    need_llm = (
        use_llm
        and LLM_ENABLED
        and rule_confidence < RULE_CONFIDENCE_THRESHOLD
    )

    llm_result = None
    if need_llm:
        llm_result = classify_with_llm(layers, blocks, file_name, raw_text)

    # ── Step 3: Fuse results ──
    if llm_result and llm_result.get('confidence', 0) > 0.3:
        # LLM 有效：融合
        llm_conf = llm_result['confidence']
        rule_weight = rule_confidence / (rule_confidence + llm_conf) if (rule_confidence + llm_conf) > 0 else 0.5

        # 如果两者一致，提升置信度
        if llm_result['primary'] == rule_result['primary']:
            fused_confidence = min(max(rule_confidence, llm_conf) + 0.1, 0.95)
            method = 'fused_agree'
        else:
            # 不一致：取置信度高的
            if llm_conf > rule_confidence:
                fused_confidence = llm_conf
                method = 'llm_override'
            else:
                fused_confidence = rule_confidence
                method = 'rule_override'

        return {
            'primary': llm_result['primary'] if llm_conf > rule_confidence else rule_result['primary'],
            'secondary': llm_result.get('secondary', '') or rule_result.get('primary', ''),
            'confidence': round(fused_confidence, 2),
            'method': method,
            'rule_result': {
                'primary': rule_result['primary'],
                'confidence': rule_result['confidence'],
            },
            'llm_result': {
                'primary': llm_result['primary'],
                'confidence': llm_result['confidence'],
                'reasoning': llm_result.get('reasoning', ''),
                'time': llm_result.get('llm_time', 0),
            },
            'layer_distribution': rule_result.get('prefix_counts', {}),
        }
    else:
        # 只有规则引擎结果
        return {
            'primary': rule_result['primary'],
            'secondary': '',
            'confidence': rule_result['confidence'],
            'method': rule_result.get('method', 'rule_engine'),
            'rule_result': {
                'primary': rule_result['primary'],
                'confidence': rule_result['confidence'],
            },
            'llm_result': None,
            'layer_distribution': rule_result.get('prefix_counts', {}),
        }


# ═══════════════════════════════════════════════════════════════
# Batch Classification
# ═══════════════════════════════════════════════════════════════

def batch_classify(
    files_info: List[Dict[str, Any]],
    use_llm: bool = True,
) -> List[Dict[str, Any]]:
    """
    批量分类多个图纸文件

    files_info: [
        { "file_name": "...", "layers": [...], "blocks": [...], "raw_text": "..." },
        ...
    ]
    """
    results = []
    for info in files_info:
        result = smart_classify(
            layers=info.get('layers', []),
            blocks=info.get('blocks', []),
            raw_text=info.get('raw_text', ''),
            file_name=info.get('file_name', ''),
            use_llm=use_llm,
        )
        result['file_name'] = info.get('file_name', '')
        results.append(result)
    return results
