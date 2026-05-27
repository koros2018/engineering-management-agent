"""
src/blueprint/parsers/pdf_parser.py - PDF图纸解析器

从 blueprint-ai/pdf_parser.py 迁移。
支持: 文本型PDF直接提取 + 扫描型PDF OCR识别
"""

import fitz  # PyMuPDF
import subprocess
import os
import tempfile
import json

from ..types import ParseResult, FileType, EntityInfo


class PDFParser:
    """PDF图纸解析器"""

    def __init__(self, use_ocr: bool = True, dpi: int = 300):
        self.use_ocr = use_ocr
        self.dpi = dpi

    def parse(self, pdf_path: str) -> ParseResult:
        result = ParseResult(
            success=False,
            file_path=pdf_path,
            file_type=FileType.PDF
        )

        try:
            doc = fitz.open(pdf_path)
            result.metadata['page_count'] = doc.page_count
            result.metadata['dpi'] = self.dpi

            all_text = []
            ocr_confidences = []

            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()

                if text and text.strip():
                    all_text.append(f"--- Page {page_num + 1} ---\n{text}")
                    result.metadata[f'page_{page_num}_has_text'] = True
                elif self.use_ocr:
                    result.metadata[f'page_{page_num}_has_text'] = False
                    ocr_text, confidence = self._ocr_page(page)
                    if ocr_text:
                        all_text.append(f"--- Page {page_num + 1} (OCR) ---\n{ocr_text}")
                        ocr_confidences.append(confidence)

            result.raw_text = "\n\n".join(all_text)

            if ocr_confidences:
                result.ocr_confidence = sum(ocr_confidences) / len(ocr_confidences)

            self._extract_text_entities(result)
            doc.close()
            result.success = True

        except Exception as e:
            result.errors.append(f"PDF parsing error: {str(e)}")

        return result

    def _ocr_page(self, page) -> tuple:
        """OCR识别单个页面"""
        temp_path = None
        try:
            pix = page.get_pixmap(dpi=self.dpi)
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                temp_path = f.name
                pix.save(temp_path)

            node_script = (
                "const {createWorker} = require('tesseract.js');"
                "(async () => {"
                "  const worker = await createWorker('eng+chi_sim');"
                "  const {data} = await worker.recognize('" + temp_path.replace("\\", "\\\\") + "');"
                "  console.log(JSON.stringify({text: data.text, confidence: data.confidence}));"
                "  await worker.terminate();"
                "})();"
            )

            proc = subprocess.run(
                ['node', '-e', node_script],
                capture_output=True, text=True, timeout=120,
                cwd='/mnt/d/OpenClawDataworkspace/Projects/blueprint-ai'
            )

            if proc.returncode == 0 and proc.stdout.strip():
                ocr_result = json.loads(proc.stdout)
                return ocr_result['text'], ocr_result['confidence']

        except Exception as e:
            pass
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        return "", 0.0

    def _extract_text_entities(self, result: ParseResult):
        """从文本中提取实体"""
        if not result.raw_text:
            return
        for i, line in enumerate(result.raw_text.split('\n')):
            if line.strip():
                result.entities.append(EntityInfo(
                    type="TEXT", layer="0", text=line.strip(),
                    attributes={'line_number': i}
                ))
