"""Multi-sheet Excel report mirroring the structure of a real
post-campaign analysis deliverable."""
from __future__ import annotations

import io
from typing import Mapping

import pandas as pd


def build_excel_report(
    campaign_name: str,
    overall: pd.DataFrame,
    segment_breakdowns: Mapping[str, pd.DataFrame],
    engagement_summary: pd.DataFrame,
    daily_engagement: pd.DataFrame,
    ops_efficiency: pd.DataFrame,
    balance_report: pd.DataFrame,
    executive_summary_md: str,
) -> bytes:
    """Build the full Excel workbook in-memory and return its bytes."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        wb = writer.book

        title_fmt = wb.add_format({
            "bold": True, "font_size": 16, "font_color": "#FFFFFF",
            "bg_color": "#7C5CFF", "align": "left", "valign": "vcenter",
        })
        header_fmt = wb.add_format({
            "bold": True, "bg_color": "#161A23", "font_color": "#F5F7FA",
            "border": 1,
        })
        wrap_fmt = wb.add_format({"text_wrap": True, "valign": "top"})

        # ---- Sheet: Executive Summary ----
        ws = wb.add_worksheet("Executive Summary")
        ws.set_column(0, 0, 110)
        ws.set_row(0, 28)
        ws.write(0, 0, f"Campaign: {campaign_name}", title_fmt)
        for i, line in enumerate(executive_summary_md.splitlines(), start=2):
            ws.write(i, 0, line, wrap_fmt)

        # ---- Sheet: Incrementality Summary ----
        overall.to_excel(writer, sheet_name="Incrementality", index=False)
        _format_sheet(writer, "Incrementality", header_fmt)

        # ---- Sheet: Engagement ----
        engagement_summary.to_excel(writer, sheet_name="Engagement", index=False)
        _format_sheet(writer, "Engagement", header_fmt)

        # ---- Sheet: Daily Engagement ----
        daily_engagement.to_excel(writer, sheet_name="Daily Engagement", index=False)
        _format_sheet(writer, "Daily Engagement", header_fmt)

        # ---- Sheet: Ops Efficiency ----
        ops_efficiency.to_excel(writer, sheet_name="Ops Efficiency", index=False)
        _format_sheet(writer, "Ops Efficiency", header_fmt)

        # ---- Sheet: Balance Report ----
        balance_report.to_excel(writer, sheet_name="TVC Balance", index=False)
        _format_sheet(writer, "TVC Balance", header_fmt)

        # ---- One sheet per segment dimension ----
        for dim, sdf in segment_breakdowns.items():
            sheet_name = f"Seg-{dim[:25]}"
            sdf.to_excel(writer, sheet_name=sheet_name, index=False)
            _format_sheet(writer, sheet_name, header_fmt)

    return buf.getvalue()


def _format_sheet(writer, sheet_name: str, header_fmt) -> None:
    ws = writer.sheets[sheet_name]
    df = writer.sheets[sheet_name]
    # set first row formatting and auto column width by best-effort
    ws.set_row(0, 22, header_fmt)
    ws.set_column(0, 50, 22)
