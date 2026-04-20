"""
backend/services/pdf_renderer.py
──────────────────────────────────
PDF renderer for artifact system.

Spec: L – Artifact System
Branch: engineering/master-list-closeout

Strategy (in order of availability):
  1. weasyprint — best HTML→PDF fidelity (pip install weasyprint)
  2. reportlab  — programmatic PDF (pip install reportlab)
  3. fpdf2      — lightweight (pip install fpdf2)
  4. fallback   — write raw text with .txt extension (always works)

Output is saved to the artifact storage directory.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ARTIFACT_STORAGE_DIR = os.environ.get("ARTIFACT_STORAGE_DIR", "/tmp/crucibai_artifacts")


class PDFRenderer:
    """Render text / markdown content to a PDF file."""

    async def render(
        self,
        *,
        content: str,
        title: str,
        output_path: Optional[str] = None,
    ) -> str:
        """Render *content* to a PDF and return the file path."""
        os.makedirs(ARTIFACT_STORAGE_DIR, exist_ok=True)
        if output_path is None:
            import uuid
            output_path = os.path.join(ARTIFACT_STORAGE_DIR, f"{uuid.uuid4()}.pdf")

        # Try weasyprint first
        result = await self._try_weasyprint(content, title, output_path)
        if result:
            return result

        # Try reportlab
        result = self._try_reportlab(content, title, output_path)
        if result:
            return result

        # Try fpdf2
        result = self._try_fpdf(content, title, output_path)
        if result:
            return result

        # Fallback: plain text
        txt_path = output_path.replace(".pdf", ".txt")
        Path(txt_path).write_text(f"# {title}\n\n{content}", encoding="utf-8")
        logger.info("[PDFRenderer] fallback to .txt: %s", txt_path)
        return txt_path

    async def _try_weasyprint(self, content: str, title: str, output_path: str) -> Optional[str]:
        try:
            from weasyprint import HTML
            html = self._to_html(content, title)
            HTML(string=html).write_pdf(output_path)
            logger.info("[PDFRenderer] weasyprint: %s", output_path)
            return output_path
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("[PDFRenderer] weasyprint error: %s", exc)
            return None

    def _try_reportlab(self, content: str, title: str, output_path: str) -> Optional[str]:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            c = canvas.Canvas(output_path, pagesize=letter)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(inch, 10 * inch, title[:80])
            c.setFont("Helvetica", 10)
            y = 9.5 * inch
            for line in content.split("\n"):
                if y < inch:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = 10 * inch
                c.drawString(inch, y, line[:110])
                y -= 14
            c.save()
            logger.info("[PDFRenderer] reportlab: %s", output_path)
            return output_path
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("[PDFRenderer] reportlab error: %s", exc)
            return None

    def _try_fpdf(self, content: str, title: str, output_path: str) -> Optional[str]:
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, title[:80], ln=True)
            pdf.set_font("Arial", size=10)
            for line in content.split("\n"):
                pdf.multi_cell(0, 6, line[:200])
            pdf.output(output_path)
            logger.info("[PDFRenderer] fpdf2: %s", output_path)
            return output_path
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("[PDFRenderer] fpdf2 error: %s", exc)
            return None

    def _to_html(self, content: str, title: str) -> str:
        """Convert markdown-ish content to basic HTML for weasyprint."""
        import html
        body_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# "):
                body_lines.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            elif stripped.startswith("## "):
                body_lines.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            elif stripped.startswith("### "):
                body_lines.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            elif stripped.startswith("- "):
                body_lines.append(f"<li>{html.escape(stripped[2:])}</li>")
            elif stripped == "":
                body_lines.append("<br>")
            else:
                body_lines.append(f"<p>{html.escape(stripped)}</p>")
        body = "\n".join(body_lines)
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: sans-serif; margin: 2cm; font-size: 11pt; }}
  h1 {{ font-size: 20pt; }} h2 {{ font-size: 16pt; }} h3 {{ font-size: 13pt; }}
  li {{ margin-left: 1em; }}
</style></head><body>
<h1>{html.escape(title)}</h1>
{body}
</body></html>"""


# Module-level singleton
pdf_renderer = PDFRenderer()
