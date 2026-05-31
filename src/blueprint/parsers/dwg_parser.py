"""
src/blueprint/parsers/dwg_parser.py - DWG图纸解析器

从 blueprint-ai/dwg_extractor.py 迁移。
双模式: 二进制字符串提取 + libredwg WASM 降级。
"""

import re
import os
from typing import List, Dict, Set

from ..types import ParseResult, FileType, EntityInfo, LayerInfo


# 字符串分类正则
LAYER_PATTERNS = re.compile(rb'^[A-Z][A-Z0-9_]{1,30}$')
BLOCK_PATTERNS = re.compile(rb'^[A-Z_][A-Z0-9_]{1,40}$')
DIM_STYLE_PATTERNS = re.compile(rb'^ACAD_DSTYLE_')
LTYPE_PATTERNS = re.compile(rb'^ACAD_')


class DWGParser:
    """DWG图纸解析器（二进制字符串提取 + WASM降级）"""

    def parse(self, dwg_path: str) -> ParseResult:
        result = ParseResult(
            success=True,
            file_path=dwg_path,
            file_type=FileType.DWG,
            errors=[]
        )

        size = os.path.getsize(dwg_path)
        result.metadata['file_size'] = size

        try:
            info = self._extract_strings(dwg_path)
            result.metadata['dwg_version'] = info.get('metadata', {}).get('dwg_version', 'unknown')
            result.metadata['layers_count'] = len(info.get('layers', []))
            result.metadata['blocks_count'] = len(info.get('blocks', []))
            result.metadata['company'] = info.get('metadata', {}).get('company', '')
            result.metadata['urls'] = info.get('urls', [])
            result.metadata['phones'] = info.get('phone_numbers', [])

            # 文字内容
            text_content = info.get('text_content', [])
            if text_content:
                filtered = [t for t in text_content if len(t) > 6 and not t.startswith('AcDb') and not t.startswith('@') and not t.startswith('"')]
                result.raw_text = '\n'.join(filtered[:200])

            # 图层
            for layer_name in info.get('layers', []):
                result.layers.append(LayerInfo(name=layer_name, color='', visible=True))

            # 图块列表
            for block_name in info.get('blocks', []):
                result.blocks.append(block_name)

            result.metadata['entity_count'] = info.get('metadata', {}).get('total_strings', 0)

            if info.get('errors'):
                result.errors.extend(info['errors'])

        except Exception as e:
            result.errors.append(f"DWG extraction error: {type(e).__name__}: {str(e)}")

        return result

    def _extract_strings(self, file_path: str) -> Dict:
        with open(file_path, 'rb') as f:
            data = f.read()

        file_size = len(data)
        strings = self._extract_ascii_strings(data)
        categories = self._categorize_strings(strings)
        metadata = self._extract_metadata(data)
        metadata['file_size'] = file_size
        metadata['total_strings'] = len(strings)

        return {
            'success': True,
            'file_path': file_path,
            'metadata': metadata,
            'layers': sorted(set(categories['layers'])),
            'blocks': sorted(set(categories['blocks'])),
            'dim_styles': sorted(set(categories['dim_styles'])),
            'ltypes': sorted(set(categories['ltypes'])),
            'text_content': categories['text_content'][:100],
            'urls': categories['urls'],
            'phone_numbers': categories['phone_numbers'],
        }

    def _extract_ascii_strings(self, data: bytes, min_len: int = 4) -> List[bytes]:
        strings = re.findall(rb'[\x20-\x7E]{%d,}' % min_len, data)
        return [s.strip() for s in strings if len(s.strip()) >= min_len]

    def _categorize_strings(self, strings: List[bytes]) -> Dict[str, List[str]]:
        categories = {
            'layers': [], 'blocks': [], 'dim_styles': [],
            'ltypes': [], 'text_content': [], 'urls': [],
            'phone_numbers': [], 'other': [],
        }
        seen: Set[bytes] = set()
        for s in strings:
            if s in seen:
                continue
            seen.add(s)
            s_str = s.decode('ascii', errors='replace')
            if re.match(rb'^[A-F0-9]+$', s) and len(s) > 12:
                continue
            if re.match(rb'^_+$', s):
                continue
            if LAYER_PATTERNS.match(s) and b'_' not in s[:4]:
                categories['layers'].append(s_str)
            elif s.startswith(b'TCH_') or s.startswith(b'PUB_'):
                categories['blocks'].append(s_str)
            elif DIM_STYLE_PATTERNS.match(s):
                categories['dim_styles'].append(s_str)
            elif LTYPE_PATTERNS.match(s):
                categories['ltypes'].append(s_str)
            elif b'www.' in s or b'http' in s:
                categories['urls'].append(s_str)
            elif re.search(rb'\d{7,}', s):
                phones = re.findall(rb'\d{7,}', s)
                for p in phones:
                    categories['phone_numbers'].append(p.decode())
            else:
                if len(s) >= 5 and s.decode('ascii', errors='replace').isprintable():
                    categories['text_content'].append(s_str)
        return categories

    def _extract_metadata(self, data: bytes) -> Dict:
        meta = {}
        version = data[:20].split(b'\x00')[0]
        if version.startswith(b'AC'):
            meta['dwg_version'] = version.decode('ascii', errors='replace')
        strings = re.findall(rb'(?i)(author|company|copyright)[:\s]+([^\x00\r\n]{3,100})', data)
        for key, value in strings[:5]:
            meta[key.decode().lower()] = value.decode('ascii', errors='replace').strip()
        urls = re.findall(rb'https?://[^\s<>"{}|\\^`\[\]]+', data)
        if urls:
            meta['urls'] = list(set(u.decode('ascii', errors='replace') for u in urls[:10]))
        phones = re.findall(rb'\d{3,4}[-\s]?\d{7,8}', data)
        if phones:
            meta['phone_numbers'] = list(set(p.decode('ascii', errors='replace') for p in phones[:10]))
        return meta
