"""
validators.py
=============

Input validation helpers for Indian financial identifiers and contact details.

Responsibilities
----------------
- Provide regex-based format validators for PAN, Aadhaar, mobile, email,
  and pincode.
- Return clear ``(is_valid, error_message)`` tuples for use in agent logic.
- Expose Pydantic-compatible field validators for use in request models.

Patterns
--------
- **PAN**    : ``ABCDE1234F`` — 5 letters, 4 digits, 1 letter.
- **Aadhaar**: ``1234 5678 9012`` — 12 digits (spaces optional).
- **Mobile** : ``9876543210`` — 10-digit Indian mobile starting with 6-9.
- **Email**  : Standard RFC-ish pattern.
- **Pincode**: ``110001`` — 6-digit Indian postal code.
"""

from __future__ import annotations

import re
from typing import Tuple

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_PATTERN = re.compile(r"^\d{4}\s?\d{4}\s?\d{4}$")
MOBILE_PATTERN = re.compile(r"^[6-9]\d{9}$")
EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
PINCODE_PATTERN = re.compile(r"^\d{6}$")


def validate_pan(pan: str) -> Tuple[bool, str]:
    """
    Validate an Indian PAN (Permanent Account Number).

    Parameters
    ----------
    pan : str
        PAN string to validate (e.g., ``ABCDE1234F``).

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` if valid; ``(False, reason)`` otherwise.
    """
    pan = pan.strip().upper()
    if not PAN_PATTERN.match(pan):
        return False, f"Invalid PAN format: '{pan}'. Expected format: ABCDE1234F."
    return True, ""


def validate_aadhaar(aadhaar: str) -> Tuple[bool, str]:
    """
    Validate an Indian Aadhaar number (12 digits, spaces optional).

    Parameters
    ----------
    aadhaar : str
        Aadhaar string to validate (e.g., ``1234 5678 9012``).

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` if valid; ``(False, reason)`` otherwise.
    """
    aadhaar = aadhaar.strip()
    if not AADHAAR_PATTERN.match(aadhaar):
        return False, f"Invalid Aadhaar format: '{aadhaar}'. Expected 12 digits."
    # Aadhaar cannot start with 0 or 1
    first_digit = aadhaar.replace(" ", "")[0]
    if first_digit in ("0", "1"):
        return False, "Aadhaar number cannot start with 0 or 1."
    return True, ""


def validate_mobile(mobile: str) -> Tuple[bool, str]:
    """
    Validate a 10-digit Indian mobile number.

    Parameters
    ----------
    mobile : str
        Mobile number string (e.g., ``9876543210``).

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` if valid; ``(False, reason)`` otherwise.
    """
    mobile = mobile.strip().replace("+91", "").replace(" ", "").replace("-", "")
    if not MOBILE_PATTERN.match(mobile):
        return False, f"Invalid mobile number: '{mobile}'. Expected 10 digits starting with 6-9."
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate an email address format.

    Parameters
    ----------
    email : str
        Email address to validate.

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` if valid; ``(False, reason)`` otherwise.
    """
    email = email.strip().lower()
    if not EMAIL_PATTERN.match(email):
        return False, f"Invalid email format: '{email}'."
    return True, ""


def validate_pincode(pincode: str) -> Tuple[bool, str]:
    """
    Validate a 6-digit Indian pincode.

    Parameters
    ----------
    pincode : str
        Pincode string to validate (e.g., ``110001``).

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` if valid; ``(False, reason)`` otherwise.
    """
    pincode = pincode.strip()
    if not PINCODE_PATTERN.match(pincode):
        return False, f"Invalid pincode: '{pincode}'. Expected exactly 6 digits."
    return True, ""
