"""
sanction_agent.py
=================

Production worker agent for **sanction-letter generation and dispatch**
in the lending chatbot.

Covered State
-------------
- ``SANCTION`` — compile approved loan terms, generate a formal sanction
  letter as HTML (PDF-convertible), and present it to the applicant with
  a download link.

Responsibilities
----------------
1. Pull all approved loan parameters from collected session data.
2. Render a professional sanction letter via an enhanced HTML template that
   includes:
   - Applicant name and reference number
   - Approved amount, EMI, tenure, interest rate
   - Processing fee
   - Decision summary with underwriting rationale
   - Terms & conditions
   - Amortization schedule preview (first 6 months + last month)
3. Write the HTML file to disk (ready for PDF conversion).
4. Return the file path and a congratulatory chat message.

Design Principles
-----------------
- **Dynamic HTML template** — all fields are parameterised; the template
  is self-contained with inline CSS for portable rendering.
- **PDF-ready** — the HTML output can be passed to WeasyPrint / Puppeteer
  for PDF conversion. A fallback ``to_pdf()`` hook is included.
- **Deterministic** — no AI involved; all values come from prior stages.
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.agents.base_agent import AgentResult, BaseAgent
from backend.core.emi_calculator import (
    calculate_emi,
    compute_total_interest,
    generate_amortization_schedule,
)


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "generated", "sanction_letters")

DEFAULT_RATES: Dict[str, float] = {
    "personal": 12.0, "home": 8.5, "auto": 9.5,
    "business": 14.0, "education": 10.0, "gold": 9.0,
}

PROCESSING_FEE_PCT = 0.02  # 2% of loan amount


# ═══════════════════════════════════════════════════════════════════════════
# Enhanced Sanction Letter HTML Template
# ═══════════════════════════════════════════════════════════════════════════

SANCTION_LETTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Loan Sanction Letter — {reference_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
            margin: 0; padding: 40px 50px;
            color: #2c3e50; background: #fff;
            line-height: 1.6; font-size: 14px;
        }}

        /* Header */
        .header {{
            text-align: center;
            border-bottom: 3px solid #003366;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header .logo {{ font-size: 28px; font-weight: 700; color: #003366; letter-spacing: 1px; }}
        .header .subtitle {{ color: #7f8c8d; font-size: 13px; margin-top: 4px; }}
        .header .ref-line {{ margin-top: 12px; font-size: 12px; color: #95a5a6; }}

        /* Greeting */
        .greeting {{ margin-bottom: 24px; }}
        .greeting p {{ margin-bottom: 8px; }}

        /* Sections */
        .section {{ margin-bottom: 28px; }}
        .section h2 {{
            font-size: 16px; color: #003366;
            border-bottom: 1px solid #dce6f0; padding-bottom: 6px;
            margin-bottom: 14px; text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Tables */
        table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
        th, td {{ padding: 10px 14px; text-align: left; border: 1px solid #e0e6ed; font-size: 13px; }}
        th {{ background-color: #f0f4f8; color: #003366; font-weight: 600; width: 40%; }}
        td {{ color: #2c3e50; }}

        /* Decision badge */
        .badge {{
            display: inline-block; padding: 4px 14px;
            border-radius: 4px; font-weight: 600;
            font-size: 13px; text-transform: uppercase;
        }}
        .badge-approved {{ background: #d4edda; color: #155724; }}
        .badge-conditional {{ background: #fff3cd; color: #856404; }}

        /* Amortization table */
        .amort-table th {{ font-size: 12px; }}
        .amort-table td {{ font-size: 12px; text-align: right; }}
        .amort-table td:first-child {{ text-align: center; }}

        /* T&C */
        .terms ol {{ padding-left: 20px; }}
        .terms li {{ margin-bottom: 6px; font-size: 13px; color: #555; }}

        /* Signature */
        .signature {{ margin-top: 50px; }}
        .signature .sign-line {{ border-top: 1px solid #333; width: 200px; margin-top: 40px; padding-top: 6px; }}

        /* Footer */
        .footer {{
            margin-top: 40px; padding-top: 16px;
            border-top: 1px solid #dce6f0;
            text-align: center; font-size: 11px;
            color: #aaa;
        }}

        @media print {{
            body {{ margin: 20px; padding: 20px; }}
            .footer {{ position: fixed; bottom: 20px; width: 100%; }}
        }}
    </style>
</head>
<body>

    <!-- Header -->
    <div class="header">
        <div class="logo">TATA CAPITAL</div>
        <div class="subtitle">Financial Services Limited</div>
        <div class="ref-line">
            Ref: <strong>{reference_number}</strong> &nbsp;|&nbsp;
            Date: <strong>{sanction_date}</strong>
        </div>
    </div>

    <!-- Greeting -->
    <div class="greeting">
        <p>Dear <strong>{applicant_name}</strong>,</p>
        <p>
            We are pleased to inform you that your loan application has been
            <span class="badge {badge_class}">{verdict_display}</span>
            subject to the terms and conditions outlined below.
        </p>
    </div>

    <!-- Loan Details -->
    <div class="section">
        <h2>Loan Details</h2>
        <table>
            <tr><th>Loan Type</th><td>{loan_type}</td></tr>
            <tr><th>Sanctioned Amount</th><td>₹{loan_amount}</td></tr>
            <tr><th>Interest Rate</th><td>{interest_rate}% p.a.</td></tr>
            <tr><th>Tenure</th><td>{tenure_months} months ({tenure_years})</td></tr>
            <tr><th>Monthly EMI</th><td>₹{emi}</td></tr>
            <tr><th>Total Interest Payable</th><td>₹{total_interest}</td></tr>
            <tr><th>Total Repayment</th><td>₹{total_repayment}</td></tr>
            <tr><th>Processing Fee (2%)</th><td>₹{processing_fee}</td></tr>
        </table>
    </div>

    <!-- Decision Summary -->
    <div class="section">
        <h2>Decision Summary</h2>
        <table>
            <tr><th>Credit Score</th><td>{credit_score}</td></tr>
            <tr><th>Monthly Income</th><td>₹{monthly_income}</td></tr>
            <tr><th>Existing Obligations</th><td>₹{existing_emi}</td></tr>
            <tr><th>Debt-to-Income Ratio</th><td>{dti_ratio}</td></tr>
            <tr><th>EMI / Income Ratio</th><td>{emi_income_ratio}</td></tr>
            <tr><th>Employment Type</th><td>{employment_type}</td></tr>
            <tr><th>Underwriting Verdict</th><td><span class="badge {badge_class}">{verdict_display}</span></td></tr>
        </table>
        {decision_reasons_html}
    </div>

    <!-- Amortization Preview -->
    <div class="section">
        <h2>Repayment Schedule (Preview)</h2>
        <table class="amort-table">
            <thead>
                <tr>
                    <th>Month</th><th>EMI (₹)</th><th>Principal (₹)</th>
                    <th>Interest (₹)</th><th>Balance (₹)</th>
                </tr>
            </thead>
            <tbody>
                {amortization_rows}
            </tbody>
        </table>
        <p style="font-size:12px;color:#888;margin-top:6px;">
            * Showing first 6 months and last month. Full schedule available on request.
        </p>
    </div>

    <!-- Terms & Conditions -->
    <div class="section terms">
        <h2>Terms &amp; Conditions</h2>
        <ol>
            <li>This sanction letter is valid for <strong>30 days</strong> from the date of issuance.</li>
            <li>Disbursement is subject to completion of all required documentation and verification.</li>
            <li>The borrower must maintain a satisfactory credit record during the loan tenure.</li>
            <li>Prepayment / foreclosure charges may apply as per prevailing policy.</li>
            <li>The interest rate is subject to periodic review as per RBI guidelines.</li>
            <li>Any change in employment or income must be reported within 30 days.</li>
            <li>Insurance on the loan amount is recommended but not mandatory.</li>
        </ol>
    </div>

    <!-- Signature -->
    <div class="signature">
        <div class="sign-line">
            Authorized Signatory<br>
            <strong>Tata Capital Financial Services</strong>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        <p>This is a system-generated document. No physical signature is required.</p>
        <p>Tata Capital Financial Services Ltd. | CIN: U65990MH2010PLC201327</p>
        <p>Generated on {generation_timestamp}</p>
    </div>

</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _fmt(n: float) -> str:
    """Indian-style number formatting."""
    if n >= 1_00_00_000:
        return f"{n / 1_00_00_000:,.2f} Cr"
    if n >= 1_00_000:
        return f"{n / 1_00_000:,.2f} L"
    return f"{n:,.0f}"


def _generate_ref(session_id: str) -> str:
    """Produce a unique reference number from the session ID."""
    short = hashlib.sha256(session_id.encode()).hexdigest()[:8].upper()
    return f"SL-{date.today().strftime('%Y%m%d')}-{short}"


def _tenure_display(months: int) -> str:
    """Human-readable tenure display."""
    years = months // 12
    rem = months % 12
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if rem:
        parts.append(f"{rem} month{'s' if rem > 1 else ''}")
    return " ".join(parts) if parts else f"{months} months"


def _build_amort_rows(principal: float, rate: float, tenure: int) -> str:
    """Build HTML table rows for the amortization preview."""
    schedule = generate_amortization_schedule(principal, rate, tenure)

    # Show first 6 + last month
    preview: List[Dict] = []
    if len(schedule) <= 7:
        preview = schedule
    else:
        preview = schedule[:6]
        preview.append(schedule[-1])

    rows: List[str] = []
    for entry in preview:
        month = entry.get("month", 0)
        emi_val = entry.get("emi", 0)
        princ = entry.get("principal", entry.get("principal_component", 0))
        interest = entry.get("interest", entry.get("interest_component", 0))
        balance = entry.get("balance", entry.get("remaining_balance", 0))
        rows.append(
            f"<tr>"
            f"<td>{month}</td>"
            f"<td>{emi_val:,.0f}</td>"
            f"<td>{princ:,.0f}</td>"
            f"<td>{interest:,.0f}</td>"
            f"<td>{balance:,.0f}</td>"
            f"</tr>"
        )
        # Separator row if we skipped months
        if month == 6 and len(schedule) > 7:
            rows.append(
                '<tr><td colspan="5" style="text-align:center;color:#aaa;font-size:11px;">'
                f'… months 7–{len(schedule) - 1} …</td></tr>'
            )

    return "\n".join(rows)


def _build_reasons_html(reasons: List[str]) -> str:
    """Build an HTML list of decision reasons."""
    if not reasons:
        return ""
    items = "".join(f"<li>{r}</li>" for r in reasons)
    return f'<ul style="margin-top:10px;padding-left:20px;font-size:13px;color:#555;">{items}</ul>'


def _render_letter(collected: Dict, session_id: str) -> Tuple[str, Dict[str, Any]]:
    """
    Render the full sanction letter HTML from collected session data.

    Returns (html_string, metadata_dict).
    """
    name = collected.get("applicant_name", "Valued Customer")
    purpose = collected.get("loan_purpose", "personal")
    amount = float(collected.get("loan_amount", 0))
    tenure = int(collected.get("selected_tenure", 60))
    rate = DEFAULT_RATES.get(purpose, 12.0)
    rate = float(collected.get("indicative_rate", rate))

    emi = calculate_emi(amount, rate, tenure)
    total_interest = compute_total_interest(amount, rate, tenure)
    total_repayment = round(amount + total_interest, 2)
    processing_fee = round(amount * PROCESSING_FEE_PCT, 2)

    credit_score = collected.get("credit_score", "N/A")
    income = float(collected.get("monthly_income", 0))
    existing_emi = float(collected.get("existing_emi", 0))
    emp_type = collected.get("employment_type", "salaried")

    # Decision info
    uw = collected.get("underwriting_details", {})
    verdict = uw.get("verdict", collected.get("underwriting_decision", "approved"))
    reasons = uw.get("reasons", [])
    dti = uw.get("dti_ratio", 0)
    emi_ratio = uw.get("emi_to_income", 0)

    ref = _generate_ref(session_id)
    sanction_date = date.today().strftime("%d %B %Y")
    timestamp = datetime.now().strftime("%d %B %Y, %I:%M %p IST")

    badge_class = "badge-approved" if verdict == "approved" else "badge-conditional"
    verdict_display = "Approved" if verdict == "approved" else "Conditionally Approved"

    html = SANCTION_LETTER_HTML.format(
        reference_number=ref,
        sanction_date=sanction_date,
        applicant_name=name,
        loan_type=purpose.title(),
        loan_amount=f"{amount:,.0f}",
        interest_rate=rate,
        tenure_months=tenure,
        tenure_years=_tenure_display(tenure),
        emi=f"{emi:,.0f}",
        total_interest=f"{total_interest:,.0f}",
        total_repayment=f"{total_repayment:,.0f}",
        processing_fee=f"{processing_fee:,.0f}",
        credit_score=credit_score,
        monthly_income=f"{income:,.0f}",
        existing_emi=f"{existing_emi:,.0f}",
        dti_ratio=f"{dti:.1%}" if isinstance(dti, float) else str(dti),
        emi_income_ratio=f"{emi_ratio:.1%}" if isinstance(emi_ratio, float) else str(emi_ratio),
        employment_type=emp_type.replace("_", "-").title(),
        verdict_display=verdict_display,
        badge_class=badge_class,
        decision_reasons_html=_build_reasons_html(reasons),
        amortization_rows=_build_amort_rows(amount, rate, tenure),
        generation_timestamp=timestamp,
    )

    meta = {
        "reference_number": ref,
        "sanction_date": sanction_date,
        "applicant_name": name,
        "loan_type": purpose,
        "loan_amount": amount,
        "interest_rate": rate,
        "tenure_months": tenure,
        "emi": emi,
        "total_interest": total_interest,
        "total_repayment": total_repayment,
        "processing_fee": processing_fee,
        "verdict": verdict,
    }

    return html, meta


def _save_letter(html: str, ref: str) -> str:
    """Write the sanction letter HTML to disk."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"{ref}.html"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return filepath


# ═══════════════════════════════════════════════════════════════════════════
# Chat Response Templates
# ═══════════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, str] = {

    "sanction_generated": (
        "🎉 **Congratulations, {name}!**\n\n"
        "Your **{loan_type} Loan** has been sanctioned! 🎊\n\n"
        "📄 **Sanction Letter Details:**\n\n"
        "| Detail | Value |\n"
        "|--------|-------|\n"
        "| Reference | {ref} |\n"
        "| Amount | ₹{amount_fmt} |\n"
        "| Interest Rate | {rate}% p.a. |\n"
        "| Tenure | {tenure} months ({tenure_display}) |\n"
        "| Monthly EMI | ₹{emi_fmt} |\n"
        "| Total Interest | ₹{interest_fmt} |\n"
        "| Processing Fee | ₹{fee_fmt} |\n\n"
        "📋 **Decision Summary:**\n"
        "• Credit Score: **{credit_score}**\n"
        "• DTI Ratio: **{dti}**\n"
        "• Verdict: **{verdict_display}** ✅\n\n"
        "📥 Your sanction letter has been generated.\n"
        "File: `{filename}`\n\n"
        "🏦 _This is a system-generated sanction letter from Tata Capital._\n\n"
        "Thank you for choosing Tata Capital! 🙏"
    ),

    "missing_data": (
        "⚠️ I don't have enough information to generate the sanction letter.\n\n"
        "Missing: {missing_fields}\n\n"
        "Please complete the previous steps first."
    ),

    "already_generated": (
        "📄 Your sanction letter was already generated.\n\n"
        "Reference: **{ref}**\n"
        "File: `{filename}`\n\n"
        "Would you like me to **regenerate** it?"
    ),
}


def _render_template(key: str, **kwargs) -> str:
    tpl = TEMPLATES.get(key, "")
    try:
        return tpl.format(**kwargs)
    except KeyError:
        return tpl


# ═══════════════════════════════════════════════════════════════════════════
# Sanction Agent
# ═══════════════════════════════════════════════════════════════════════════

class SanctionAgent(BaseAgent):
    """
    Generates and dispatches formal loan sanction letters
    with full loan terms, decision summary, and amortization preview.

    Operates during the ``SANCTION`` state.
    """

    def __init__(self) -> None:
        super().__init__(name="sanction")
        # Track generated letters per session
        self._generated: Dict[str, Dict[str, Any]] = {}

    async def process(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AgentResult:
        """Generate the sanction letter and present it to the user."""
        collected = context.get("collected_data", {})
        self.logger.info("SanctionAgent | session=%s", session_id)

        # Check for regeneration request
        if session_id in self._generated:
            normalised = user_message.strip().lower()
            if normalised in ("regenerate", "regen", "new letter", "again"):
                del self._generated[session_id]
            else:
                info = self._generated[session_id]
                return AgentResult(
                    success=True,
                    message=_render_template(
                        "already_generated",
                        ref=info["reference_number"],
                        filename=info["filename"],
                    ),
                    data={},
                )

        # Validate we have minimum required data
        missing = self._check_required_data(collected)
        if missing:
            return AgentResult(
                success=False,
                message=_render_template(
                    "missing_data",
                    missing_fields=", ".join(missing),
                ),
                data={},
                errors=[f"Missing fields: {', '.join(missing)}"],
            )

        # Render and save the letter
        html, meta = _render_letter(collected, session_id)
        filepath = _save_letter(html, meta["reference_number"])
        filename = os.path.basename(filepath)
        meta["filename"] = filename
        meta["filepath"] = filepath

        # Track it
        self._generated[session_id] = meta

        # Build the chat response
        uw = collected.get("underwriting_details", {})
        dti = uw.get("dti_ratio", 0)
        verdict = uw.get("verdict", collected.get("underwriting_decision", "approved"))
        verdict_display = "Approved" if verdict == "approved" else "Conditionally Approved"

        return AgentResult(
            success=True,
            message=_render_template(
                "sanction_generated",
                name=meta["applicant_name"],
                loan_type=meta["loan_type"].title(),
                ref=meta["reference_number"],
                amount_fmt=_fmt(meta["loan_amount"]),
                rate=meta["interest_rate"],
                tenure=meta["tenure_months"],
                tenure_display=_tenure_display(meta["tenure_months"]),
                emi_fmt=_fmt(meta["emi"]),
                interest_fmt=_fmt(meta["total_interest"]),
                fee_fmt=_fmt(meta["processing_fee"]),
                credit_score=collected.get("credit_score", "N/A"),
                dti=f"{dti:.1%}" if isinstance(dti, float) else str(dti),
                verdict_display=verdict_display,
                filename=filename,
            ),
            data={
                "sanction_letter_generated": True,
                "sanction_reference": meta["reference_number"],
                "sanction_letter_path": filepath,
                "sanction_letter_filename": filename,
                "loan_sanctioned": True,
            },
        )

    @staticmethod
    def _check_required_data(collected: Dict) -> List[str]:
        """Check that we have minimum required fields for letter generation."""
        required = {
            "applicant_name": "Applicant Name",
            "loan_amount": "Loan Amount",
            "loan_purpose": "Loan Purpose",
        }
        missing = []
        for key, label in required.items():
            if not collected.get(key):
                missing.append(label)
        return missing
