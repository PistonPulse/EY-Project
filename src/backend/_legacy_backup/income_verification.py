"""
================================================================================
PHASE 6: CONTROLLED SALARY DOCUMENT UPLOAD AND DETERMINISTIC INCOME VERIFICATION
================================================================================

This module handles salary slip upload and income verification in a controlled,
deterministic manner. NO LLM involvement in parsing or decisions.

================================================================================
WHY INCOME VERIFICATION IS ISOLATED
================================================================================

SINGLE RESPONSIBILITY PRINCIPLE:
   Income verification is a critical financial validation step that MUST:
   - Run exactly once per application
   - Produce deterministic, reproducible results
   - Not be influenced by LLM hallucinations
   - Not be bypassed or repeated

FRAUD PREVENTION:
   Isolating income verification prevents:
   - Multiple upload attempts to game the system
   - UI bugs causing infinite verification loops
   - State inconsistencies from partial uploads
   - Race conditions in concurrent uploads

AUDIT TRAIL:
   Every income verification creates a permanent record:
   - Document hash for integrity
   - Extraction timestamp
   - Verified salary amount
   - Verification source

================================================================================
WHY UPLOAD IS STAGE-CONTROLLED
================================================================================

SECURITY:
   Upload button visibility tied to stage prevents:
   - Premature uploads before KYC
   - Late uploads after underwriting
   - Orphaned documents without context

UI DEADLOCK PREVENTION:
   Stage-controlled upload ensures:
   - Button appears exactly when needed
   - Button disappears after success (no re-upload)
   - Clear state transitions
   - No flickering or race conditions

STATE MACHINE INTEGRITY:
   Upload control maintains:
   - Linear progression through stages
   - Single source of truth for document status
   - Predictable UI behavior
   - Testable state transitions

================================================================================
DETERMINISTIC SALARY PARSING
================================================================================

For demo/testing, we use a MOCK parser that:
1. Maps filenames to predetermined salaries
2. Returns consistent results for same input
3. Simulates real parsing delays
4. Handles error cases deterministically

In production, this would integrate with:
- OCR services (Google Vision, AWS Textract)
- PDF parsers (PyPDF2, pdfplumber)
- ML models for document classification

================================================================================
"""

import logging
import hashlib
import re
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# ================================================================================
# LOGGING CONFIGURATION
# ================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | INCOME_VERIFY | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('income_verification')


# ================================================================================
# DATA STRUCTURES
# ================================================================================

class DocumentType(Enum):
    """Supported document types for income verification."""
    SALARY_SLIP = "salary_slip"
    BANK_STATEMENT = "bank_statement"
    FORM_16 = "form_16"
    ITR = "itr"


class VerificationStatus(Enum):
    """Status of income verification."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    RETRY_ALLOWED = "RETRY_ALLOWED"


@dataclass
class DocumentUploadResult:
    """Result of document upload operation."""
    success: bool
    document_id: Optional[str]
    document_type: Optional[DocumentType]
    file_hash: Optional[str]
    file_name: str
    file_size_bytes: int
    upload_timestamp: str
    error_message: Optional[str]


@dataclass
class SalaryExtractionResult:
    """Result of salary extraction from document."""
    success: bool
    monthly_salary_inr: Optional[int]
    employer_name: Optional[str]
    employee_name: Optional[str]
    pay_period: Optional[str]
    extraction_method: str
    confidence_score: float
    extraction_timestamp: str
    error_message: Optional[str]


@dataclass
class IncomeVerificationResult:
    """Complete income verification result."""
    success: bool
    income_verified: bool
    verified_monthly_salary_inr: Optional[int]
    document_id: Optional[str]
    verification_status: VerificationStatus
    verification_timestamp: str
    can_retry: bool
    retry_count: int
    error_message: Optional[str]


# ================================================================================
# MOCK DATA FOR DETERMINISTIC TESTING
# ================================================================================
# These are deterministic test cases for demo/development.
# In production, actual parsing would be performed.

# Mock salary database: filename pattern -> salary amount
# This allows deterministic testing with predictable outcomes
MOCK_SALARY_DATABASE: Dict[str, Dict[str, Any]] = {
    # High earners (₹1L+)
    "salary_high": {
        "monthly_salary": 150000,
        "employer": "TechCorp India Pvt Ltd",
        "employee": "Demo User",
        "pay_period": "January 2026"
    },
    "salary_senior": {
        "monthly_salary": 200000,
        "employer": "Global Finance Ltd",
        "employee": "Demo User",
        "pay_period": "January 2026"
    },
    
    # Mid-range earners (₹50K-1L)
    "salary_mid": {
        "monthly_salary": 75000,
        "employer": "Startup Solutions",
        "employee": "Demo User",
        "pay_period": "January 2026"
    },
    "salary_medium": {
        "monthly_salary": 60000,
        "employer": "Retail Corp",
        "employee": "Demo User",
        "pay_period": "January 2026"
    },
    
    # Lower earners (₹25K-50K)
    "salary_low": {
        "monthly_salary": 35000,
        "employer": "Local Services",
        "employee": "Demo User",
        "pay_period": "January 2026"
    },
    "salary_entry": {
        "monthly_salary": 25000,
        "employer": "Entry Level Corp",
        "employee": "Demo User",
        "pay_period": "January 2026"
    },
    
    # Edge cases
    "salary_minimum": {
        "monthly_salary": 15000,
        "employer": "Small Business",
        "employee": "Demo User",
        "pay_period": "January 2026"
    },
    
    # Error cases (for testing failure handling)
    "salary_corrupt": None,  # Simulates corrupt file
    "salary_unreadable": None,  # Simulates unreadable file
}

# Default salary for unknown files (simulates successful parsing)
DEFAULT_MOCK_SALARY = {
    "monthly_salary": 50000,
    "employer": "Unknown Employer",
    "employee": "Demo User",
    "pay_period": "January 2026"
}

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# Maximum file size (10 MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Maximum retry attempts
MAX_RETRY_ATTEMPTS = 1


# ================================================================================
# ENTRY CONDITION CHECKS
# ================================================================================

def can_start_income_verification(
    kyc_status: Optional[str],
    interest_rate_min: Optional[float],
    interest_rate_max: Optional[float],
    requested_loan_amount: Optional[int]
) -> Tuple[bool, str]:
    """
    Check if INCOME_DOC_UPLOAD stage entry conditions are met.
    
    STRICT ENTRY CONDITIONS (Phase 6):
    1. KYC status must be VERIFIED
    2. Interest rate range must exist (from Phase 5)
    3. Requested loan amount must be known
    
    Args:
        kyc_status: Current KYC verification status
        interest_rate_min: Minimum interest rate from offer discovery
        interest_rate_max: Maximum interest rate from offer discovery
        requested_loan_amount: Customer's requested loan amount
        
    Returns:
        Tuple of (can_proceed, reason)
    """
    logger.info("Checking income verification entry conditions")
    
    if kyc_status != "VERIFIED":
        reason = f"KYC not verified. Status: {kyc_status}"
        logger.warning(f"Entry blocked: {reason}")
        return False, reason
    
    if interest_rate_min is None or interest_rate_max is None:
        reason = "Interest rate range not available. Complete offer discovery first."
        logger.warning(f"Entry blocked: {reason}")
        return False, reason
    
    if requested_loan_amount is None or requested_loan_amount <= 0:
        reason = "Requested loan amount not specified."
        logger.warning(f"Entry blocked: {reason}")
        return False, reason
    
    logger.info("All entry conditions met for income verification")
    return True, "Ready for income verification"


def can_upload_document(
    current_stage: str,
    income_verified: bool,
    upload_attempted: bool,
    retry_count: int
) -> Tuple[bool, str]:
    """
    Check if document upload is allowed.
    
    Upload is allowed ONLY when:
    1. Current stage is INCOME_DOC_UPLOAD
    2. Income is not already verified
    3. Retry count is within limits
    
    Args:
        current_stage: Current stage name
        income_verified: Whether income is already verified
        upload_attempted: Whether upload was already attempted
        retry_count: Number of retry attempts made
        
    Returns:
        Tuple of (can_upload, reason)
    """
    if current_stage != "INCOME_DOC_UPLOAD":
        return False, f"Upload not allowed in stage: {current_stage}"
    
    if income_verified:
        return False, "Income already verified. Upload not allowed."
    
    if upload_attempted and retry_count >= MAX_RETRY_ATTEMPTS:
        return False, f"Maximum retry attempts ({MAX_RETRY_ATTEMPTS}) exceeded."
    
    return True, "Upload allowed"


# ================================================================================
# DOCUMENT UPLOAD HANDLING
# ================================================================================

def validate_document(
    file_name: str,
    file_size_bytes: int,
    file_content: Optional[bytes] = None
) -> Tuple[bool, str]:
    """
    Validate uploaded document before processing.
    
    Checks:
    1. File extension is supported
    2. File size is within limits
    3. File is not empty
    
    Args:
        file_name: Name of the uploaded file
        file_size_bytes: Size of file in bytes
        file_content: Optional file content for additional validation
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    logger.info(f"Validating document: {file_name} ({file_size_bytes} bytes)")
    
    # Check file extension
    extension = "." + file_name.lower().split(".")[-1] if "." in file_name else ""
    if extension not in SUPPORTED_EXTENSIONS:
        return False, f"Unsupported file type: {extension}. Allowed: PDF, JPG, PNG"
    
    # Check file size
    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        return False, f"File too large. Maximum size: {MAX_FILE_SIZE_BYTES // (1024*1024)} MB"
    
    if file_size_bytes == 0:
        return False, "File is empty"
    
    logger.info("Document validation passed")
    return True, ""


def generate_document_id(file_name: str, file_size: int, timestamp: str) -> str:
    """Generate unique document ID from file metadata."""
    content = f"{file_name}:{file_size}:{timestamp}"
    return hashlib.md5(content.encode()).hexdigest()[:12].upper()


def process_document_upload(
    file_name: str,
    file_size_bytes: int,
    file_content: Optional[bytes] = None
) -> DocumentUploadResult:
    """
    Process document upload and prepare for parsing.
    
    This function:
    1. Validates the document
    2. Generates document ID
    3. Computes file hash
    4. Prepares for salary extraction
    
    Args:
        file_name: Name of the uploaded file
        file_size_bytes: Size of file in bytes
        file_content: Optional file content
        
    Returns:
        DocumentUploadResult with upload status
    """
    timestamp = datetime.now().isoformat()
    logger.info(f"Salary document upload started: {file_name}")
    
    # Validate document
    is_valid, error = validate_document(file_name, file_size_bytes, file_content)
    if not is_valid:
        logger.error(f"Document validation failed: {error}")
        return DocumentUploadResult(
            success=False,
            document_id=None,
            document_type=None,
            file_hash=None,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            upload_timestamp=timestamp,
            error_message=error
        )
    
    # Generate document ID and hash
    doc_id = generate_document_id(file_name, file_size_bytes, timestamp)
    file_hash = hashlib.sha256(
        (file_content or f"{file_name}:{file_size_bytes}".encode())
        if isinstance(file_content, bytes) 
        else f"{file_name}:{file_size_bytes}".encode()
    ).hexdigest()[:16]
    
    logger.info(f"Document uploaded successfully. ID: {doc_id}")
    
    return DocumentUploadResult(
        success=True,
        document_id=doc_id,
        document_type=DocumentType.SALARY_SLIP,
        file_hash=file_hash,
        file_name=file_name,
        file_size_bytes=file_size_bytes,
        upload_timestamp=timestamp,
        error_message=None
    )


# ================================================================================
# SALARY EXTRACTION (DETERMINISTIC MOCK)
# ================================================================================

def extract_salary_from_document(
    document_id: str,
    file_name: str,
    file_content: Optional[bytes] = None
) -> SalaryExtractionResult:
    """
    Extract salary information from uploaded document.
    
    DETERMINISTIC MOCK IMPLEMENTATION:
    - Maps filename patterns to predetermined salaries
    - Ensures reproducible results for testing
    - Simulates real parsing behavior
    
    In production, this would use:
    - OCR for images
    - PDF parsing for PDFs
    - ML models for data extraction
    
    Args:
        document_id: Unique document identifier
        file_name: Name of the uploaded file
        file_content: Optional file content for parsing
        
    Returns:
        SalaryExtractionResult with extracted salary data
    """
    timestamp = datetime.now().isoformat()
    logger.info(f"Starting salary extraction for document: {document_id}")
    
    # Normalize filename for lookup
    file_base = file_name.lower().replace(" ", "_").split(".")[0]
    
    # Check for error test cases
    if "corrupt" in file_base or "unreadable" in file_base:
        logger.error(f"Salary extraction failed: File unreadable - {file_name}")
        return SalaryExtractionResult(
            success=False,
            monthly_salary_inr=None,
            employer_name=None,
            employee_name=None,
            pay_period=None,
            extraction_method="mock_parser",
            confidence_score=0.0,
            extraction_timestamp=timestamp,
            error_message="Unable to read document. File may be corrupt or password protected."
        )
    
    # Look up salary from mock database
    salary_data = None
    for key in MOCK_SALARY_DATABASE:
        if key in file_base:
            salary_data = MOCK_SALARY_DATABASE[key]
            break
    
    # Use default if no match found
    if salary_data is None:
        salary_data = DEFAULT_MOCK_SALARY
        logger.info("Using default salary data (file pattern not recognized)")
    
    # Check for None (error test case)
    if salary_data is None:
        logger.error("Salary data is None - simulating extraction failure")
        return SalaryExtractionResult(
            success=False,
            monthly_salary_inr=None,
            employer_name=None,
            employee_name=None,
            pay_period=None,
            extraction_method="mock_parser",
            confidence_score=0.0,
            extraction_timestamp=timestamp,
            error_message="Could not extract salary information from document."
        )
    
    monthly_salary = salary_data["monthly_salary"]
    logger.info(f"Salary parsing successful: ₹{monthly_salary:,}")
    
    return SalaryExtractionResult(
        success=True,
        monthly_salary_inr=monthly_salary,
        employer_name=salary_data["employer"],
        employee_name=salary_data["employee"],
        pay_period=salary_data["pay_period"],
        extraction_method="mock_parser",
        confidence_score=0.95,  # High confidence for mock
        extraction_timestamp=timestamp,
        error_message=None
    )


# ================================================================================
# COMPLETE INCOME VERIFICATION FLOW
# ================================================================================

def perform_income_verification(
    file_name: str,
    file_size_bytes: int,
    file_content: Optional[bytes] = None,
    retry_count: int = 0
) -> IncomeVerificationResult:
    """
    Perform complete income verification for a customer.
    
    This is the main entry point for Phase 6 income verification.
    It combines document upload, validation, and salary extraction.
    
    IMPORTANT: This function runs EXACTLY ONCE per successful verification.
    No looping, no repeated calls, no UI toggles.
    
    Args:
        file_name: Name of the uploaded file
        file_size_bytes: Size of file in bytes
        file_content: Optional file content
        retry_count: Current retry attempt number
        
    Returns:
        IncomeVerificationResult with complete verification status
    """
    logger.info("=" * 60)
    logger.info("PHASE 6: INCOME VERIFICATION STARTED")
    logger.info("=" * 60)
    
    timestamp = datetime.now().isoformat()
    
    # Step 1: Process document upload
    upload_result = process_document_upload(file_name, file_size_bytes, file_content)
    
    if not upload_result.success:
        # Upload failed - check if retry is allowed
        can_retry = retry_count < MAX_RETRY_ATTEMPTS
        logger.warning(f"Upload failed. Retry allowed: {can_retry}")
        
        return IncomeVerificationResult(
            success=False,
            income_verified=False,
            verified_monthly_salary_inr=None,
            document_id=None,
            verification_status=VerificationStatus.RETRY_ALLOWED if can_retry else VerificationStatus.FAILED,
            verification_timestamp=timestamp,
            can_retry=can_retry,
            retry_count=retry_count,
            error_message=upload_result.error_message
        )
    
    # Step 2: Extract salary from document
    extraction_result = extract_salary_from_document(
        upload_result.document_id,
        file_name,
        file_content
    )
    
    if not extraction_result.success:
        # Extraction failed - check if retry is allowed
        can_retry = retry_count < MAX_RETRY_ATTEMPTS
        logger.warning(f"Salary extraction failed. Retry allowed: {can_retry}")
        
        return IncomeVerificationResult(
            success=False,
            income_verified=False,
            verified_monthly_salary_inr=None,
            document_id=upload_result.document_id,
            verification_status=VerificationStatus.RETRY_ALLOWED if can_retry else VerificationStatus.FAILED,
            verification_timestamp=timestamp,
            can_retry=can_retry,
            retry_count=retry_count,
            error_message=extraction_result.error_message
        )
    
    # Step 3: Verification successful
    logger.info("Income verification completed")
    logger.info(f"Verified monthly salary: ₹{extraction_result.monthly_salary_inr:,}")
    
    return IncomeVerificationResult(
        success=True,
        income_verified=True,
        verified_monthly_salary_inr=extraction_result.monthly_salary_inr,
        document_id=upload_result.document_id,
        verification_status=VerificationStatus.VERIFIED,
        verification_timestamp=timestamp,
        can_retry=False,  # No retry needed on success
        retry_count=retry_count,
        error_message=None
    )


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def format_salary_for_display(salary_inr: int) -> str:
    """Format salary amount for display with Indian numbering."""
    if salary_inr >= 10000000:  # 1 crore
        return f"₹{salary_inr/10000000:.2f} Cr"
    elif salary_inr >= 100000:  # 1 lakh
        return f"₹{salary_inr/100000:.2f} L"
    else:
        return f"₹{salary_inr:,}"


def get_upload_instructions() -> str:
    """Get instructions for document upload."""
    return """
Please upload your latest salary slip to continue with your loan application.

**Accepted formats:**
- PDF
- JPG/JPEG
- PNG

**Requirements:**
- File must be clearly readable
- Recent salary slip (last 3 months)
- Maximum file size: 10 MB

Your document will be securely processed and used only for income verification.
"""


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PHASE 6: INCOME VERIFICATION MODULE TEST")
    print("=" * 70)
    
    # Test 1: Entry conditions
    print("\n--- Test 1: Entry conditions ---")
    can_proceed, reason = can_start_income_verification(
        kyc_status="VERIFIED",
        interest_rate_min=10.0,
        interest_rate_max=11.0,
        requested_loan_amount=500000
    )
    print(f"All conditions met: {can_proceed}")
    assert can_proceed == True
    
    can_proceed, reason = can_start_income_verification(
        kyc_status="PENDING",
        interest_rate_min=10.0,
        interest_rate_max=11.0,
        requested_loan_amount=500000
    )
    print(f"KYC not verified: {can_proceed}, Reason: {reason}")
    assert can_proceed == False
    
    # Test 2: Document upload validation
    print("\n--- Test 2: Document validation ---")
    is_valid, error = validate_document("salary_slip.pdf", 1024)
    print(f"Valid PDF: {is_valid}")
    assert is_valid == True
    
    is_valid, error = validate_document("salary_slip.doc", 1024)
    print(f"Invalid DOC: {is_valid}, Error: {error}")
    assert is_valid == False
    
    # Test 3: High salary extraction
    print("\n--- Test 3: High salary extraction ---")
    result = perform_income_verification("salary_high.pdf", 5000)
    print(f"Success: {result.success}")
    print(f"Salary: {format_salary_for_display(result.verified_monthly_salary_inr)}")
    assert result.success == True
    assert result.verified_monthly_salary_inr == 150000
    
    # Test 4: Mid salary extraction
    print("\n--- Test 4: Mid salary extraction ---")
    result = perform_income_verification("salary_mid.pdf", 5000)
    print(f"Salary: {format_salary_for_display(result.verified_monthly_salary_inr)}")
    assert result.verified_monthly_salary_inr == 75000
    
    # Test 5: Low salary extraction
    print("\n--- Test 5: Low salary extraction ---")
    result = perform_income_verification("salary_low.pdf", 5000)
    print(f"Salary: {format_salary_for_display(result.verified_monthly_salary_inr)}")
    assert result.verified_monthly_salary_inr == 35000
    
    # Test 6: Default salary (unknown file)
    print("\n--- Test 6: Default salary (unknown file) ---")
    result = perform_income_verification("random_document.pdf", 5000)
    print(f"Salary: {format_salary_for_display(result.verified_monthly_salary_inr)}")
    assert result.verified_monthly_salary_inr == 50000
    
    # Test 7: Corrupt file handling
    print("\n--- Test 7: Corrupt file handling ---")
    result = perform_income_verification("salary_corrupt.pdf", 5000)
    print(f"Success: {result.success}, Can retry: {result.can_retry}")
    print(f"Error: {result.error_message}")
    assert result.success == False
    assert result.can_retry == True
    
    # Test 8: Upload control
    print("\n--- Test 8: Upload control ---")
    can_upload, reason = can_upload_document(
        current_stage="INCOME_DOC_UPLOAD",
        income_verified=False,
        upload_attempted=False,
        retry_count=0
    )
    print(f"Can upload in correct stage: {can_upload}")
    assert can_upload == True
    
    can_upload, reason = can_upload_document(
        current_stage="KYC_VERIFICATION",
        income_verified=False,
        upload_attempted=False,
        retry_count=0
    )
    print(f"Can upload in wrong stage: {can_upload}")
    assert can_upload == False
    
    can_upload, reason = can_upload_document(
        current_stage="INCOME_DOC_UPLOAD",
        income_verified=True,
        upload_attempted=True,
        retry_count=0
    )
    print(f"Can upload after verified: {can_upload}")
    assert can_upload == False
    
    print("\n" + "=" * 70)
    print("ALL INCOME VERIFICATION MODULE TESTS PASSED!")
    print("=" * 70)
