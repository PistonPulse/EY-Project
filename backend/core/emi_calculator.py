"""
emi_calculator.py
=================

Pure-function module for EMI and loan-repayment computations.

Responsibilities
----------------
- Calculate the Equated Monthly Instalment (EMI) using the standard
  reducing-balance formula.
- Generate a month-by-month **amortization schedule**.
- Compute total interest payable over the loan tenure.
- Provide a quick affordability check against a given monthly income.

Formula
-------
EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)

Where:
  P = Principal loan amount
  r = Monthly interest rate (annual rate / 12 / 100)
  n = Tenure in months
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class AmortizationRow:
    """
    A single row in the amortization schedule.

    Attributes
    ----------
    month : int
        Month number (1-indexed).
    emi : float
        EMI payment for this month (₹).
    principal : float
        Principal component of the EMI (₹).
    interest : float
        Interest component of the EMI (₹).
    balance : float
        Outstanding principal after this payment (₹).
    """

    month: int
    emi: float
    principal: float
    interest: float
    balance: float


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """
    Calculate the EMI for a loan.

    Parameters
    ----------
    principal : float
        Loan principal amount (₹).
    annual_rate : float
        Annual interest rate (e.g., 10.5 for 10.5 %).
    tenure_months : int
        Loan tenure in months.

    Returns
    -------
    float
        Monthly EMI rounded to 2 decimal places.

    Examples
    --------
    >>> calculate_emi(500_000, 10.5, 60)
    10747.05
    """
    if principal <= 0 or tenure_months <= 0:
        return 0.0
    if annual_rate == 0:
        return round(principal / tenure_months, 2)

    monthly_rate = annual_rate / 12 / 100
    emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / (
        (1 + monthly_rate) ** tenure_months - 1
    )
    return round(emi, 2)


def compute_total_interest(principal: float, annual_rate: float, tenure_months: int) -> float:
    """
    Compute the total interest payable over the loan tenure.

    Returns
    -------
    float
        Total interest amount (₹).
    """
    emi = calculate_emi(principal, annual_rate, tenure_months)
    return round(emi * tenure_months - principal, 2)


def generate_amortization_schedule(
    principal: float, annual_rate: float, tenure_months: int
) -> List[AmortizationRow]:
    """
    Generate a month-by-month amortization schedule.

    Returns
    -------
    list[AmortizationRow]
        One entry per month from month 1 to ``tenure_months``.
    """
    schedule: List[AmortizationRow] = []
    monthly_rate = annual_rate / 12 / 100
    emi = calculate_emi(principal, annual_rate, tenure_months)
    balance = principal

    for month in range(1, tenure_months + 1):
        interest = round(balance * monthly_rate, 2)
        principal_component = round(emi - interest, 2)
        balance = round(balance - principal_component, 2)
        schedule.append(
            AmortizationRow(
                month=month,
                emi=emi,
                principal=principal_component,
                interest=interest,
                balance=max(balance, 0.0),
            )
        )

    return schedule


def check_affordability(monthly_income: float, emi: float, max_foir: float = 0.50) -> bool:
    """
    Check if the EMI is affordable given the applicant's income.

    Parameters
    ----------
    monthly_income : float
        Applicant's net monthly income (₹).
    emi : float
        Proposed EMI (₹).
    max_foir : float
        Maximum Fixed Obligation-to-Income Ratio (default 50 %).

    Returns
    -------
    bool
        ``True`` if EMI / income ≤ max_foir.
    """
    if monthly_income <= 0:
        return False
    return (emi / monthly_income) <= max_foir
