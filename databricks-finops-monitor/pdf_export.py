# =============================================================================
# PDF Export Module for FinOps Monitor
# =============================================================================
# Generates per-tab PDF reports with metrics, charts, and data tables.
# Uses fpdf2 for PDF generation and kaleido for Plotly chart image export.
# =============================================================================

import io
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from fpdf import FPDF


class FinOpsPDFReport(FPDF):
    """Custom PDF class for FinOps Monitor tab reports."""

    def __init__(self, tab_title: str, date_range: str = ""):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.tab_title = tab_title
        self.date_range = date_range
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    def header(self):
        # Logo text
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(41, 98, 255)
        self.cell(0, 10, "Databricks FinOps Monitor", ln=True, align="L")
        # Tab title
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, self.tab_title, ln=True, align="L")
        # Date range and generation time
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        meta = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if self.date_range:
            meta += f"  |  Data Range: {self.date_range}"
        self.cell(0, 6, meta, ln=True, align="L")
        self.ln(4)
        # Separator line
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  Databricks FinOps Monitor",
                  align="C")

    def add_section_title(self, title: str):
        """Add a section heading."""
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(30, 30, 30)
        self.cell(0, 8, title, ln=True)
        self.ln(2)

    def add_metrics_row(self, metrics: Dict[str, str]):
        """Add a row of key metrics as colored boxes."""
        if not metrics:
            return
        n = len(metrics)
        box_w = min(55, (self.w - 20) / n)
        box_h = 20
        start_x = self.get_x()
        start_y = self.get_y()

        for label, value in metrics.items():
            # Box background
            self.set_fill_color(240, 245, 255)
            self.set_draw_color(41, 98, 255)
            self.rect(self.get_x(), self.get_y(), box_w, box_h, style="DF")
            # Value
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(41, 98, 255)
            self.set_xy(self.get_x(), start_y + 2)
            self.cell(box_w, 9, str(value), align="C")
            # Label
            self.set_font("Helvetica", "", 8)
            self.set_text_color(80, 80, 80)
            self.set_xy(self.get_x() - box_w, start_y + 11)
            self.cell(box_w, 6, label, align="C")
            # Move to next box
            self.set_xy(self.get_x() + 3, start_y)

        self.set_xy(start_x, start_y + box_h + 6)

    def add_chart_image(self, fig, width: int = 250, caption: str = ""):
        """Export a Plotly figure as image and embed in PDF."""
        try:
            img_bytes = fig.to_image(format="png", width=1200, height=500,
                                     scale=2, engine="kaleido")
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img_bytes)
                tmp_path = tmp.name

            if caption:
                self.set_font("Helvetica", "I", 9)
                self.set_text_color(80, 80, 80)
                self.cell(0, 5, caption, ln=True)
                self.ln(1)

            # Check if we need a new page
            if self.get_y() + 80 > self.h - 20:
                self.add_page()

            self.image(tmp_path, x=10, w=width)
            self.ln(6)
        except Exception as e:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(200, 50, 50)
            self.cell(0, 5, f"[Chart export failed: {e}]", ln=True)
            self.ln(4)

    def add_dataframe_table(self, df: pd.DataFrame, title: str = "",
                            max_rows: int = 50, col_widths: Optional[List[int]] = None):
        """Render a DataFrame as a PDF table."""
        if df.empty:
            return

        if title:
            self.add_section_title(title)

        df_export = df.head(max_rows).copy()
        cols = list(df_export.columns)
        n_cols = len(cols)

        # Calculate column widths
        available_w = self.w - 20
        if col_widths and len(col_widths) == n_cols:
            widths = col_widths
        else:
            widths = [available_w / n_cols] * n_cols

        # Truncate column widths if total exceeds page
        total_w = sum(widths)
        if total_w > available_w:
            scale = available_w / total_w
            widths = [w * scale for w in widths]

        # Header row
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(41, 98, 255)
        self.set_text_color(255, 255, 255)
        for i, col in enumerate(cols):
            self.cell(widths[i], 6, str(col)[:20], border=1, fill=True, align="C")
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 7)
        self.set_text_color(30, 30, 30)
        for row_idx, (_, row) in enumerate(df_export.iterrows()):
            if self.get_y() + 6 > self.h - 20:
                self.add_page()
                # Re-draw header on new page
                self.set_font("Helvetica", "B", 7)
                self.set_fill_color(41, 98, 255)
                self.set_text_color(255, 255, 255)
                for i, col in enumerate(cols):
                    self.cell(widths[i], 6, str(col)[:20], border=1, fill=True, align="C")
                self.ln()
                self.set_font("Helvetica", "", 7)
                self.set_text_color(30, 30, 30)

            # Alternate row colors
            if row_idx % 2 == 0:
                self.set_fill_color(248, 249, 252)
            else:
                self.set_fill_color(255, 255, 255)

            for i, col in enumerate(cols):
                val = str(row[col]) if pd.notna(row[col]) else ""
                # Truncate long values
                max_chars = max(5, int(widths[i] / 2))
                display_val = val[:max_chars] + ".." if len(val) > max_chars else val
                self.cell(widths[i], 5, display_val, border=1, fill=True, align="C")
            self.ln()

        self.ln(4)
        if len(df) > max_rows:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5, f"Showing {max_rows} of {len(df)} rows. Export CSV for full data.",
                      ln=True)
            self.ln(3)

    def add_text_block(self, text: str, bold: bool = False):
        """Add a paragraph of text."""
        self.set_font("Helvetica", "B" if bold else "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, text)
        self.ln(3)

    def add_key_value_list(self, items: Dict[str, str]):
        """Add a list of key-value pairs."""
        for key, val in items.items():
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(50, 50, 50)
            self.cell(50, 5, f"{key}:")
            self.set_font("Helvetica", "", 9)
            self.set_text_color(30, 30, 30)
            self.cell(0, 5, str(val), ln=True)
        self.ln(3)

    def get_pdf_bytes(self) -> bytes:
        """Return the PDF as bytes for Streamlit download."""
        return bytes(self.output())


def generate_tab_pdf(
    tab_title: str,
    date_range: str = "",
    metrics: Optional[Dict[str, str]] = None,
    figures: Optional[List[Tuple]] = None,
    dataframes: Optional[List[Tuple]] = None,
    text_sections: Optional[List[Tuple]] = None,
) -> bytes:
    """
    Convenience function to generate a complete tab PDF.

    Args:
        tab_title: Name of the tab (e.g., "Job Monitoring")
        date_range: Date range string for the header
        metrics: Dict of {label: value} for the KPI row
        figures: List of (plotly_fig, caption) tuples
        dataframes: List of (df, title, max_rows) tuples
        text_sections: List of (title, text) tuples

    Returns:
        PDF bytes ready for st.download_button
    """
    pdf = FinOpsPDFReport(tab_title=tab_title, date_range=date_range)
    pdf.alias_nb_pages()

    if metrics:
        pdf.add_section_title("Key Metrics")
        pdf.add_metrics_row(metrics)

    if figures:
        pdf.add_section_title("Charts")
        for fig, caption in figures:
            pdf.add_chart_image(fig, caption=caption)

    if text_sections:
        for title, text in text_sections:
            pdf.add_section_title(title)
            pdf.add_text_block(text)

    if dataframes:
        for item in dataframes:
            if len(item) == 3:
                df, title, max_rows = item
            else:
                df, title = item
                max_rows = 50
            pdf.add_dataframe_table(df, title=title, max_rows=max_rows)

    return pdf.get_pdf_bytes()
