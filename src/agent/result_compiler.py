"""
agent/result_compiler.py - 结果整合

将 Sub-Agent 的执行结果整合为：
1. 面向用户的友好输出（text）
2. 结构化数据（structured）
3. 置信度评估
"""

from typing import Any, Dict, List

from agent.base_agent import AgentResult


# ─────────────────────────────────────────────────────────────────
# ResultCompiler
# ─────────────────────────────────────────────────────────────────

class ResultCompiler:
    """
    结果整合器

    职责：
    - 将 AgentResult 转换为用户友好的文本
    - 提取关键信息（confidence/suggestions/issues）
    - 多结果合并
    """

    async def compile(self, result: AgentResult) -> Dict:
        """
        整合单个 Agent 的执行结果

        Args:
            result: AgentResult

        Returns:
            {
                'output': Any,         # 原始输出
                'text': str,           # 友好文本描述
                'confidence': float,   # 综合置信度
                'summary': str,        # 简短摘要
                'suggestions': List,   # 建议列表
                'issues': List,        # 问题列表
            }
        """
        output = result.output or {}
        confidence = result.confidence

        # 生成友好文本
        text_parts = []
        if isinstance(output, dict):
            # 图纸分析结果
            if 'drawing_type' in output:
                text_parts.append(f"📋 图纸类型：**{output['drawing_type']}**（置信度 {output.get('type_confidence', confidence)*100:.0f}%）")

            if 'analysis' in output and output['analysis']:
                analysis_text = output['analysis'].get('analysis', '')
                if analysis_text:
                    text_parts.append(f"\n📝 **AI分析**：{analysis_text[:200]}...")

            if 'quantities' in output and output['quantities']:
                q = output['quantities']
                quantities = q.get('quantities', [])
                if quantities:
                    text_parts.append("\n📐 **工程量清单**：")
                    for item in quantities[:5]:
                        text_parts.append(f"  • {item.get('name', 'Unknown')}: 约 {item.get('estimated', 0)} {item.get('unit', '')}")

            if 'optimizations' in output and output['optimizations']:
                opts = output['optimizations'].get('suggestions', [])
                if opts:
                    text_parts.append("\n💡 **优化建议**：")
                    for opt in opts[:3]:
                        text_parts.append(f"  • [{opt.get('type', '')}] {opt.get('recommendation', '')[:80]}")

        elif isinstance(output, str):
            text_parts.append(output)

        # 问题列表
        issues = result.errors or []

        return {
            'output': output,
            'text': '\n'.join(text_parts) if text_parts else str(output),
            'confidence': confidence,
            'summary': self._make_summary(output),
            'suggestions': result.suggestions or [],
            'issues': issues,
            'status': result.status,
        }

    async def compile_multi(self, results: List[AgentResult]) -> Dict:
        """
        整合多个 Agent 的执行结果

        Args:
            results: AgentResult 列表

        Returns:
            {
                'output': List,        # 所有原始输出
                'text': str,           # 合并后的友好文本
                'confidence': float,   # 综合置信度（取平均）
                'summaries': List[str],# 各结果摘要
            }
        """
        if not results:
            return {
                'output': [],
                'text': '无执行结果',
                'confidence': 0.0,
                'summaries': [],
            }

        # 合并所有输出
        all_outputs = []
        all_texts = []
        all_suggestions = []
        all_issues = []
        confidences = []

        for result in results:
            compiled = await self.compile(result)
            all_outputs.append(result.output)
            if compiled['text']:
                all_texts.append(compiled['text'])
            all_suggestions.extend(compiled['suggestions'])
            all_issues.extend(compiled['issues'])
            confidences.append(result.confidence)

        # 生成综合文本
        combined_text = '\n\n'.join(all_texts)

        return {
            'output': all_outputs,
            'text': combined_text,
            'confidence': sum(confidences) / len(confidences) if confidences else 0.0,
            'summaries': [self._make_summary(r.output) for r in results],
            'suggestions': all_suggestions[:10],
            'issues': all_issues[:10],
            'agent_count': len(results),
        }

    def _make_summary(self, output: Any) -> str:
        """生成简短摘要"""
        if not output:
            return '执行完成'

        if isinstance(output, dict):
            if 'drawing_type' in output:
                return f"图纸类型识别为 {output['drawing_type']}"
            if 'message' in output:
                return str(output['message'])[:100]
            keys = list(output.keys())
            if keys:
                return f"返回 {len(keys)} 个字段：{', '.join(keys[:3])}"

        if isinstance(output, str):
            return output[:100]

        return '执行完成'