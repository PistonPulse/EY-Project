# PHASE 6: Sanction Letter Generator
"""
PDF Sanction Letter Generator for Tata Capital
Creates professional loan sanction letters with dynamic data
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, blue, black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime, timedelta
import tempfile
import os

def generate_sanction_letter(
    customer_name: str,
    loan_amount: int,
    interest_rate: float,
    tenure: int,
    emi: int,
    phone: str = "",
    pan: str = ""
) -> str:
    """
    PHASE 6: Generate professional Tata Capital sanction letter PDF
    
    Args:
        customer_name: Customer's full name
        loan_amount: Sanctioned loan amount in rupees
        interest_rate: Interest rate per annum
        tenure: Loan tenure in months
        emi: Monthly EMI amount
        phone: Customer phone number
        pan: Customer PAN number
        
    Returns:
        str: File path to generated PDF
    """
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, 
        suffix='.pdf',
        prefix='tata_sanction_'
    )
    
    # Create PDF document
    doc = SimpleDocTemplate(
        temp_file.name,
        pagesize=A4,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=18,
        textColor=HexColor('#004589'),
        alignment=1,  # Center
        spaceAfter=20
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#004589'),
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Build PDF content
    story = []
    
    # Header
    story.append(Paragraph("<b>TATA CAPITAL LIMITED</b>", title_style))
    story.append(Paragraph("Personal Loan Sanction Letter", header_style))
    story.append(Spacer(1, 20))
    
    # Date and reference
    today = datetime.now()
    ref_no = f"TCL/PL/{today.strftime('%Y%m%d')}/{customer_name.replace(' ', '').upper()[:4]}"
    
    story.append(Paragraph(f"<b>Date:</b> {today.strftime('%B %d, %Y')}", normal_style))
    story.append(Paragraph(f"<b>Reference No:</b> {ref_no}", normal_style))
    story.append(Spacer(1, 20))
    
    # Customer details
    story.append(Paragraph("<b>Dear Mr./Ms. " + customer_name + ",</b>", normal_style))
    story.append(Spacer(1, 10))
    
    # Sanction message
    story.append(Paragraph(
        f"We are pleased to inform you that your application for a Personal Loan has been <b>APPROVED</b>. "
        f"Please find the loan details below:",
        normal_style
    ))
    story.append(Spacer(1, 15))
    
    # Loan details table
    loan_data = [
        ['Loan Details', ''],
        ['Sanctioned Amount', f'₹ {loan_amount:,}'],
        ['Interest Rate', f'{interest_rate}% per annum'],
        ['Loan Tenure', f'{tenure} months ({tenure//12} years {tenure%12} months)'],
        ['Monthly EMI', f'₹ {emi:,}'],
        ['Processing Fee', '₹ 2,500 + GST'],
        ['Customer Details', ''],
        ['Customer Name', customer_name],
        ['Phone Number', phone or 'On file'],
        ['PAN Number', pan or 'On file'],
    ]
    
    table = Table(loan_data, colWidths=[3*inch, 3*inch])
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#004589')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
        ('BACKGROUND', (0, 6), (-1, 6), HexColor('#004589')),
        ('TEXTCOLOR', (0, 6), (-1, 6), HexColor('#FFFFFF')),
        
        # General styling
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, black),
        
        # Bold for labels
        ('FONTNAME', (0, 1), (0, 5), 'Helvetica-Bold'),
        ('FONTNAME', (0, 7), (0, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 20))
    
    # Important notes
    story.append(Paragraph("<b>Important Terms & Conditions:</b>", header_style))
    
    terms = [
        "This sanction is valid for 30 days from the date of this letter.",
        "Loan disbursal is subject to completion of documentation and verification.",
        "Interest rate is fixed for the entire loan tenure.",
        "Prepayment charges: 4% + GST on outstanding principal (after 1 year).",
        "Late payment charges: ₹500 + GST per instance.",
        "Please visit your nearest Tata Capital branch to complete the documentation."
    ]
    
    for i, term in enumerate(terms, 1):
        story.append(Paragraph(f"{i}. {term}", normal_style))
    
    story.append(Spacer(1, 20))
    
    # Closing
    story.append(Paragraph(
        "We look forward to serving you and thank you for choosing Tata Capital.",
        normal_style
    ))
    story.append(Spacer(1, 30))
    
    # Signature section
    story.append(Paragraph("<b>Yours sincerely,</b>", normal_style))
    story.append(Spacer(1, 40))
    story.append(Paragraph("<b>Credit Manager</b>", normal_style))
    story.append(Paragraph("<b>Tata Capital Limited</b>", normal_style))
    story.append(Spacer(1, 20))
    
    # Footer
    story.append(Paragraph(
        "<i>This is a system-generated document. For any queries, please contact our customer service at 1800-209-5555.</i>",
        ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=HexColor('#666666'),
            alignment=1  # Center
        )
    ))
    
    # Build PDF
    doc.build(story)
    temp_file.close()
    
    return temp_file.name


def cleanup_pdf_file(file_path: str):
    """Clean up temporary PDF file"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f"Warning: Could not cleanup PDF file {file_path}: {e}")