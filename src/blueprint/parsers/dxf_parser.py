"""
src/blueprint/parsers/dxf_parser.py - DXF图纸解析器

从 blueprint-ai/dxf_parser.py 迁移。
使用ezdxf库，支持DXF R12到DXF2018。
"""

import ezdxf
from typing import List, Set

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
            doc = ezdxf.readfile(dxf_path)
            result.metadata['dxf_version'] = doc.dxfversion
            result.metadata['encoding'] = doc.encoding

            self._extract_layers(doc, result)
            self._extract_entities(doc, result)
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

            for entity in msp:
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

            if text_entities:
                result.raw_text = "\n".join(
                    f"[{e.layer}] {e.text}" for e in text_entities if e.text
                )

            result.metadata['entity_types'] = sorted(entity_types)
            result.metadata['text_entity_count'] = len(text_entities)

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
