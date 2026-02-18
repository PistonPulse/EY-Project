"""
intent_detector.py
==================

Production intent classification engine for user messages.

Detection Strategy (Two-Tier)
-----------------------------
1. **Keyword fallback** (fast path) — regex / keyword rules that fire
   instantly when high-confidence patterns are matched.
2. **Semantic similarity** (deep path) — uses ``sentence-transformers``
   to encode the user message and compare against curated exemplar
   embeddings via cosine similarity.

If ``sentence-transformers`` is not installed, the module gracefully
degrades to keyword-only mode with a warning log.

Supported Intents
-----------------
- ``HESITATION``             — user is unsure, stalling, or expressing doubt.
- ``EMI_AFFORDABILITY``      — concern about EMI being too high.
- ``INTEREST_RATE_QUESTION`` — asking about or negotiating interest rates.
- ``TENURE_QUESTION``        — asking about tenure options / flexibility.
- ``LOAN_INQUIRY``           — general loan product / eligibility queries.
- ``APPLY_LOAN``             — user wants to start a new application.
- ``CHECK_STATUS``           — asking about application progress.
- ``UPLOAD_DOCUMENT``        — intends to upload a document.
- ``ASK_EMI``                — wants EMI / repayment calculation.
- ``GREETING``               — social / greeting messages.
- ``GENERAL_QUERY``          — informational catch-all.
- ``UNKNOWN``                — could not classify with confidence.

Architecture
------------
::

    User Message
        │
        ├─ Tier 1: Keyword / Regex Rules ─── match? → Intent (conf ≥ 0.85)
        │
        └─ Tier 2: Sentence-Transformer
              │
              ├─ encode(message)
              ├─ cosine_similarity vs exemplar bank
              └─ top match above threshold? → Intent (conf = sim score)

Returns an ``Intent`` dataclass with ``intent_type``, ``confidence``,
``raw_text``, and optional ``entities``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ── Optional: sentence-transformers ─────────────────────────────────────
_HAS_TRANSFORMERS = False
_model = None

try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _HAS_TRANSFORMERS = True
except ImportError:
    logger.warning(
        "sentence-transformers not installed — "
        "intent detection will use keyword fallback only."
    )


# ═══════════════════════════════════════════════════════════════════════════
# Intent Enum & Dataclass
# ═══════════════════════════════════════════════════════════════════════════

class IntentType(str, Enum):
    """Recognised user intent categories."""

    HESITATION             = "hesitation"
    EMI_AFFORDABILITY      = "emi_affordability"
    INTEREST_RATE_QUESTION = "interest_rate_question"
    TENURE_QUESTION        = "tenure_question"
    LOAN_INQUIRY           = "loan_inquiry"
    APPLY_LOAN             = "apply_loan"
    CHECK_STATUS           = "check_status"
    UPLOAD_DOCUMENT        = "upload_document"
    ASK_EMI                = "ask_emi"
    GREETING               = "greeting"
    GENERAL_QUERY          = "general_query"
    UNKNOWN                = "unknown"


@dataclass
class Intent:
    """
    Classified intent with confidence metadata.

    Attributes
    ----------
    intent_type : IntentType
        The detected intent category.
    confidence : float
        Confidence score between 0.0 and 1.0.
    raw_text : str
        The original user message.
    method : str
        Detection method used: ``keyword`` or ``semantic``.
    entities : dict or None
        Optional extracted entities.
    """

    intent_type: IntentType
    confidence: float
    raw_text: str
    method: str = "keyword"
    entities: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════
# Keyword / Regex Rules (Tier 1 — Fast Path)
# ═══════════════════════════════════════════════════════════════════════════

# Each entry: (IntentType, confidence, list_of_patterns)
# Patterns are checked in order; first match wins.

KEYWORD_RULES: List[Tuple[IntentType, float, List[str]]] = [

    # ── Hesitation ──────────────────────────────────────────────────────
    (IntentType.HESITATION, 0.90, [
        r"\b(not sure|unsure|confused|don'?t know|thinking|maybe|perhaps)\b",
        r"\b(let me think|give me time|i'?ll decide later|i need time)\b",
        r"\b(hmmm+|umm+|ugh|idk|dunno)\b",
        r"\b(can i think|wait|hold on|one sec|scared|nervous|worried)\b",
        r"\b(too fast|slow down|overwhelming)\b",
    ]),

    # ── EMI Affordability Concern ──────────────────────────────────────
    (IntentType.EMI_AFFORDABILITY, 0.90, [
        r"\b(emi|installment|monthly payment).*(high|too much|afford|expensive|costly|burden)\b",
        r"\b(can'?t afford|unaffordable|out of budget|too heavy|tight budget)\b",
        r"\b(afford|affordab).*(emi|loan|payment|installment)\b",
        r"\b(reduce|lower|decrease).*(emi|installment|payment)\b",
        r"\b(emi).*(reduce|lower|less|decrease|cut)\b",
        r"\b(salary|income).*(not enough|low|less|insufficient)\b",
        r"\b(heavy|burden|difficult).*(emi|payment|repay)\b",
    ]),

    # ── Interest Rate Question ─────────────────────────────────────────
    (IntentType.INTEREST_RATE_QUESTION, 0.90, [
        r"\b(interest rate|rate of interest|roi)\b",
        r"\b(what|how much).*(interest|rate)\b",
        r"\b(interest).*(charge|percent|%|apply|applicable)\b",
        r"\b(lower|reduce|negotiate|discount).*(rate|interest)\b",
        r"\b(fixed|floating|variable).*(rate|interest)\b",
        r"\b(rate|interest).*(personal|home|auto|car|business|education)\b",
    ]),

    # ── Tenure Question ───────────────────────────────────────────────
    (IntentType.TENURE_QUESTION, 0.90, [
        r"\b(tenure|loan period|loan duration|repayment period)\b",
        r"\b(how (many|long)|what).*(months|years|tenure|duration|period)\b",
        r"\b(extend|increase|shorten|reduce).*(tenure|duration|period)\b",
        r"\b(maximum|minimum|max|min).*(tenure|period|duration)\b",
        r"\b(change|modify|adjust).*(tenure|period|term)\b",
    ]),

    # ── Loan Inquiry ──────────────────────────────────────────────────
    (IntentType.LOAN_INQUIRY, 0.88, [
        r"\b(loan|credit).*(information|info|details|options|types|products)\b",
        r"\b(tell me|what is|explain|know).*(loan|credit|lending)\b",
        r"\b(eligible|eligibility|qualify|qualification)\b",
        r"\b(personal loan|home loan|auto loan|car loan|business loan|education loan)\b",
        r"\b(loan).*(available|offer|provide|give)\b",
        r"\b(borrow|borrowing|finance|financing)\b",
    ]),

    # ── Apply Loan ────────────────────────────────────────────────────
    (IntentType.APPLY_LOAN, 0.92, [
        r"\b(apply|start|begin|new|get).*(loan|application|credit)\b",
        r"\b(loan).*(apply|application|start|open)\b",
        r"\b(i (want|need|would like)).*(loan|borrow|credit)\b",
        r"\b(take|avail).*(loan|credit)\b",
    ]),

    # ── Check Status ──────────────────────────────────────────────────
    (IntentType.CHECK_STATUS, 0.92, [
        r"\b(status|progress|track|where).*(application|loan|request)\b",
        r"\b(application|loan|request).*(status|progress|update|stage)\b",
        r"\b(what('s| is| stage)).*(my|the).*(application|loan)\b",
    ]),

    # ── Upload Document ──────────────────────────────────────────────
    (IntentType.UPLOAD_DOCUMENT, 0.92, [
        r"\b(upload|attach|submit|share|send).*(document|doc|file|paper|slip|proof)\b",
        r"\b(document|file|paper|slip|proof).*(upload|attach|submit|share|send)\b",
        r"\b(salary slip|bank statement|address proof|pan card|aadhaar|itr)\b",
    ]),

    # ── Ask EMI ──────────────────────────────────────────────────────
    (IntentType.ASK_EMI, 0.90, [
        r"\b(calculate|compute|what|how much).*(emi|installment|monthly payment)\b",
        r"\b(emi|installment).*(calculate|how much|what|amount)\b",
        r"\b(repayment|amortization|schedule|breakup|breakdown)\b",
    ]),

    # ── Greeting ─────────────────────────────────────────────────────
    (IntentType.GREETING, 0.95, [
        r"^(hi|hello|hey|hola|namaste|good (morning|afternoon|evening))[\s!.?]*$",
        r"^(howdy|greetings|sup|what'?s up|yo)[\s!.?]*$",
    ]),
]


def _keyword_classify(text: str) -> Optional[Intent]:
    """
    Attempt to classify via keyword / regex rules.

    Returns an Intent if a rule matches, else None.
    """
    lower = text.strip().lower()

    for intent_type, confidence, patterns in KEYWORD_RULES:
        for pattern in patterns:
            if re.search(pattern, lower):
                return Intent(
                    intent_type=intent_type,
                    confidence=confidence,
                    raw_text=text,
                    method="keyword",
                )
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Semantic Similarity (Tier 2 — Deep Path)
# ═══════════════════════════════════════════════════════════════════════════

# Curated exemplar sentences per intent for embedding comparison.
EXEMPLAR_BANK: Dict[IntentType, List[str]] = {

    IntentType.HESITATION: [
        "I'm not sure about this",
        "Let me think about it",
        "I need some time to decide",
        "Can I come back later?",
        "I'm confused, is this right for me?",
        "Maybe I should wait",
        "I don't know if I should proceed",
        "This is too fast for me",
        "I'm a bit nervous about this",
        "Give me a moment to think",
    ],

    IntentType.EMI_AFFORDABILITY: [
        "The EMI is too high for me",
        "I can't afford this monthly payment",
        "Is there a way to reduce the EMI?",
        "My salary is not enough for this EMI",
        "This installment is too expensive",
        "The monthly payment is out of my budget",
        "Can you lower the EMI amount?",
        "I'm worried about paying this every month",
        "This EMI will be a burden on me",
        "Is there a cheaper option with lower payments?",
    ],

    IntentType.INTEREST_RATE_QUESTION: [
        "What is the interest rate for personal loans?",
        "Can you tell me the rate of interest?",
        "What rate will I get?",
        "Is there any discount on the interest rate?",
        "What is the current ROI?",
        "Can you reduce the interest rate?",
        "Is it fixed or floating rate?",
        "What percentage interest do you charge?",
        "How much interest will I pay?",
        "Any offers on interest rates?",
    ],

    IntentType.TENURE_QUESTION: [
        "What tenure options are available?",
        "How many months can I repay in?",
        "Can I extend the loan tenure?",
        "What is the maximum loan duration?",
        "I want a longer repayment period",
        "Can I change the tenure later?",
        "What EMI will I get for 5 years?",
        "Is 3 year or 5 year tenure better?",
        "How long will I have to pay?",
        "What is the minimum repayment period?",
    ],

    IntentType.LOAN_INQUIRY: [
        "Tell me about your loan products",
        "What types of loans do you offer?",
        "Am I eligible for a loan?",
        "I want to know about personal loans",
        "What are the requirements for a home loan?",
        "How much can I borrow?",
        "What documents do I need for a loan?",
        "Do you offer education loans?",
        "Is there a loan for buying a car?",
        "What are the eligibility criteria?",
    ],

    IntentType.APPLY_LOAN: [
        "I want to apply for a loan",
        "Start my loan application",
        "I need a personal loan",
        "Help me get a home loan",
        "I want to borrow money",
        "Begin the loan process",
        "I'd like to take a loan",
        "Open a new loan for me",
    ],

    IntentType.ASK_EMI: [
        "Calculate my EMI",
        "What will be my monthly payment?",
        "Show me the EMI for 5 lakh loan",
        "How much EMI for 10 lakh personal loan?",
        "Break down the repayment schedule",
        "Show me the amortization table",
        "What is the EMI for 3 years?",
    ],

    IntentType.GREETING: [
        "Hello",
        "Hi there",
        "Good morning",
        "Hey",
        "Namaste",
    ],
}

# Confidence threshold for semantic match
SEMANTIC_THRESHOLD = 0.55

# Lazy-loaded model and exemplar embeddings
_exemplar_embeddings: Optional[Dict[IntentType, Any]] = None


def _load_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None and _HAS_TRANSFORMERS:
        logger.info("Loading sentence-transformer model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Sentence-transformer model loaded.")
    return _model


def _get_exemplar_embeddings():
    """Lazy-compute and cache exemplar embeddings."""
    global _exemplar_embeddings
    if _exemplar_embeddings is not None:
        return _exemplar_embeddings

    model = _load_model()
    if model is None:
        return None

    _exemplar_embeddings = {}
    for intent_type, sentences in EXEMPLAR_BANK.items():
        _exemplar_embeddings[intent_type] = model.encode(
            sentences, convert_to_tensor=True, show_progress_bar=False,
        )
    logger.info("Exemplar embeddings computed for %d intents.", len(_exemplar_embeddings))
    return _exemplar_embeddings


def _semantic_classify(text: str) -> Optional[Intent]:
    """
    Classify via sentence-transformer cosine similarity.

    Encodes the user message and compares against all exemplar embeddings.
    Returns the intent with the highest similarity above the threshold.
    """
    if not _HAS_TRANSFORMERS:
        return None

    model = _load_model()
    if model is None:
        return None

    exemplars = _get_exemplar_embeddings()
    if exemplars is None:
        return None

    # Encode user message
    user_emb = model.encode(text, convert_to_tensor=True, show_progress_bar=False)

    best_intent: Optional[IntentType] = None
    best_score: float = 0.0

    for intent_type, emb_matrix in exemplars.items():
        # Cosine similarity against all exemplars for this intent
        scores = st_util.cos_sim(user_emb, emb_matrix)
        max_score = float(scores.max())

        if max_score > best_score:
            best_score = max_score
            best_intent = intent_type

    if best_intent is not None and best_score >= SEMANTIC_THRESHOLD:
        return Intent(
            intent_type=best_intent,
            confidence=round(best_score, 4),
            raw_text=text,
            method="semantic",
        )

    return None


# ═══════════════════════════════════════════════════════════════════════════
# Entity Extraction (Lightweight)
# ═══════════════════════════════════════════════════════════════════════════

def _extract_entities(text: str) -> Dict[str, Any]:
    """
    Extract common entities from the user message.

    Supports:
    - Monetary amounts (₹5,00,000 / 5 lakh / 10k)
    - PAN numbers (ABCDE1234F)
    - Phone numbers (10 digits)
    - Tenure mentions (36 months / 3 years)
    """
    entities: Dict[str, Any] = {}
    lower = text.lower().replace(",", "").replace("₹", "")

    # Amount
    amt_match = re.search(
        r"(\d+\.?\d*)\s*(crore|cr|lakh|lac|l|thousand|k)s?", lower
    )
    if amt_match:
        val = float(amt_match.group(1))
        suffix = amt_match.group(2)
        mult = {
            "crore": 1_00_00_000, "cr": 1_00_00_000,
            "lakh": 1_00_000, "lac": 1_00_000, "l": 1_00_000,
            "thousand": 1_000, "k": 1_000,
        }
        entities["amount"] = val * mult.get(suffix, 1)

    # PAN
    pan_match = re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", text.upper())
    if pan_match:
        entities["pan"] = pan_match.group()

    # Phone
    phone_match = re.search(r"\b[6-9]\d{9}\b", text)
    if phone_match:
        entities["phone"] = phone_match.group()

    # Tenure
    tenure_match = re.search(r"(\d+)\s*(months?|years?|yrs?)", lower)
    if tenure_match:
        val = int(tenure_match.group(1))
        unit = tenure_match.group(2)
        if "year" in unit or "yr" in unit:
            val *= 12
        entities["tenure_months"] = val

    return entities


# ═══════════════════════════════════════════════════════════════════════════
# Main Detection Function
# ═══════════════════════════════════════════════════════════════════════════

async def detect(user_message: str) -> Intent:
    """
    Classify the user's intent from raw text.

    Two-tier strategy:
    1. **Keyword rules** (fast, high-confidence).
    2. **Semantic similarity** via sentence-transformers (if available).
    3. Falls back to ``GENERAL_QUERY`` if no match is found.

    Parameters
    ----------
    user_message : str
        The user's message text.

    Returns
    -------
    Intent
        Detected intent with confidence, method, and optional entities.
    """
    text = user_message.strip()
    if not text:
        return Intent(
            intent_type=IntentType.UNKNOWN,
            confidence=0.0,
            raw_text=text,
            method="empty",
        )

    logger.info("Detecting intent for: '%s'", text[:80])

    # Extract entities regardless of classification method
    entities = _extract_entities(text)

    # ── Tier 1: Keyword fallback ────────────────────────────────────────
    kw_result = _keyword_classify(text)
    if kw_result is not None:
        kw_result.entities = entities or None
        logger.info(
            "Intent (keyword): %s conf=%.2f",
            kw_result.intent_type.value,
            kw_result.confidence,
        )
        return kw_result

    # ── Tier 2: Semantic similarity ─────────────────────────────────────
    sem_result = _semantic_classify(text)
    if sem_result is not None:
        sem_result.entities = entities or None
        logger.info(
            "Intent (semantic): %s conf=%.4f",
            sem_result.intent_type.value,
            sem_result.confidence,
        )
        return sem_result

    # ── Fallback: General query ─────────────────────────────────────────
    logger.info("Intent: GENERAL_QUERY (fallback)")
    return Intent(
        intent_type=IntentType.GENERAL_QUERY,
        confidence=0.3,
        raw_text=text,
        method="fallback",
        entities=entities or None,
    )
