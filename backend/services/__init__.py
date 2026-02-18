"""
services
========

External API integration layer for the Agentic Lending Platform.

Each service module is a thin async wrapper around a third-party API,
following a consistent pattern:

1. Accept typed input parameters.
2. Build and sign the HTTP request.
3. Handle retries, timeouts, and error mapping.
4. Return a typed response dataclass.

Modules
-------
- ``crm_service``            — CRM API for lead / customer management.
- ``credit_bureau_service``  — Credit-score and report retrieval.
- ``loan_offer_service``     — Loan-offer generation and comparison.
"""
