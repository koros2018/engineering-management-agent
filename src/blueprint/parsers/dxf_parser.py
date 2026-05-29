"""
src/blueprint/parsers/dxf_parser.py - DXF图纸解析器

从 blueprint-ai/dxf_parser.py 迁移。
使用ezdxf库，支持DXF R12到DXF2018。
增强容错：处理libredwg转换的DXF格式问题（换行符混乱、EOF位置不对）。
"""

import io
import os
import re
import tempfile
import ezdxf
from typing import List, Set


def _clean_dxf_stream(raw: bytes) -> str:
    """
    清理 DXF 字节流，修复 libredwg 转换的格式问题。
    
    核心问题：ezdxf tagger 不能处理空行（readline() 返回 "\n"，int("\n") 失败）。
    但空行是合法的 DXF value（空字符串），不能简单去除——去除会导致 code-value 对错位。
    
    解决方案：用状态机重建 code-value 对，跳过空行（不输出），
    保留所有非空行。如果状态机失步（遇到非整数且非关键字），
    假设是 code 位置，跳过该行。
    """
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('ascii', errors='replace')

    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    raw_lines = [l.strip() for l in text.split('\n')]

    # 快速路径：如果没有空行且没有中文垃圾数据，直接返回
    has_empty = '' in raw_lines
    if not has_empty:
        result = list(raw_lines)
        if result and result[-1] != 'EOF':
            result.append('EOF')
        return '\n'.join(result) + '\n'

    # 有空行时的处理：
    # 核心问题：空行在 code 位置时 tagger 崩溃（int("\n") 失败）
    # 但空行在 value 位置是合法的（空字符串 value）
    # 
    # 方案：状态机 + 前瞻（lookahead）
    # - 空行在 code 位置 → 跳过（下一行仍是 code）
    # - 空行在 value 位置 → 输出空字符串
    # - STRUCT_KEYWORD 在任何位置都输出并重置状态
    # - 关键修复：空行在 code 位置时，检查下一行是否是 STRUCT_KEYWORD
    #   如果是，直接跳过空行（让 STRUCT_KEYWORD 正常处理）
    # - 中文垃圾数据在 code 位置 → 跳过
    STRUCT_KEYWORDS = {'SECTION', 'ENDSEC', 'EOF', 'HEADER', 'CLASSES',
                        'TABLES', 'BLOCKS', 'ENTITIES', 'OBJECTS'}
    result = []
    expect_code = True
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]

        # 结构关键字：任何位置都输出，重置为 expect_code=True
        if line in STRUCT_KEYWORDS:
            result.append(line)
            expect_code = True
            i += 1
            continue

        if line == '':
            # 空行
            if expect_code:
                # 空行在 code 位置——跳过
                # 前瞻：如果下一行是 STRUCT_KEYWORD，直接跳过空行
                # 如果下一行是 CODE，也跳过空行（让 CODE 成为新的 code）
                # 如果下一行也是空行，继续跳过
                i += 1
                continue
            else:
                # 空行在 value 位置——输出空字符串
                result.append('')
                expect_code = True
                i += 1
                continue

        if expect_code:
            try:
                code = int(line)
                if 0 <= code <= 9999:
                    result.append(line)
                    expect_code = False
                # 超出范围的整数，跳过
            except ValueError:
                # 非整数在 code 位置——跳过（中文垃圾数据）
                pass
            i += 1
        else:
            # value 位置——接受任何非空内容
            result.append(line)
            expect_code = True
            i += 1

    # 去尾部空 value
    while result and result[-1] == '':
        result.pop()

    # 确保 EOF（不重复追加）
    if 'EOF' not in result:
        result.append('EOF')
    else:
        # EOF 已存在，移除尾部多余的 code/value
        while result and result[-1] != 'EOF':
            result.pop()

    return '\n'.join(result) + '\n'


def _fix_dxf_for_ezdxf(raw: bytes) -> io.BytesIO:
    """
    修复 libredwg 转换的 DXF 格式问题：
    1. 统一换行符为 \r\n（DXF 标准格式）
    2. 去除每行首尾空白（DXF 解析器要求）
    3. 确保 EOF 结尾
    
    注意：不去除空行！DXF HEADER section 中空行是格式的一部分，
    去除空行会破坏 group code/value 对的交替结构。
    """
    # 统一换行符为 \n
    text = raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    # 分割成行，只去除每行首尾空白（保留空行）
    lines = [line.strip() for line in text.split(b'\n')]
    # 确保以 EOF 结尾
    if lines and lines[-1] != b'EOF':
        lines.append(b'EOF')
    # 用 \r\n 连接（DXF 标准）
    fixed = b'\r\n'.join(lines) + b'\r\n'
    return io.BytesIO(fixed)

from ..types import ParseResult, FileType, EntityInfo, LayerInfo


class DXFParser:
    """DXF图纸解析器（ezdxf）"""

    def parse(self, dxf_path: str) -> ParseResult:
        result = ParseResult(
            success=False,
            file_path=dxf_path,
            file_type=FileType.DXF
        )

        try:
            # 尝试直接读取DXF（ezdxf原生容错）
            # libredwg转换的DXF可能有格式问题，失败后尝试清理
            try:
                doc = ezdxf.readfile(dxf_path)
            except Exception:
                # 清理后重试
                with open(dxf_path, 'rb') as f:
                    raw = f.read()
                cleaned = _clean_dxf_stream(raw)
                tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.dxf', delete=False)
                tmp.write(cleaned)
                tmp.flush()
                tmp_path = tmp.name
                tmp.close()
                try:
                    doc = ezdxf.readfile(tmp_path)
                finally:
                    os.unlink(tmp_path)
            result.metadata['dxf_version'] = doc.dxfversion
            result.metadata['encoding'] = doc.encoding

            # 提取 layers 和 entities（ezdxf 可能对不规范数据报验证错误，逐个 try/except）
            try:
                self._extract_layers(doc, result)
            except Exception as e:
                result.errors.append(f"Layer extraction warning: {str(e)[:100]}")
            try:
                self._extract_entities(doc, result)
            except Exception as e:
                result.errors.append(f"Entity extraction warning: {str(e)[:100]}")
            result.success = True

        except Exception as e:
            result.errors.append(f"DXF parsing error: {str(e)}")

        return result

    def _extract_layers(self, doc, result: ParseResult):
        try:
            for layer in doc.layers:
                result.layers.append(LayerInfo(
                    name=layer.dxf.name,
                    color=str(layer.color) if hasattr(layer, 'color') else None,
                    line_type=layer.dxf.linetype if hasattr(layer.dxf, 'linetype') else None
                ))
        except Exception as e:
            result.errors.append(f"Layer extraction error: {str(e)}")

    def _extract_entities(self, doc, result: ParseResult):
        try:
            msp = doc.modelspace()
            entity_types: Set[str] = set()
            text_entities: List[EntityInfo] = []
            error_entities = 0

            for entity in msp:
                try:
                    entity_type = entity.dxftype()
                    entity_types.add(entity_type)

                    ent_info = EntityInfo(
                        type=entity_type,
                        layer=entity.dxf.layer if hasattr(entity.dxf, 'layer') else '0'
                    )

                    if entity_type in ('TEXT', 'MTEXT') and hasattr(entity, 'text'):
                        ent_info.text = entity.text
                        text_entities.append(ent_info)

                    ent_info.geometry = self._get_geometry(entity)
                    result.entities.append(ent_info)
                except Exception:
                    error_entities += 1

            if text_entities:
                result.raw_text = "\n".join(
                    f"[{e.layer}] {e.text}" for e in text_entities if e.text
                )

            result.metadata['entity_types'] = sorted(entity_types)
            result.metadata['text_entity_count'] = len(text_entities)
            if error_entities:
                result.metadata['error_entities'] = error_entities

        except Exception as e:
            result.errors.append(f"Entity extraction error: {str(e)}")

    def _get_geometry(self, entity) -> dict:
        geo = {}
        try:
            dxf = entity.dxf
            if hasattr(dxf, 'insert'):
                geo['insert'] = {'x': dxf.insert.x, 'y': dxf.insert.y}
            if hasattr(dxf, 'start') and hasattr(dxf, 'end'):
                geo['start'] = {'x': dxf.start.x, 'y': dxf.start.y}
                geo['end'] = {'x': dxf.end.x, 'y': dxf.end.y}
            if hasattr(dxf, 'center'):
                geo['center'] = {'x': dxf.center.x, 'y': dxf.center.y}
            if hasattr(dxf, 'radius'):
                geo['radius'] = dxf.radius
            if hasattr(dxf, 'height'):
                geo['height'] = dxf.height
            if hasattr(dxf, 'width'):
                geo['width'] = dxf.width
        except Exception:
            pass
        return geo if geo else None
