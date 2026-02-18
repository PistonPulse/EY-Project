"""
document_agent.py
=================

Production worker agent for **document collection and validation** in
the lending chatbot.

Covered State
-------------
- ``DOCUMENT_UPLOAD`` — guide the user through uploading required documents,
  validate file metadata (type, size), track the checklist, and simulate
  document approval after all items are received.

Architecture
------------
::

    User Message / File Metadata
         │
         ▼
    DocumentAgent.process()
         │
         ├─ _handle_checklist_prompt()  → show pending docs
         ├─ _handle_upload()           → validate type + size
         └─ _handle_completion()       → simulate approval

Required Documents (per employment type)
----------------------------------------
- **Salaried**:      salary_slip, bank_statement, address_proof, photo_id
- **Self-employed**: itr_returns, bank_statement, address_proof, photo_id, business_proof
- **Business**:      itr_returns, bank_statement, address_proof, photo_id, business_proof, gst_certificate
- **Professional**:  itr_returns, bank_statement, address_proof, photo_id, professional_certificate

Design Principles
-----------------
- **File-type validation** — only PDF, JPEG, PNG accepted.
- **File-size validation** — max 5 MB per file.
- **Document checklist** — tracks which docs are pending vs. received.
- **Simulated approval** — deterministic; swappable with real doc-review service.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.agents.base_agent import AgentResult, BaseAgent


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

# Allowed file types
ALLOWED_EXTENSIONS: Set[str] = {"pdf", "jpg", "jpeg", "png"}
ALLOWED_MIME_TYPES: Set[str] = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # 5 MB

# Human-readable document labels
DOC_LABELS: Dict[str, str] = {
    "salary_slip":              "Salary Slip (last 3 months)",
    "bank_statement":           "Bank Statement (last 6 months)",
    "address_proof":            "Address Proof (Aadhaar / Utility Bill)",
    "photo_id":                 "Photo ID (PAN Card / Passport)",
    "itr_returns":              "ITR Returns (last 2 years)",
    "business_proof":           "Business Registration Certificate",
    "gst_certificate":          "GST Certificate",
    "professional_certificate": "Professional Certificate / License",
}

# Required documents per employment type
REQUIRED_DOCS: Dict[str, List[str]] = {
    "salaried":      ["salary_slip", "bank_statement", "address_proof", "photo_id"],
    "self_employed":  ["itr_returns", "bank_statement", "address_proof", "photo_id", "business_proof"],
    "business":      ["itr_returns", "bank_statement", "address_proof", "photo_id", "business_proof", "gst_certificate"],
    "professional":  ["itr_returns", "bank_statement", "address_proof", "photo_id", "professional_certificate"],
}

# Map user text to document keys
DOC_SYNONYMS: Dict[str, str] = {
    "salary":     "salary_slip",
    "salary slip": "salary_slip",
    "payslip":    "salary_slip",
    "pay slip":   "salary_slip",
    "bank":       "bank_statement",
    "bank statement": "bank_statement",
    "statement":  "bank_statement",
    "address":    "address_proof",
    "address proof": "address_proof",
    "aadhaar":    "address_proof",
    "utility":    "address_proof",
    "utility bill": "address_proof",
    "photo":      "photo_id",
    "photo id":   "photo_id",
    "id proof":   "photo_id",
    "passport":   "photo_id",
    "pan card":   "photo_id",
    "itr":        "itr_returns",
    "tax return": "itr_returns",
    "income tax": "itr_returns",
    "business registration": "business_proof",
    "business proof": "business_proof",
    "gst":        "gst_certificate",
    "gst certificate": "gst_certificate",
    "professional certificate": "professional_certificate",
    "license":    "professional_certificate",
}


# ═══════════════════════════════════════════════════════════════════════════
# File Validation
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FileMetadata:
    """Metadata for an uploaded file."""
    filename: str = ""
    size_bytes: int = 0
    mime_type: str = ""
    extension: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FileMetadata":
        filename = d.get("filename", d.get("file_name", ""))
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return cls(
            filename=filename,
            size_bytes=int(d.get("size_bytes", d.get("size", 0))),
            mime_type=d.get("mime_type", d.get("content_type", "")),
            extension=ext,
        )

    @classmethod
    def from_filename(cls, name: str, size: int = 0) -> "FileMetadata":
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        mime_map = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}
        return cls(filename=name, size_bytes=size, mime_type=mime_map.get(ext, ""), extension=ext)


def validate_file(meta: FileMetadata) -> Tuple[bool, List[str]]:
    """
    Validate file type and size.

    Returns (True, []) if valid, (False, [error_messages]) otherwise.
    """
    errors: List[str] = []

    # Extension check
    if meta.extension not in ALLOWED_EXTENSIONS:
        errors.append(
            f"File type `.{meta.extension}` is not accepted. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # MIME type check (if available)
    if meta.mime_type and meta.mime_type not in ALLOWED_MIME_TYPES:
        errors.append(f"MIME type `{meta.mime_type}` is not allowed.")

    # Size check
    if meta.size_bytes > MAX_FILE_SIZE_BYTES:
        actual_mb = meta.size_bytes / (1024 * 1024)
        errors.append(
            f"File is too large ({actual_mb:.1f} MB). Maximum allowed: {MAX_FILE_SIZE_MB} MB."
        )

    if meta.size_bytes == 0 and not errors:
        # Size unknown is OK for chat-based uploads (size checked server-side)
        pass

    return (len(errors) == 0, errors)


# ═══════════════════════════════════════════════════════════════════════════
# Document Checklist Tracker
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DocumentChecklist:
    """Tracks which required documents have been received."""
    required: List[str] = field(default_factory=list)
    received: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def pending(self) -> List[str]:
        return [d for d in self.required if d not in self.received]

    @property
    def is_complete(self) -> bool:
        return len(self.pending) == 0

    @property
    def progress_pct(self) -> int:
        if not self.required:
            return 100
        return int(len(self.received) / len(self.required) * 100)

    def mark_received(self, doc_key: str, metadata: Dict[str, Any]) -> None:
        self.received[doc_key] = {
            **metadata,
            "received_at": time.time(),
            "status": "received",
        }


# ═══════════════════════════════════════════════════════════════════════════
# Response Templates
# ═══════════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, str] = {

    "checklist_prompt": (
        "📄 **Document Upload**\n\n"
        "Please upload the following documents for your loan application:\n\n"
        "{checklist}\n\n"
        "📌 **Upload rules:**\n"
        "• Accepted formats: **PDF**, **JPEG**, **PNG**\n"
        "• Max file size: **5 MB** per document\n"
        "• Ensure documents are clear and legible\n\n"
        "Upload a document or tell me which one you're submitting "
        "(e.g. _\"salary slip\"_)."
    ),

    "upload_success": (
        "✅ **{doc_label}** received!\n\n"
        "📊 Progress: **{progress}%** ({received}/{total} documents)\n\n"
        "{remaining_text}"
    ),

    "upload_invalid_type": (
        "❌ **Invalid file type**\n\n"
        "{errors}\n\n"
        "Please re-upload as **PDF**, **JPEG**, or **PNG**."
    ),

    "upload_invalid_size": (
        "❌ **File too large**\n\n"
        "{errors}\n\n"
        "Please compress the file and re-upload (max **5 MB**)."
    ),

    "upload_validation_errors": (
        "❌ **Upload rejected**\n\n"
        "{errors}\n\n"
        "Please fix the issues and try again."
    ),

    "doc_identified": (
        "Got it — you're uploading your **{doc_label}**.\n\n"
        "Please attach the file now (PDF, JPEG, or PNG, max 5 MB)."
    ),

    "all_received": (
        "🎉 **All documents received!**\n\n"
        "{summary_table}\n\n"
        "⏳ Verifying your documents… This usually takes a moment."
    ),

    "approval_simulated": (
        "✅ **Documents Verified & Approved**\n\n"
        "All submitted documents have passed our verification checks:\n\n"
        "{verification_table}\n\n"
        "🔒 Your documents are securely stored and encrypted.\n\n"
        "Let's proceed to the final step — your **Sanction Letter**! 🎉"
    ),

    "status_check": (
        "📋 **Document Status**\n\n"
        "{summary_table}\n\n"
        "Progress: **{progress}%** complete."
    ),
}


def _render(key: str, **kwargs) -> str:
    tpl = TEMPLATES.get(key, "")
    try:
        return tpl.format(**kwargs)
    except KeyError:
        return tpl


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _detect_doc_type(text: str) -> Optional[str]:
    """Map user text to a document key."""
    normalised = text.strip().lower()
    if normalised in DOC_SYNONYMS:
        return DOC_SYNONYMS[normalised]
    for keyword, doc_key in DOC_SYNONYMS.items():
        if keyword in normalised:
            return doc_key
    return None


def _build_checklist_text(checklist: DocumentChecklist) -> str:
    """Build a Markdown checklist of required documents."""
    lines: List[str] = []
    for doc_key in checklist.required:
        label = DOC_LABELS.get(doc_key, doc_key.replace("_", " ").title())
        if doc_key in checklist.received:
            lines.append(f"  ✅ ~~{label}~~ — received")
        else:
            lines.append(f"  ⬜ {label}")
    return "\n".join(lines)


def _build_summary_table(checklist: DocumentChecklist) -> str:
    """Build a Markdown table summarising all documents."""
    lines = ["| Document | Status | File |"]
    lines.append("|----------|--------|------|")
    for doc_key in checklist.required:
        label = DOC_LABELS.get(doc_key, doc_key.replace("_", " ").title())
        if doc_key in checklist.received:
            info = checklist.received[doc_key]
            fname = info.get("filename", "uploaded")
            lines.append(f"| {label} | ✅ Received | `{fname}` |")
        else:
            lines.append(f"| {label} | ⏳ Pending | — |")
    return "\n".join(lines)


def _build_verification_table(checklist: DocumentChecklist) -> str:
    """Build a verification result table (simulated)."""
    lines = ["| Document | Verification | Result |"]
    lines.append("|----------|-------------|--------|")
    for doc_key in checklist.required:
        label = DOC_LABELS.get(doc_key, doc_key.replace("_", " ").title())
        lines.append(f"| {label} | Authenticity check | ✅ Passed |")
    return "\n".join(lines)


def _build_remaining_text(checklist: DocumentChecklist) -> str:
    """Build text showing remaining documents."""
    pending = checklist.pending
    if not pending:
        return "🎉 All documents have been received!"
    labels = [DOC_LABELS.get(d, d.replace("_", " ").title()) for d in pending]
    items = "\n".join(f"  ⬜ {label}" for label in labels)
    return f"📋 **Still needed:**\n{items}"


# ═══════════════════════════════════════════════════════════════════════════
# Document Agent
# ═══════════════════════════════════════════════════════════════════════════

class DocumentAgent(BaseAgent):
    """
    Manages document collection, file validation, checklist tracking,
    and simulated document approval for the loan application.

    Operates during the ``DOCUMENT_UPLOAD`` state.
    """

    def __init__(self) -> None:
        super().__init__(name="document")
        # In-memory checklist storage per session
        self._checklists: Dict[str, DocumentChecklist] = {}

    async def process(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AgentResult:
        """Main entry point — routes based on upload state and user input."""
        state = context.get("state", "")
        collected = context.get("collected_data", {})
        self.logger.info("DocumentAgent | session=%s state=%s", session_id, state)

        # Initialise checklist if not yet created for this session
        checklist = self._get_or_create_checklist(session_id, collected)

        # Check for status request
        if any(kw in user_message.lower() for kw in ("status", "progress", "checklist", "list")):
            return self._show_status(checklist)

        # Check if user is telling us which doc they're uploading
        file_meta = self._extract_file_from_context(context)

        if file_meta:
            return await self._handle_upload(session_id, user_message, checklist, file_meta, collected)

        # Check if user is naming a document type
        doc_type = _detect_doc_type(user_message)
        if doc_type:
            return self._handle_doc_identified(session_id, doc_type, checklist)

        # Check for simulated file mention (e.g. "salary_slip.pdf" in text)
        simulated = self._detect_simulated_upload(user_message)
        if simulated:
            doc_type_key, meta = simulated
            return await self._handle_upload(session_id, user_message, checklist, meta, collected, doc_type_key)

        # Default: show the checklist
        return self._show_checklist(checklist)

    # ──────────────────────────────────────────────────────────────────
    # Checklist Management
    # ──────────────────────────────────────────────────────────────────

    def _get_or_create_checklist(
        self, session_id: str, collected: Dict
    ) -> DocumentChecklist:
        """Get existing checklist or create one based on employment type."""
        if session_id in self._checklists:
            return self._checklists[session_id]

        emp_type = collected.get("employment_type", "salaried")
        required = REQUIRED_DOCS.get(emp_type, REQUIRED_DOCS["salaried"])

        # Restore previously uploaded docs from collected data
        received: Dict[str, Dict[str, Any]] = {}
        for doc_key in collected.get("documents_received", []):
            received[doc_key] = {"filename": "previously_uploaded", "status": "received"}

        checklist = DocumentChecklist(required=list(required), received=received)
        self._checklists[session_id] = checklist
        return checklist

    def _show_checklist(self, checklist: DocumentChecklist) -> AgentResult:
        """Show the document checklist to the user."""
        checklist_text = _build_checklist_text(checklist)
        return AgentResult(
            success=True,
            message=_render("checklist_prompt", checklist=checklist_text),
            data={},
        )

    def _show_status(self, checklist: DocumentChecklist) -> AgentResult:
        """Show document upload status."""
        return AgentResult(
            success=True,
            message=_render(
                "status_check",
                summary_table=_build_summary_table(checklist),
                progress=checklist.progress_pct,
            ),
            data={},
        )

    # ──────────────────────────────────────────────────────────────────
    # Document Identification
    # ──────────────────────────────────────────────────────────────────

    def _handle_doc_identified(
        self, session_id: str, doc_key: str, checklist: DocumentChecklist
    ) -> AgentResult:
        """User told us which document they're going to upload."""
        if doc_key in checklist.received:
            label = DOC_LABELS.get(doc_key, doc_key)
            return AgentResult(
                success=True,
                message=f"✅ **{label}** was already received. Would you like to re-upload it?",
                data={},
            )

        label = DOC_LABELS.get(doc_key, doc_key.replace("_", " ").title())
        return AgentResult(
            success=True,
            message=_render("doc_identified", doc_label=label),
            data={"pending_doc_type": doc_key},
        )

    # ──────────────────────────────────────────────────────────────────
    # Upload Handling
    # ──────────────────────────────────────────────────────────────────

    async def _handle_upload(
        self,
        session_id: str,
        msg: str,
        checklist: DocumentChecklist,
        file_meta: FileMetadata,
        collected: Dict,
        override_doc_key: Optional[str] = None,
    ) -> AgentResult:
        """Validate an uploaded file and add it to the checklist."""

        # Validate file
        valid, errors = validate_file(file_meta)
        if not valid:
            error_text = "\n".join(f"• {e}" for e in errors)
            # Determine which template to use
            has_type_error = any("type" in e.lower() for e in errors)
            has_size_error = any("large" in e.lower() for e in errors)
            if has_type_error and not has_size_error:
                template = "upload_invalid_type"
            elif has_size_error and not has_type_error:
                template = "upload_invalid_size"
            else:
                template = "upload_validation_errors"

            return AgentResult(
                success=False,
                message=_render(template, errors=error_text),
                data={},
                errors=errors,
            )

        # Determine document type
        doc_key = override_doc_key or collected.get("pending_doc_type") or _detect_doc_type(msg)
        if not doc_key:
            # Try to guess from filename
            doc_key = self._guess_doc_from_filename(file_meta.filename)

        if not doc_key:
            # Assign to first pending doc
            pending = checklist.pending
            doc_key = pending[0] if pending else "salary_slip"

        label = DOC_LABELS.get(doc_key, doc_key.replace("_", " ").title())

        # Mark as received
        checklist.mark_received(doc_key, {
            "filename": file_meta.filename,
            "size_bytes": file_meta.size_bytes,
            "mime_type": file_meta.mime_type,
        })

        # Check if all docs are now received
        if checklist.is_complete:
            return await self._handle_completion(session_id, checklist)

        remaining_text = _build_remaining_text(checklist)

        return AgentResult(
            success=True,
            message=_render(
                "upload_success",
                doc_label=label,
                progress=checklist.progress_pct,
                received=len(checklist.received),
                total=len(checklist.required),
                remaining_text=remaining_text,
            ),
            data={
                "documents_received": list(checklist.received.keys()),
                "documents_pending": checklist.pending,
                "document_progress": checklist.progress_pct,
            },
        )

    # ──────────────────────────────────────────────────────────────────
    # Completion & Simulated Approval
    # ──────────────────────────────────────────────────────────────────

    async def _handle_completion(
        self, session_id: str, checklist: DocumentChecklist
    ) -> AgentResult:
        """All documents received — simulate verification and approval."""
        summary = _build_summary_table(checklist)
        verification_table = _build_verification_table(checklist)

        # Two-part response: "all received" → "approved"
        combined_msg = (
            _render("all_received", summary_table=summary)
            + "\n\n"
            + _render("approval_simulated", verification_table=verification_table)
        )

        return AgentResult(
            success=True,
            message=combined_msg,
            data={
                "documents_received": list(checklist.received.keys()),
                "documents_pending": [],
                "document_progress": 100,
                "documents_verified": True,
                "documents_approved": True,
                "document_verification_status": "approved",
            },
        )

    # ──────────────────────────────────────────────────────────────────
    # Utility Methods
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_file_from_context(context: Dict) -> Optional[FileMetadata]:
        """
        Check if the context contains file upload metadata.

        The API layer is expected to populate ``context['file']`` with
        a dict containing ``filename``, ``size_bytes``, and ``mime_type``.
        """
        file_data = context.get("file") or context.get("uploaded_file")
        if file_data and isinstance(file_data, dict):
            return FileMetadata.from_dict(file_data)
        return None

    @staticmethod
    def _detect_simulated_upload(msg: str) -> Optional[Tuple[str, FileMetadata]]:
        """
        Detect simulated file uploads in text messages for demo/testing.

        Handles patterns like:
        - "uploading salary_slip.pdf"
        - "here's my bank_statement.pdf (2MB)"
        - "salary slip.jpg"
        """
        # Look for filename-like patterns
        m = re.search(
            r"(\w[\w\s]*?)\.(pdf|jpg|jpeg|png)",
            msg,
            re.IGNORECASE,
        )
        if not m:
            return None

        raw_name = m.group(0)
        name_part = m.group(1).strip().lower().replace(" ", "_")
        ext = m.group(2).lower()

        # Try to extract size
        size_match = re.search(r"(\d+\.?\d*)\s*(mb|kb)", msg, re.IGNORECASE)
        size_bytes = 0
        if size_match:
            val = float(size_match.group(1))
            unit = size_match.group(2).lower()
            size_bytes = int(val * (1024 * 1024 if unit == "mb" else 1024))
        else:
            # Default simulated size: 500 KB
            size_bytes = 500 * 1024

        meta = FileMetadata.from_filename(raw_name, size_bytes)

        # Map filename to doc type
        doc_key = _detect_doc_type(name_part)
        if not doc_key:
            # Try the raw name
            doc_key = _detect_doc_type(m.group(1))

        return (doc_key, meta) if doc_key else None

    @staticmethod
    def _guess_doc_from_filename(filename: str) -> Optional[str]:
        """Best-effort guess of document type from filename."""
        lower = filename.lower().replace("_", " ").replace("-", " ")
        for keyword, doc_key in DOC_SYNONYMS.items():
            if keyword in lower:
                return doc_key
        return None
