"""
response_messages.py
====================

Versioned dictionary of templated chat responses.

Responsibilities
----------------
- Provide deterministic, compliance-reviewed message templates for every
  stage × intent combination.
- Support variable interpolation via Python ``str.format()`` / f-string
  compatible placeholders (e.g., ``{applicant_name}``, ``{emi}``).
- Allow easy A/B testing by swapping template versions.

Usage
-----
::

    from backend.templates.response_messages import get_message

    msg = get_message("lead_capture", "greeting", applicant_name="Rajesh")
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------
# Structure:  MESSAGES[stage][intent] → template string
# Placeholders use ``{key}`` syntax for .format() interpolation.
# ---------------------------------------------------------------------------

MESSAGES: Dict[str, Dict[str, str]] = {
    # ── Lead Capture ────────────────────────────────────────────────────
    "lead_capture": {
        "greeting": (
            "Hello{applicant_name_greeting}! 👋 Welcome to Tata Capital. "
            "I'm your AI lending assistant. How can I help you today?"
        ),
        "ask_name": "To get started, may I know your full name?",
        "ask_loan_type": (
            "Great, {applicant_name}! What type of loan are you looking for? "
            "We offer Personal Loans, Home Loans, and Auto Loans."
        ),
    },

    # ── Product Selection ───────────────────────────────────────────────
    "product_selection": {
        "recommend": (
            "Based on your requirements, I'd recommend our **{product_name}** "
            "with interest rates starting at {min_rate}% p.a."
        ),
        "confirm": "Shall I proceed with the {product_name} application?",
    },

    # ── KYC Verification ───────────────────────────────────────────────
    "kyc_verification": {
        "ask_pan": "Please provide your PAN number for identity verification.",
        "ask_aadhaar": "Now, could you share your Aadhaar number?",
        "verified": "✅ Your identity has been successfully verified!",
        "failed": "❌ We could not verify the provided details. Please double-check and try again.",
    },

    # ── Document Collection ─────────────────────────────────────────────
    "document_collection": {
        "ask_docs": (
            "Please upload the following documents:\n"
            "1️⃣ Salary slips (last 3 months)\n"
            "2️⃣ Bank statement (last 6 months)\n"
            "3️⃣ Address proof"
        ),
        "doc_received": "✅ {doc_name} received and validated.",
        "all_docs_done": "All required documents have been collected. Moving to credit assessment.",
    },

    # ── Underwriting ────────────────────────────────────────────────────
    "underwriting": {
        "in_progress": "Your credit assessment is in progress. This usually takes a few moments…",
        "approved": (
            "🎉 Great news, {applicant_name}! You are eligible for a loan up to "
            "₹{max_amount:,.0f}."
        ),
        "rejected": (
            "We're sorry, {applicant_name}. Based on our current credit policy, "
            "we are unable to approve your application at this time. Reason: {reason}"
        ),
        "referred": (
            "Your application has been referred for additional review. "
            "Our team will get back to you within 24 hours."
        ),
    },

    # ── Loan Offer ──────────────────────────────────────────────────────
    "loan_offer": {
        "present_offer": (
            "Here is your personalised loan offer:\n"
            "💰 Amount: ₹{amount:,.0f}\n"
            "📊 Rate: {rate}% p.a.\n"
            "📅 Tenure: {tenure} months\n"
            "💳 EMI: ₹{emi:,.0f}/month"
        ),
        "accept_offer": "Would you like to accept this offer and proceed to sanction?",
    },

    # ── Sanction ────────────────────────────────────────────────────────
    "sanction": {
        "generating": "Your sanction letter is being prepared…",
        "ready": (
            "✅ Your loan has been sanctioned! The sanction letter has been "
            "generated and is available for download."
        ),
    },

    # ── Generic ─────────────────────────────────────────────────────────
    "generic": {
        "fallback": "I'm sorry, I didn't quite understand that. Could you rephrase?",
        "error": "Oops! Something went wrong on our end. Please try again shortly.",
        "goodbye": "Thank you for choosing Tata Capital. Have a great day! 👋",
    },
}


def get_message(stage: str, intent: str, **kwargs: Any) -> str:
    """
    Retrieve and interpolate a response template.

    Parameters
    ----------
    stage : str
        Current application stage (e.g., ``'lead_capture'``).
    intent : str
        Message intent key (e.g., ``'greeting'``).
    **kwargs
        Template variable values for interpolation.

    Returns
    -------
    str
        Formatted message string, or a generic fallback if the key is missing.
    """
    # Add a helper for optional name greeting
    if "applicant_name" in kwargs and "applicant_name_greeting" not in kwargs:
        kwargs["applicant_name_greeting"] = f", {kwargs['applicant_name']}"
    elif "applicant_name_greeting" not in kwargs:
        kwargs["applicant_name_greeting"] = ""

    template = MESSAGES.get(stage, {}).get(intent)
    if template is None:
        return MESSAGES["generic"]["fallback"]

    try:
        return template.format(**kwargs)
    except KeyError:
        return template  # Return unformatted if placeholders are missing
