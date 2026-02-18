"""
sanction_letter_template.py
===========================

HTML / PDF sanction-letter builder for approved loan applications.

Responsibilities
----------------
- Accept loan terms (amount, rate, tenure, EMI, applicant details).
- Render a professional sanction-letter HTML document using Jinja2 templating.
- Provide a ``to_pdf()`` hook for converting the HTML to a downloadable PDF
  (via WeasyPrint or ReportLab).

Design Notes
------------
- The HTML template is embedded as a module-level string for portability.
  In production, it can be moved to an external ``.html`` template file.
- All monetary values are formatted in Indian numbering (₹ X,XX,XXX).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Embedded HTML Template
# ---------------------------------------------------------------------------

SANCTION_LETTER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Loan Sanction Letter</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
        .header {{ text-align: center; border-bottom: 2px solid #003366; padding-bottom: 16px; }}
        .header h1 {{ color: #003366; margin-bottom: 4px; }}
        .header p {{ color: #666; font-size: 14px; }}
        .section {{ margin: 24px 0; }}
        .section h2 {{ color: #003366; font-size: 18px; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ padding: 10px 14px; text-align: left; border: 1px solid #ddd; }}
        th {{ background-color: #f0f4f8; color: #003366; }}
        .footer {{ margin-top: 40px; font-size: 12px; color: #999; text-align: center; }}
        .signature {{ margin-top: 60px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LOAN SANCTION LETTER</h1>
        <p>Ref: {reference_number} | Date: {sanction_date}</p>
    </div>

    <div class="section">
        <p>Dear <strong>{applicant_name}</strong>,</p>
        <p>
            We are pleased to inform you that your loan application has been
            <strong>sanctioned</strong> subject to the terms and conditions
            outlined below.
        </p>
    </div>

    <div class="section">
        <h2>Loan Details</h2>
        <table>
            <tr><th>Loan Type</th><td>{loan_type}</td></tr>
            <tr><th>Sanctioned Amount</th><td>₹{loan_amount}</td></tr>
            <tr><th>Interest Rate</th><td>{interest_rate}% p.a.</td></tr>
            <tr><th>Tenure</th><td>{tenure_months} months</td></tr>
            <tr><th>EMI</th><td>₹{emi}</td></tr>
            <tr><th>Processing Fee</th><td>₹{processing_fee}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Terms & Conditions</h2>
        <ol>
            <li>This sanction is valid for 30 days from the date of issuance.</li>
            <li>Disbursement is subject to completion of all required documentation.</li>
            <li>The borrower must maintain a satisfactory credit record during the loan tenure.</li>
            <li>Prepayment / foreclosure charges may apply as per the prevailing policy.</li>
        </ol>
    </div>

    <div class="signature">
        <p>Authorized Signatory</p>
        <p><strong>Tata Capital Financial Services</strong></p>
    </div>

    <div class="footer">
        <p>This is a system-generated document. No physical signature is required.</p>
    </div>
</body>
</html>
"""


def render_sanction_letter(
    applicant_name: str,
    loan_type: str,
    loan_amount: float,
    interest_rate: float,
    tenure_months: int,
    emi: float,
    processing_fee: float = 0.0,
    reference_number: Optional[str] = None,
    sanction_date: Optional[str] = None,
) -> str:
    """
    Render the sanction-letter HTML with the given loan details.

    Parameters
    ----------
    applicant_name : str
        Full name of the borrower.
    loan_type : str
        Type of loan (Personal / Home / Auto).
    loan_amount : float
        Sanctioned principal amount (₹).
    interest_rate : float
        Annual interest rate (%).
    tenure_months : int
        Loan tenure in months.
    emi : float
        Monthly EMI (₹).
    processing_fee : float
        One-time processing fee (₹).
    reference_number : str or None
        Unique reference ID. Auto-generated if not provided.
    sanction_date : str or None
        Date string. Defaults to today.

    Returns
    -------
    str
        Rendered HTML string ready for display or PDF conversion.
    """
    if reference_number is None:
        reference_number = f"SL-{date.today().strftime('%Y%m%d')}-001"
    if sanction_date is None:
        sanction_date = date.today().strftime("%d %B %Y")

    logger.info("Rendering sanction letter ref=%s for %s", reference_number, applicant_name)

    return SANCTION_LETTER_HTML.format(
        applicant_name=applicant_name,
        loan_type=loan_type.title(),
        loan_amount=f"{loan_amount:,.0f}",
        interest_rate=interest_rate,
        tenure_months=tenure_months,
        emi=f"{emi:,.0f}",
        processing_fee=f"{processing_fee:,.0f}",
        reference_number=reference_number,
        sanction_date=sanction_date,
    )


def to_pdf(html_content: str, output_path: str) -> str:
    """
    Convert rendered HTML to a PDF file.

    Parameters
    ----------
    html_content : str
        The HTML string (from ``render_sanction_letter``).
    output_path : str
        File path where the PDF will be saved.

    Returns
    -------
    str
        Absolute path to the generated PDF.

    TODO
    ----
    - Integrate WeasyPrint or ReportLab for actual PDF generation.
    """
    logger.info("PDF generation requested → %s (not yet implemented)", output_path)
    # Placeholder — write HTML as-is; replace with PDF lib in production
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path
