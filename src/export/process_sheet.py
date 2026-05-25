import io
import logging

logger = logging.getLogger(__name__)


class ProcessSheetExporter:
    def generate_pdf(self, program: dict) -> bytes:
        content = f"Process Sheet: {program.get('filename', 'Unknown')}\n"
        content += f"Program ID: {program.get('program_id', 'N/A')}\n"
        content += f"G-code lines: {len(program.get('gcode', '').splitlines())}\n"
        logger.warning("PDF export is a stub — install reportlab for real PDFs")
        return content.encode("utf-8")


_exporter = None


def get_exporter() -> ProcessSheetExporter:
    global _exporter
    if _exporter is None:
        _exporter = ProcessSheetExporter()
    return _exporter
