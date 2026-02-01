# ================================================================================
# TATA CAPITAL - PROFESSIONAL SANCTION LETTER PDF GENERATOR
# ================================================================================
#
# PURPOSE:
# --------
# This module generates professional sanction letter PDF documents for approved
# loans with Tata Capital branding. Documents are saved to /sanction_letters
# folder for download by customers.
#
# ================================================================================

"""
PDF Sanction Letter Generator for Tata Capital
Creates professional loan sanction letters with Tata Capital branding.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from datetime import datetime, timedelta
import os
import uuid

# ================================================================================
# CONFIGURATION - TATA CAPITAL BRANDING
# ================================================================================

# Tata Capital Branding
COMPANY_NAME = "TATA CAPITAL"
COMPANY_FULL_NAME = "Tata Capital Financial Services Limited"
COMPANY_TAGLINE = "We only do what's right for you"
COMPANY_ADDRESS = "11th Floor, Tower A, Peninsula Business Park, Senapati Bapat Marg, Lower Parel, Mumbai - 400013"
COMPANY_CIN = "U65990MH1991PLC060670"
COMPANY_HELPLINE = "1860-267-6060"
COMPANY_EMAIL = "customercare@tatacapital.com"
COMPANY_WEBSITE = "www.tatacapital.com"

# Tata Capital Brand Colors
TATA_BLUE = HexColor('#004589')  # Primary Tata Blue
TATA_DARK_BLUE = HexColor('#002D5A')  # Dark Blue
TATA_LIGHT_BLUE = HexColor('#E8F4FC')  # Light Blue Background
TATA_GOLD = HexColor('#C4A000')  # Accent Gold

# Sanction letters storage folder
SANCTION_LETTERS_FOLDER = os.path.join(os.path.dirname(__file__), "sanction_letters")


def ensure_sanction_letters_folder():
    """Ensure the sanction_letters folder exists."""
    if not os.path.exists(SANCTION_LETTERS_FOLDER):
        os.makedirs(SANCTION_LETTERS_FOLDER)
        print(f"📁 Created sanction_letters folder: {SANCTION_LETTERS_FOLDER}")
    return SANCTION_LETTERS_FOLDER


def format_indian_currency(amount: int) -> str:
    """Format number in Indian currency style (lakhs/crores)."""
    amount = int(round(float(amount)))
    s = str(amount)
    if len(s) <= 3:
        return s
    last_three = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ','.join(parts) + ',' + last_three


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
    Generate professional Tata Capital sanction letter PDF.
    
    Args:
        customer_name: Customer's full name
        loan_amount: Sanctioned loan amount in rupees
        interest_rate: Interest rate per annum
        tenure: Loan tenure in months
        emi: Monthly EMI amount
        phone: Customer phone number
        pan: Customer PAN number
        approval_type: Type of approval
        session_id: Session ID for file naming
        
    Returns:
        str: Absolute file path to generated PDF
    """
    
    folder = ensure_sanction_letters_folder()
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = session_id or str(uuid.uuid4())[:8]
    filename = f"tata_capital_sanction_{unique_id}_{timestamp}.pdf"
    filepath = os.path.join(folder, filename)
    
    print(f"\n📄 Generating Tata Capital Sanction Letter PDF")
    print(f"   Customer: {customer_name}")
    print(f"   Amount: ₹{format_indian_currency(loan_amount)}")
    
    # Create PDF with custom page setup
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # ============ HEADER WITH LOGO AREA ============
    # Blue header bar
    c.setFillColor(TATA_BLUE)
    c.rect(0, height - 100, width, 100, fill=True, stroke=False)
    
    # Company name in header
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(50, height - 55, "TATA CAPITAL")
    
    # Tagline
    c.setFont("Helvetica-Oblique", 11)
    c.drawString(50, height - 75, COMPANY_TAGLINE)
    
    # CIN on right side
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 50, height - 45, f"CIN: {COMPANY_CIN}")
    c.drawRightString(width - 50, height - 58, COMPANY_WEBSITE)
    c.drawRightString(width - 50, height - 71, f"Helpline: {COMPANY_HELPLINE}")
    
    # ============ DOCUMENT TITLE ============
    c.setFillColor(TATA_BLUE)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 140, "PERSONAL LOAN SANCTION LETTER")
    
    # Decorative line
    c.setStrokeColor(TATA_GOLD)
    c.setLineWidth(2)
    c.line(150, height - 150, width - 150, height - 150)
    
    # ============ DATE AND REFERENCE ============
    today = datetime.now()
    name_code = customer_name.replace(" ", "").upper()[:4] if customer_name else "CUST"
    ref_no = f"TC/PL/{today.strftime('%Y%m%d')}/{name_code}{today.strftime('%H%M')}"
    validity_date = (today + timedelta(days=30)).strftime("%d %B %Y")
    
    y_pos = height - 190
    
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_pos, "Date:")
    c.setFont("Helvetica", 10)
    c.drawString(130, y_pos, today.strftime("%d %B %Y"))
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(350, y_pos, "Reference No:")
    c.setFont("Helvetica", 10)
    c.drawString(440, y_pos, ref_no)
    
    y_pos -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_pos, "Valid Until:")
    c.setFont("Helvetica", 10)
    c.drawString(130, y_pos, validity_date)
    
    # ============ CUSTOMER ADDRESS ============
    y_pos -= 40
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_pos, "To,")
    y_pos -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, f"Mr./Ms. {customer_name}")
    
    if phone:
        y_pos -= 16
        c.setFont("Helvetica", 10)
        c.drawString(50, y_pos, f"Mobile: {phone}")
    
    if pan:
        y_pos -= 16
        c.drawString(50, y_pos, f"PAN: {pan}")
    
    # ============ GREETING ============
    y_pos -= 35
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_pos, f"Dear Mr./Ms. {customer_name},")
    
    y_pos -= 25
    c.setFont("Helvetica", 10)
    
    # Opening paragraph
    opening_text = "We are delighted to inform you that your application for a Personal Loan has been"
    c.drawString(50, y_pos, opening_text)
    
    y_pos -= 18
    c.setFillColor(HexColor('#006400'))  # Dark green for APPROVED
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "APPROVED")
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    c.drawString(120, y_pos, "by Tata Capital Financial Services Limited.")
    
    y_pos -= 25
    c.drawString(50, y_pos, "Please find the details of your sanctioned loan below:")
    
    # ============ LOAN DETAILS TABLE ============
    y_pos -= 30
    
    # Table header
    c.setFillColor(TATA_BLUE)
    c.rect(50, y_pos - 5, width - 100, 25, fill=True, stroke=False)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, y_pos + 3, "LOAN DETAILS")
    
    y_pos -= 35
    
    # Calculate derived values
    total_amount_payable = emi * tenure
    total_interest = total_amount_payable - loan_amount
    processing_fee = max(2500, int(loan_amount * 0.02))  # 2% or min ₹2,500
    
    # Loan details rows
    loan_details = [
        ("Sanctioned Loan Amount", f"₹ {format_indian_currency(loan_amount)}"),
        ("Interest Rate (Fixed)", f"{interest_rate}% per annum"),
        ("Loan Tenure", f"{tenure} months"),
        ("Monthly EMI", f"₹ {format_indian_currency(emi)}"),
        ("Total Interest Payable", f"₹ {format_indian_currency(total_interest)}"),
        ("Total Amount Payable", f"₹ {format_indian_currency(total_amount_payable)}"),
        ("Processing Fee", f"₹ {format_indian_currency(processing_fee)} + GST"),
        ("EMI Start Date", (today + timedelta(days=30)).strftime("%d %B %Y")),
    ]
    
    row_height = 22
    for i, (label, value) in enumerate(loan_details):
        # Alternating row colors
        if i % 2 == 0:
            c.setFillColor(TATA_LIGHT_BLUE)
            c.rect(50, y_pos - 5, width - 100, row_height, fill=True, stroke=False)
        
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y_pos + 3, label)
        c.setFont("Helvetica", 10)
        c.drawRightString(width - 60, y_pos + 3, value)
        
        y_pos -= row_height
    
    # Table border
    c.setStrokeColor(TATA_BLUE)
    c.setLineWidth(1)
    c.rect(50, y_pos + 5, width - 100, row_height * len(loan_details) + 30, fill=False, stroke=True)
    
    # ============ TERMS AND CONDITIONS ============
    y_pos -= 30
    c.setFillColor(TATA_BLUE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_pos, "Terms & Conditions:")
    
    y_pos -= 20
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    
    terms = [
        "1. This sanction letter is valid for 30 days from the date of issue.",
        "2. Loan disbursement is subject to completion of all documentation and verification.",
        "3. The interest rate mentioned above is fixed for the entire loan tenure.",
        "4. Prepayment/Foreclosure charges: 4% + GST on outstanding principal (after 12 months).",
        "5. Late payment charges: ₹500 + GST per instance of delayed EMI payment.",
        "6. Please ensure timely payment of EMIs to maintain a healthy credit score.",
        "7. The loan is subject to the general terms and conditions of Tata Capital.",
    ]
    
    for term in terms:
        c.drawString(50, y_pos, term)
        y_pos -= 14
    
    # ============ ACCEPTANCE SECTION ============
    y_pos -= 20
    c.setFillColor(TATA_BLUE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_pos, "To accept this offer:")
    
    y_pos -= 18
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    c.drawString(50, y_pos, f"• Visit your nearest Tata Capital branch with original documents")
    y_pos -= 14
    c.drawString(50, y_pos, f"• Call our helpline at {COMPANY_HELPLINE}")
    y_pos -= 14
    c.drawString(50, y_pos, f"• Email us at {COMPANY_EMAIL}")
    
    # ============ CLOSING ============
    y_pos -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y_pos, "We thank you for choosing Tata Capital and look forward to serving you.")
    
    # ============ SIGNATURE ============
    y_pos -= 50
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_pos, "Yours sincerely,")
    
    y_pos -= 35
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_pos, "Authorized Signatory")
    y_pos -= 14
    c.setFont("Helvetica", 10)
    c.drawString(50, y_pos, "Tata Capital Financial Services Limited")
    
    # Digital signature note
    y_pos -= 20
    c.setFillColor(HexColor('#666666'))
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, y_pos, "[Digitally Signed Document]")
    
    # ============ FOOTER ============
    # Footer bar
    c.setFillColor(TATA_BLUE)
    c.rect(0, 0, width, 50, fill=True, stroke=False)
    
    c.setFillColor(white)
    c.setFont("Helvetica", 7)
    c.drawCentredString(width/2, 35, COMPANY_FULL_NAME)
    c.drawCentredString(width/2, 24, COMPANY_ADDRESS)
    c.drawCentredString(width/2, 13, f"Helpline: {COMPANY_HELPLINE} | Email: {COMPANY_EMAIL} | Website: {COMPANY_WEBSITE}")
    
    # Disclaimer at very bottom
    c.setFillColor(HexColor('#666666'))
    c.setFont("Helvetica-Oblique", 7)
    disclaimer = "This is a system-generated document and does not require a physical signature. For any queries, please contact our customer care."
    c.drawCentredString(width/2, 55, disclaimer)
    
    # Save PDF
    c.save()
    
    print(f"✅ Sanction letter generated: {filepath}")
    
    return filepath


def get_sanction_letter_path(session_id: str) -> str:
    """
    Get the file path for a sanction letter by session ID.
    
    Args:
        session_id: Session ID used when generating the letter
        
    Returns:
        str: File path if found, None otherwise
    """
    folder = ensure_sanction_letters_folder()
    
    for filename in os.listdir(folder):
        if session_id in filename and filename.endswith('.pdf'):
            return os.path.join(folder, filename)
    
    return None


def cleanup_pdf_file(file_path: str):
    """Clean up a PDF file."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            print(f"🗑️ Cleaned up PDF file: {file_path}")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup PDF file {file_path}: {e}")