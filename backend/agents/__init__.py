"""
agents
======

Domain-specific worker agents for the Agentic Lending Platform.

Each agent inherits from :class:`BaseAgent` and encapsulates the business logic
for a single stage of the loan lifecycle — from lead qualification through
sanction-letter dispatch.

Modules
-------
- ``base_agent``          — Abstract base class with ``process()`` contract.
- ``sales_agent``         — Lead qualification and product recommendation.
- ``verification_agent``  — KYC / identity verification workflows.
- ``underwriting_agent``  — Risk assessment and eligibility decisioning.
- ``document_agent``      — Document collection, parsing, and validation.
- ``sanction_agent``      — Sanction-letter generation and dispatch.
"""
