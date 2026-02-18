"""
backend
=======

Production-ready FastAPI backend for the Agentic Lending Platform.

Packages
--------
- orchestration : Master Agent and loan-application state machine.
- agents        : Domain-specific worker agents (sales, verification, underwriting, document, sanction).
- intelligence  : Intent detection and LLM-powered response generation.
- services      : External API integrations (CRM, credit bureau, loan offers).
- core          : Business logic — EMI calculator and underwriting rule engine.
- templates     : Canned response messages and sanction-letter builders.
- utils         : Cross-cutting utilities — validators, structured logging.
"""

__version__ = "0.1.0"
