# ================================================================================
# PHASE 7: SANCTION LETTER PDF GENERATOR
# ================================================================================
#
# PURPOSE:
# --------
# This module generates professional sanction letter PDF documents for approved
# loans. The documents are saved to a persistent /sanction_letters folder for
# download by customers.
#
# HOW THIS SIMULATES REAL NBFC BACK-OFFICE APPROVAL:
# --------------------------------------------------
# In a real NBFC (Non-Banking Financial Company), when a loan is approved:
#
# 1. The Credit Operations team generates a formal Sanction Letter
# 2. The letter is created using the APPROVED loan parameters (not editable)
# 3. Contains legally binding terms:
#    - Loan amount sanctioned
#    - Interest rate (fixed/floating)
#    - Tenure and EMI schedule
#    - Processing fees
#    - Terms & conditions
#    - Validity period (typically 30 days)
#
# 4. The letter is digitally signed (we simulate with "Authorized Signatory")
# 5. Customer reviews and accepts the sanction
# 6. Only then does disbursement happen
#
# WHY DOCUMENT CREATION IS SEPARATED FROM LLM DIALOGUE:
# -----------------------------------------------------
# 1. REGULATORY COMPLIANCE: Loan terms must be exact and auditable
#    - LLM could hallucinate wrong numbers (₹5L becomes ₹50L)
#    - Interest rates must match what was calculated by rules engine
#    - EMI must be mathematically correct
#
# 2. LEGAL VALIDITY: Sanction letter is a binding document
#    - Cannot have creative liberties in wording
#    - Must follow standardized format
#    - All values must come from verified shared state
#
# 3. AUDIT TRAIL: Every document must be reproducible
#    - Given same inputs, must generate same document
#    - LLM non-determinism would break audit requirements
#
# 4. SEPARATION OF CONCERNS:
#    - LLM handles: Human-like conversation, emotional response
#    - PDF Generator handles: Precise, legal document creation
#    - This prevents the LLM from "inventing" loan terms
#
# ================================================================================

"""
PDF Sanction Letter Generator for Aurora Finance NBFC Ltd.
Creates professional loan sanction letters with dynamic data from shared state.

PHASE 7: Documents are saved to /sanction_letters folder for persistent storage.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime, timedelta
import os
import uuid

# ================================================================================
# CONFIGURATION
# ================================================================================

# NBFC Branding (Phase 7: Using placeholder brand as specified)
NBFC_NAME = "Aurora Finance NBFC Ltd."
NBFC_TAGLINE = "Illuminating Your Financial Future"
NBFC_ADDRESS = "Aurora Tower, 15th Floor, Bandra Kurla Complex, Mumbai - 400051"
NBFC_CIN = "U65100MH2020PLC123456"
NBFC_HELPLINE = "1800-123-4567"
NBFC_EMAIL = "support@aurorafinance.in"

# Fixed interest rate as per Phase 7 specification (can be overridden by actual rate)
DEFAULT_INTEREST_RATE = 12.5

# Sanction letters storage folder
SANCTION_LETTERS_FOLDER = os.path.join(os.path.dirname(__file__), "sanction_letters")


def ensure_sanction_letters_folder():
    """
    Ensure the sanction_letters folder exists.
    Creates it if it doesn't exist.
    
    PHASE 7: Files are stored persistently, not in temp folder.
    """
    if not os.path.exists(SANCTION_LETTERS_FOLDER):
        os.makedirs(SANCTION_LETTERS_FOLDER)
        print(f"📁 Created sanction_letters folder: {SANCTION_LETTERS_FOLDER}")
    return SANCTION_LETTERS_FOLDER


def generate_sanction_letter(
    customer_name: str,
    loan_amount: int,
    interest_rate: float,
    tenure: int,
    emi: int,
    phone: str = "",
    pan: str = "",
    approval_type: str = None,
    session_id: str = None
) -> str:
    """
    PHASE 7: Generate professional Aurora Finance NBFC sanction letter PDF
    
    This function creates a realistic-looking sanction letter document using
    ONLY values from the shared state (passed as parameters). It does NOT
    invent any data - all values must be provided by the caller.
    
    HOW THIS SIMULATES REAL NBFC DOCUMENT GENERATION:
    -------------------------------------------------
    1. Uses verified data from underwriting decision (not LLM-generated)
    2. Calculates derived values (total interest, repayment) deterministically
    3. Generates unique reference number for tracking
    4. Sets 30-day validity period (standard NBFC practice)
    5. Includes standard terms & conditions
    6. Saves to persistent folder for download
    
    Args:
        customer_name: Customer's full name (from shared state)
        loan_amount: Sanctioned loan amount in rupees (from underwriting)
        interest_rate: Interest rate per annum (from underwriting)
        tenure: Loan tenure in months (from shared state)
        emi: Monthly EMI amount (calculated by underwriting engine)
        phone: Customer phone number (from shared state)
        pan: Customer PAN number (from shared state)
        approval_type: Type of approval (from underwriting decision)
        session_id: Session ID for file naming (optional)
        
    Returns:
        str: Absolute file path to generated PDF in /sanction_letters folder
    """
    
    # Ensure storage folder exists
    folder = ensure_sanction_letters_folder()
    
    # Generate unique filename
    # Format: aurora_sanction_<SESSION_ID>_<TIMESTAMP>.pdf
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = session_id or str(uuid.uuid4())[:8]
    filename = f"aurora_sanction_{unique_id}_{timestamp}.pdf"
    filepath = os.path.join(folder, filename)
    
    print(f"\n📄 PHASE 7: Generating Sanction Letter PDF")
    print(f"   Folder: {folder}")
    print(f"   Filename: {filename}")
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles with Aurora Finance branding (Deep Purple theme)
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=18,
        textColor=HexColor('#4A148C'),  # Deep Purple
        alignment=1,  # Center
        spaceAfter=10
    )
    
    tagline_style = ParagraphStyle(
        'TaglineStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor('#7B1FA2'),  # Purple
        alignment=1,
        spaceAfter=20
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#4A148C'),
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        leading=14
    )
    
    # Build PDF content
    story = []
    
    # ============ Header Section ============
    story.append(Paragraph(f"<b>{NBFC_NAME}</b>", title_style))
    story.append(Paragraph(f"<i>{NBFC_TAGLINE}</i>", tagline_style))
    story.append(Paragraph(f"CIN: {NBFC_CIN}", ParagraphStyle(
        'CINStyle', parent=styles['Normal'], fontSize=8, alignment=1, textColor=HexColor('#666666')
    )))
    story.append(Spacer(1, 15))
    
    # ============ Document Title ============
    story.append(Paragraph("<b>PERSONAL LOAN SANCTION LETTER</b>", header_style))
    story.append(Spacer(1, 15))
    
    # ============ Date and Reference ============
    today = datetime.now()
    # Reference format: AFNL/PL/YYYYMMDD/XXXX (Aurora Finance NBFC Ltd)
    name_code = customer_name.replace(" ", "").upper()[:4] if customer_name else "CUST"
    ref_no = f"AFNL/PL/{today.strftime('%Y%m%d')}/{name_code}{today.strftime('%H%M')}"
    validity_date = (today + timedelta(days=30)).strftime("%B %d, %Y")
    
    story.append(Paragraph(f"<b>Date:</b> {today.strftime('%B %d, %Y')}", normal_style))
    story.append(Paragraph(f"<b>Reference No:</b> {ref_no}", normal_style))
    story.append(Paragraph(f"<b>Offer Valid Until:</b> {validity_date}", normal_style))
    story.append(Spacer(1, 20))
    
    # ============ Customer Greeting ============
    salutation = customer_name if customer_name else "Valued Customer"
    story.append(Paragraph(f"<b>Dear Mr./Ms. {salutation},</b>", normal_style))
    story.append(Spacer(1, 10))
    
    # ============ Approval Message ============
    approval_text = approval_type if approval_type else "Standard Approval"
    story.append(Paragraph(
        f"We are pleased to inform you that your application for a Personal Loan has been <b>APPROVED</b> "
        f"({approval_text}). Please find the sanctioned loan details below:",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # ============ Loan Details Table ============
    # Calculate derived values deterministically (same as underwriting engine)
    total_repayment = emi * tenure
    total_interest = total_repayment - loan_amount
    processing_fee = 2500  # Fixed processing fee
    
    loan_data = [
        ['SANCTIONED LOAN DETAILS', ''],
        ['Sanctioned Loan Amount', f'₹ {loan_amount:,}'],
        ['Interest Rate (Fixed)', f'{interest_rate}% per annum'],
        ['Loan Tenure', f'{tenure} months ({tenure//12} years {tenure%12} months)' if tenure >= 12 else f'{tenure} months'],
        ['Monthly EMI', f'₹ {emi:,}'],
        ['Total Interest Payable', f'₹ {total_interest:,}'],
        ['Total Amount Repayable', f'₹ {total_repayment:,}'],
        ['Processing Fee', f'₹ {processing_fee:,} + GST (18%)'],
        ['CUSTOMER DETAILS', ''],
        ['Customer Name', customer_name or 'As per records'],
        ['Mobile Number', phone if phone else 'On file'],
        ['PAN Number', pan if pan else 'On file'],
        ['Approval Type', approval_type or 'Standard Approval'],
    ]
    
    table = Table(loan_data, colWidths=[2.8*inch, 3.2*inch])
    table.setStyle(TableStyle([
        # Header rows styling (Deep Purple)
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4A148C')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
        ('BACKGROUND', (0, 8), (-1, 8), HexColor('#4A148C')),
        ('TEXTCOLOR', (0, 8), (-1, 8), HexColor('#FFFFFF')),
        
        # General styling
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, 7), [HexColor('#F5F5F5'), HexColor('#FFFFFF')]),
        ('ROWBACKGROUNDS', (0, 9), (-1, -1), [HexColor('#F5F5F5'), HexColor('#FFFFFF')]),
        
        # Bold for labels (first column)
        ('FONTNAME', (0, 1), (0, 7), 'Helvetica-Bold'),
        ('FONTNAME', (0, 9), (0, -1), 'Helvetica-Bold'),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 25))
    
    # ============ Terms & Conditions (Phase 7: Comprehensive) ============
    story.append(Paragraph("<b>IMPORTANT TERMS &amp; CONDITIONS:</b>", header_style))
    story.append(Spacer(1, 5))
    
    # Phase 7: Simple terms & conditions paragraph as specified
    terms = [
        "This sanction letter is valid for 30 days from the date of issue. The offer will automatically expire if not accepted within this period.",
        "Loan disbursement is subject to successful completion of all documentation, verification processes, and execution of the loan agreement.",
        "The interest rate mentioned is fixed for the entire tenure of the loan and will not change due to market fluctuations.",
        "Prepayment/Foreclosure charges: 4% of outstanding principal + applicable GST (waived if prepaid after 12 months of disbursement).",
        "Late payment penalty: Rs.500 + GST per instance of delayed EMI payment. Continued default may affect your credit score.",
        "The borrower must maintain an active bank account for auto-debit/ECS mandate throughout the loan tenure.",
        "Insurance on the loan is optional but recommended. Premium details available on request.",
        "All disputes shall be subject to the exclusive jurisdiction of courts in Mumbai."
    ]
    
    for i, term in enumerate(terms, 1):
        story.append(Paragraph(f"<b>{i}.</b> {term}", normal_style))
    
    story.append(Spacer(1, 20))
    
    # ============ Next Steps ============
    story.append(Paragraph("<b>NEXT STEPS:</b>", header_style))
    next_steps = [
        "Review this sanction letter carefully.",
        f"Visit your nearest {NBFC_NAME} branch with original documents for verification.",
        "Complete KYC formalities and sign the loan agreement.",
        "Disbursement will be processed within 24-48 hours after documentation completion."
    ]
    for step in next_steps:
        story.append(Paragraph(f"• {step}", normal_style))
    
    story.append(Spacer(1, 20))
    
    # ============ Closing Message ============
    story.append(Paragraph(
        f"We are delighted to have you as our valued customer. Thank you for choosing {NBFC_NAME}!",
        normal_style
    ))
    story.append(Spacer(1, 30))
    
    # ============ Signature Section (Phase 7: Authorized Signatory) ============
    story.append(Paragraph("<b>Yours sincerely,</b>", normal_style))
    story.append(Spacer(1, 40))
    story.append(Paragraph("_________________________", normal_style))
    story.append(Paragraph("<b>Authorized Signatory</b>", normal_style))
    story.append(Paragraph(f"<b>{NBFC_NAME}</b>", normal_style))
    story.append(Spacer(1, 20))
    
    # ============ Footer ============
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=HexColor('#666666'),
        alignment=1  # Center
    )
    
    story.append(Paragraph(
        "<i>This is a system-generated document and does not require a physical signature.</i>",
        footer_style
    ))
    story.append(Paragraph(
        f"<i>For any queries, please contact: {NBFC_HELPLINE} | {NBFC_EMAIL}</i>",
        footer_style
    ))
    story.append(Paragraph(
        f"<i>{NBFC_ADDRESS}</i>",
        footer_style
    ))
    
    # Build PDF
    doc.build(story)
    
    print(f"✅ PHASE 7: Sanction letter PDF generated successfully")
    print(f"   Path: {filepath}")
    print(f"   Reference: {ref_no}")
    
    # Return the file path (not temp file, persistent storage)
    return filepath


def get_sanction_letter_path(session_id: str) -> str:
    """
    Get the path to a sanction letter by session ID.
    
    PHASE 7: Searches the sanction_letters folder for matching file.
    
    Args:
        session_id: Session ID used when generating the letter
        
    Returns:
        str: Path to the PDF file, or None if not found
    """
    folder = ensure_sanction_letters_folder()
    
    # Look for file matching session ID pattern
    for filename in os.listdir(folder):
        if session_id in filename and filename.endswith('.pdf'):
            return os.path.join(folder, filename)
    
    return None


def cleanup_old_sanction_letters(max_age_days: int = 30):
    """
    Clean up old sanction letters to prevent disk space issues.
    
    PHASE 7: Removes files older than max_age_days.
    In production, this would be run as a scheduled job.
    
    Args:
        max_age_days: Maximum age of files to keep (default 30 days)
    """
    folder = ensure_sanction_letters_folder()
    cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
    
    removed_count = 0
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.getmtime(filepath) < cutoff_time:
            try:
                os.remove(filepath)
                removed_count += 1
            except Exception as e:
                print(f"Warning: Could not remove old file {filepath}: {e}")
    
    if removed_count > 0:
        print(f"🧹 Cleaned up {removed_count} old sanction letters")


def cleanup_pdf_file(file_path: str):
    """
    Clean up a specific PDF file.
    
    Note: With PHASE 7's persistent storage, this is less commonly needed.
    Files are now kept for download rather than being temporary.
    
    Args:
        file_path: Path to the PDF file to remove
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            print(f"🗑️ Removed PDF file: {file_path}")
    except Exception as e:
        print(f"Warning: Could not cleanup PDF file {file_path}: {e}")


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    """Test the sanction letter generator."""
    
    print("\n" + "="*70)
    print("🧪 TESTING PHASE 7: SANCTION LETTER PDF GENERATOR")
    print("="*70)
    
    # Test sanction letter generation
    filepath = generate_sanction_letter(
        customer_name="Rahul Mehta",
        loan_amount=500000,
        interest_rate=11.5,
        tenure=48,
        emi=13045,
        phone="9876543210",
        pan="ABCDE1234F",
        approval_type="Instant Pre-Approved",
        session_id="test-session-001"
    )
    
    print(f"\n✅ Test PDF generated: {filepath}")
    print(f"   File exists: {os.path.exists(filepath)}")
    
    # Test retrieval
    retrieved = get_sanction_letter_path("test-session-001")
    print(f"   Retrieved path: {retrieved}")
    
    print("\n" + "="*70)
    print("✅ Phase 7 PDF Generator tests completed")
    print("="*70)
