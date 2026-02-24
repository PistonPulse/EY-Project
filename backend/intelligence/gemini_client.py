"""
gemini_client.py
================

Gemini Flash Convers-AI layer for the Agentic Lending Platform.

This module provides:
- Hesitation reassurance
- Affordability persuasion
- Financial concept explanation
- Recovery from user confusion

While ensuring:
- Deterministic underwriting integrity (no decisions)
- Hallucination prevention (financial numbers blocked)
- Compliance safety (post-response sanitiser)
- Low latency (timeout + fallback)
- API quota efficiency (only invoked when needed)

Architecture
------------
::

    User Message  →  Intent Detection  →  Master Agent
                                              │
                                      Deterministic Agents
                                              │
                                  Optional Gemini Layer ←── maybe_use_ai()
                                              │
                                      Safe conversational reply

Gemini is called ONLY for conversational intents (hesitation, affordability,
rate queries, tenure queries, EMI explanations).  All underwriting, KYC,
document, and sanction stages bypass Gemini entirely.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ── Optional: google-generativeai SDK ───────────────────────────────────
_HAS_GENAI = False
_genai = None

try:
    import google.generativeai as genai
    _HAS_GENAI = True
    _genai = genai
except ImportError:
    logger.warning(
        "google-generativeai not installed — "
        "Gemini client will use fallback responses only. "
        "Install with: pip install google-generativeai"
    )

# ── Optional: Groq SDK (fallback LLM) ──────────────────────────────────
_HAS_GROQ = False
_groq_client = None

try:
    from groq import Groq
    _HAS_GROQ = True
    logger.info("Groq SDK available — will use as Gemini fallback.")
except ImportError:
    logger.info(
        "groq SDK not installed — Groq fallback disabled. "
        "Install with: pip install groq"
    )

# ── httpx for Local LLM calls ──────────────────────────────────────────
_HAS_HTTPX = False
try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    logger.info(
        "httpx not installed — Local LLM fallback disabled. "
        "Install with: pip install httpx"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Role Prompts (GEMS)
# ═══════════════════════════════════════════════════════════════════════════

# 🟢 Sales Advisor Role — for hesitation and affordability concerns
SALES_ADVISOR_PROMPT = """
You are a professional NBFC loan advisor.

Guide users politely.
Reassure hesitant customers.
Encourage without pressure.

STRICT RULES:
- never promise approval
- never generate EMI, rates, loan limits, or credit scores
- only explain numbers provided in context
- keep responses under 60 words
"""

# 🔵 Financial Explainer Role — for rate, tenure, and EMI concept queries
FINANCIAL_EXPLAINER_PROMPT = """
Explain loan and EMI concepts in simple language.

RULES:
- do not provide approvals
- do not generate financial numbers
- keep explanations short and clear
- keep responses under 60 words
"""

# 🟡 Recovery Role — for confusion, off-topic, and unexpected input
RECOVERY_PROMPT = """
The user has asked an off-topic question, is confused, or has provided an unexpected input.

Your job:
1. STRICTLY REFUSE to answer any questions that are not related to Tata Capital, personal loans, or finance.
2. Do NOT say you are happy to help with their unrelated question.
3. Politely explain that as a Tata Capital loan assistant, your expertise is strictly limited to personal loans.
4. Firmly guide them back to the loan application.

RULES:
- NEVER answer general knowledge, geography, coding, or off-topic queries.
- Keep the tone polite but very firm about your domain boundaries.
- if you know the current stage from context, ask them exactly what is needed next.
- keep responses under 60 words.
"""


# ═══════════════════════════════════════════════════════════════════════════
# Intent → Role Routing Map
# ═══════════════════════════════════════════════════════════════════════════

INTENT_ROLE_MAP: Dict[str, str] = {
    "hesitation":             "sales_advisor",
    "emi_affordability":      "sales_advisor",
    "interest_rate_question": "financial_explainer",
    "tenure_question":        "financial_explainer",
    "ask_emi":                "financial_explainer",
    "general_query":          "recovery",
    "unknown":                "recovery",
}

ROLE_PROMPTS: Dict[str, str] = {
    "sales_advisor":       SALES_ADVISOR_PROMPT,
    "financial_explainer": FINANCIAL_EXPLAINER_PROMPT,
    "recovery":            RECOVERY_PROMPT,
}


# ═══════════════════════════════════════════════════════════════════════════
# Fallback Responses (when API is unavailable / times out)
# ═══════════════════════════════════════════════════════════════════════════

FALLBACK_RESPONSES: Dict[str, str] = {
    "hesitation": (
        "I completely understand — take your time! There's absolutely no rush "
        "or obligation here. Whenever you're ready, I'm here to help. 😊"
    ),
    "emi_affordability": (
        "I hear you — affordability is really important. Let me show you "
        "some alternative options that might work better for your budget."
    ),
    "interest_rate_question": (
        "Great question! Your interest rate depends on your credit profile. "
        "Let me pull up your personalised rate from our system."
    ),
    "tenure_question": (
        "We have multiple tenure options available! Let me show you the "
        "different plans with their corresponding monthly payments."
    ),
    "ask_emi": (
        "EMI stands for Equated Monthly Instalment — it's the fixed amount "
        "you pay each month. Let me calculate the exact figure for you."
    ),
    "general_query": (
        "I'd be happy to help! Let's get back on track with your loan "
        "application. What would you like to know?"
    ),
    "unknown": (
        "No worries! I'm here to help with your loan application. "
        "Let me know if you have any questions, or we can continue "
        "where we left off. 😊"
    ),
    "default": (
        "I understand your concern. Let me guide you with the best "
        "available options."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# Response Sanitiser (Compliance Safety — STEP 6)
# ═══════════════════════════════════════════════════════════════════════════

def sanitize(text: str) -> str:
    """
    Strip any accidentally generated financial numbers from the LLM
    response and replace with safe placeholders.

    Catches:
    - ₹ amounts  (₹5,00,000 / Rs. 50000)
    - Percentages (10.5%, 12 percent)
    - 3-digit credit scores (750, 820)
    - EMI amounts ("EMI of 12000")
    - Approximate figures ("approximately ₹5 lakh")
    """
    # ₹ / Rs. / INR amounts
    text = re.sub(r'₹\s?\d[\d,]*(?:\.\d+)?', '[calculated by system]', text)
    text = re.sub(r'\bRs\.?\s?\d[\d,]*(?:\.\d+)?', '[calculated by system]', text, flags=re.IGNORECASE)
    text = re.sub(r'\bINR\s?\d[\d,]*(?:\.\d+)?', '[calculated by system]', text, flags=re.IGNORECASE)

    # Percentages
    text = re.sub(r'\d+\.?\d*\s*(%|percent|per\s*cent)', '[rate determined by system]', text, flags=re.IGNORECASE)

    # Credit scores (standalone 3-digit numbers in score context)
    text = re.sub(r'\b(cibil|credit\s*score|score)\b.*?\b\d{3}\b', '[score determined by system]', text, flags=re.IGNORECASE)

    # EMI amounts
    text = re.sub(r'\bEMI\b.*?\b\d[\d,]+', '[EMI calculated by system]', text, flags=re.IGNORECASE)

    # Approximate figures
    text = re.sub(
        r'\b(approximately|approx|around|roughly|about|estimated?)\s*[₹]?\s*\d[\d,]*',
        '[calculated by system]', text, flags=re.IGNORECASE
    )

    return text.strip()


# ═══════════════════════════════════════════════════════════════════════════
# Fallback Response (STEP 7)
# ═══════════════════════════════════════════════════════════════════════════

def fallback_response(intent: str = "default") -> str:
    """Return a deterministic fallback response for the given intent."""
    return FALLBACK_RESPONSES.get(intent, FALLBACK_RESPONSES["default"])


# ═══════════════════════════════════════════════════════════════════════════
# Gemini Model Initialisation (STEP 4)
# ═══════════════════════════════════════════════════════════════════════════

_model = None


def _get_model():
    """Lazy-initialise the Gemini model."""
    global _model
    if _model is not None:
        return _model

    if not _HAS_GENAI:
        logger.warning("Gemini SDK not available — cannot initialise model.")
        return None

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — using fallback responses only.")
        return None

    try:
        _genai.configure(api_key=api_key)
        _model = _genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
        logger.info(
            "Gemini model initialised | model=%s timeout=%ds max_tokens=%d temp=%.1f",
            settings.GEMINI_MODEL_NAME,
            settings.GEMINI_TIMEOUT_SECONDS,
            settings.GEMINI_MAX_TOKENS,
            settings.GEMINI_TEMPERATURE,
        )
        return _model
    except Exception as exc:
        logger.error("Failed to initialise Gemini model: %s", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Groq Fallback Client (STEP 4b)
# ═══════════════════════════════════════════════════════════════════════════

def _get_groq_client():
    """Lazy-initialise the Groq client."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client

    if not _HAS_GROQ:
        return None

    api_key = settings.GROQ_API_KEY
    if not api_key:
        logger.info("GROQ_API_KEY not set — Groq fallback disabled.")
        return None

    try:
        _groq_client = Groq(api_key=api_key)
        logger.info(
            "Groq client initialised | model=%s timeout=%ds",
            settings.GROQ_MODEL_NAME,
            settings.GROQ_TIMEOUT_SECONDS,
        )
        return _groq_client
    except Exception as exc:
        logger.error("Failed to initialise Groq client: %s", exc)
        return None


def _generate_groq_response(
    role_prompt: str,
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a response using Groq (LLaMA 3.1) as fallback.
    Uses OpenAI-compatible chat completions API.

    Returns sanitised response or empty string on failure.
    """
    client = _get_groq_client()
    if client is None:
        return ""

    # Build context block
    ctx_block = ""
    if context:
        safe_keys = {
            "applicant_name", "stage", "loan_type", "employment_type",
            "city", "purpose", "previous_agent_message",
        }
        ctx_lines = [f"- {k}: {v}" for k, v in context.items() if k in safe_keys]
        if ctx_lines:
            ctx_block = "\n[CONTEXT]\n" + "\n".join(ctx_lines)

    try:
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": role_prompt},
                {"role": "user", "content": f"{ctx_block}\n\n{user_message}"},
            ],
            temperature=settings.GEMINI_TEMPERATURE,
            max_tokens=settings.GEMINI_MAX_TOKENS,
        )

        text = completion.choices[0].message.content
        if text:
            logger.info("Groq response generated successfully (fallback).")
            return sanitize(text)

        return ""

    except Exception as exc:
        logger.error("Groq API error: %s", exc)
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# Local LLM Client (STEP 4c) — Ollama / LM Studio / LocalAI
# ═══════════════════════════════════════════════════════════════════════════

def _generate_local_llm_response(
    role_prompt: str,
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a response using a local LLM via OpenAI-compatible HTTP API.

    Works with Ollama (default), LM Studio, LocalAI, or any server
    that exposes ``/v1/chat/completions``.

    Returns sanitised response or empty string on failure.
    """
    if not _HAS_HTTPX:
        return ""

    if not settings.LOCAL_LLM_ENABLED:
        return ""

    base_url = settings.LOCAL_LLM_URL.rstrip("/")
    model = settings.LOCAL_LLM_MODEL

    # Build context block
    ctx_block = ""
    if context:
        safe_keys = {
            "applicant_name", "stage", "loan_type", "employment_type",
            "city", "purpose", "previous_agent_message",
        }
        ctx_lines = [f"- {k}: {v}" for k, v in context.items() if k in safe_keys]
        if ctx_lines:
            ctx_block = "\n[CONTEXT]\n" + "\n".join(ctx_lines)

    try:
        with httpx.Client(timeout=settings.LOCAL_LLM_TIMEOUT_SECONDS) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": role_prompt},
                        {"role": "user", "content": f"{ctx_block}\n\n{user_message}"},
                    ],
                    "temperature": settings.GEMINI_TEMPERATURE,
                    "max_tokens": settings.GEMINI_MAX_TOKENS,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if text:
                logger.info("Local LLM response generated successfully (model=%s).", model)
                return sanitize(text)

        return ""

    except Exception as exc:
        logger.error("Local LLM error (%s): %s", base_url, exc)
        return ""


# ═══════════════════════════════════════════════════════════════════════════
# Safe Response Generator (STEP 5)
# ═══════════════════════════════════════════════════════════════════════════

def generate_ai_response(
    role_prompt: str,
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a conversational response using Gemini Flash.

    Parameters
    ----------
    role_prompt : str
        System-level role instructions (Sales Advisor / Financial Explainer).
    user_message : str
        The user's raw message.
    context : dict or None
        Optional session context (safe metadata only — no raw financials).

    Returns
    -------
    str
        Sanitised response with no financial numbers.
    """
    model = _get_model()
    if model is None:
        return fallback_response()

    # Build context block (safe metadata only)
    ctx_block = ""
    if context:
        safe_keys = {
            "applicant_name", "stage", "loan_type", "employment_type",
            "city", "purpose", "previous_agent_message",
        }
        ctx_lines = [f"- {k}: {v}" for k, v in context.items() if k in safe_keys]
        if ctx_lines:
            ctx_block = "\n[CONTEXT]\n" + "\n".join(ctx_lines)

    full_prompt = f"{role_prompt}{ctx_block}\n\n[USER MESSAGE]\n{user_message}"

    try:
        import os
        import requests
        
        primary_key = os.getenv("GEMINI_API_KEY")
        fallback_keys_str = os.getenv("GEMINI_FALLBACK_KEYS", "")
        fallback_keys = [k.strip() for k in fallback_keys_str.split(",") if k.strip()]
        all_keys = [primary_key] + fallback_keys
        
        for idx, key in enumerate(all_keys):
            if not key:
                continue
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "temperature": settings.GEMINI_TEMPERATURE,
                    "maxOutputTokens": settings.GEMINI_MAX_TOKENS,
                }
            }
            
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=5)
                
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        if content_parts:
                            return sanitize(content_parts[0].get("text", ""))
                elif resp.status_code == 429:
                    logger.warning(f"[API ROTATION] Key {idx+1}/{len(all_keys)} reached rate limit (429)! Rotating...")
                    continue
                elif resp.status_code in (400, 403):
                    logger.warning(f"[API ROTATION] Key {idx+1}/{len(all_keys)} is INVALID or EXPIRED ({resp.status_code})! Rotating...")
                    continue
                else:
                    logger.error(f"Gemini API error (Key {idx+1}): {resp.status_code} - {resp.text}")
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error querying Gemini (Key {idx+1}): {e}")
                continue
                
        logger.warning("All Gemini keys exhausted or failed — trying Groq fallback.")

    except Exception as exc:
        logger.error("Gemini Multi-Key Setup error: %s — trying Groq fallback.", exc)

    # ── Groq fallback ────────────────────────────────────────────────
    groq_response = _generate_groq_response(role_prompt, user_message, context)
    if groq_response:
        return groq_response

    # ── Local LLM fallback ───────────────────────────────────────────
    local_response = _generate_local_llm_response(role_prompt, user_message, context)
    if local_response:
        return local_response

    logger.warning("All AI providers failed — using static fallback.")
    return fallback_response()


async def generate_ai_response_async(
    role_prompt: str,
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Async wrapper for ``generate_ai_response`` with timeout.

    Uses ``asyncio.wait_for`` to enforce the configured timeout.
    Falls back on timeout or error.
    """
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: generate_ai_response(role_prompt, user_message, context),
            ),
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
        )
        return result

    except asyncio.TimeoutError:
        logger.warning(
            "Gemini timed out after %ds — using fallback.",
            settings.GEMINI_TIMEOUT_SECONDS,
        )
        return fallback_response()

    except Exception as exc:
        logger.error("Async Gemini error: %s — using fallback.", exc)
        return fallback_response()


# ═══════════════════════════════════════════════════════════════════════════
# Intent → Role Routing (STEP 8)
# ═══════════════════════════════════════════════════════════════════════════

# Intents that should trigger Gemini (conversational enhancement)
AI_INTENTS = {
    "hesitation",
    "emi_affordability",
    "interest_rate_question",
    "tenure_question",
    "ask_emi",
    "general_query",
    "unknown",
}

# Intents / stages that must NEVER use Gemini (deterministic only)
NO_AI_STAGES = {
    "credit_check",
    "decision",
    "document_upload",
    "sanction",
    "rejection",
    "pan_verification",
    "phone_verification",
    "underwriting"
}


async def maybe_use_ai(
    intent: str,
    user_message: str,
    stage: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Intent → Role router.  Returns an AI response if appropriate,
    or ``None`` to let the deterministic agent handle it.

    Gemini SHOULD be used for:
    ✔ hesitation reassurance
    ✔ EMI affordability concerns
    ✔ financial explanations (rate, tenure, EMI concepts)
    ✔ unexpected free-form questions

    Gemini MUST NOT be used for:
    ❌ EMI calculations
    ❌ underwriting decisions
    ❌ approval / rejection
    ❌ KYC validation
    ❌ document verification

    Parameters
    ----------
    intent : str
        Detected intent label (from intent_detector).
    user_message : str
        The user's raw message.
    stage : str
        Current loan application stage (state machine state).
    context : dict or None
        Session context (safe metadata).

    Returns
    -------
    str or None
        AI-generated response if applicable, else None
        (meaning the deterministic agent response should be used).
    """
    # Never use AI in compliance-critical stages
    if stage.lower() in NO_AI_STAGES:
        logger.info("AI skipped — stage '%s' is deterministic-only.", stage)
        return None

    # Check if this intent should trigger AI
    if intent not in AI_INTENTS:
        return None

    # Get the role for this intent
    role_key = INTENT_ROLE_MAP.get(intent)
    if not role_key:
        return None

    role_prompt = ROLE_PROMPTS.get(role_key 	)
    if not role_prompt:
        return None

    logger.info("AI triggered | intent=%s role=%s stage=%s", intent, role_key, stage)

    # Generate the AI response
    response = await generate_ai_response_async(role_prompt, user_message, context)
    return response


# ═══════════════════════════════════════════════════════════════════════════
# Convenience Exports
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "SALES_ADVISOR_PROMPT",
    "FINANCIAL_EXPLAINER_PROMPT",
    "RECOVERY_PROMPT",
    "generate_ai_response",
    "generate_ai_response_async",
    "maybe_use_ai",
    "sanitize",
    "fallback_response",
    "_generate_groq_response",
    "_generate_local_llm_response",
]
