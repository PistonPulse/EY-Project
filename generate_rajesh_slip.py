from PIL import Image, ImageDraw, ImageFont
import os

width, height = 800, 1000
img = Image.new('RGB', (width, height), color='white')
draw = ImageDraw.Draw(img)

try:
    font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", 20)
    font_text = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
except:
    font_title = font_bold = font_text = ImageFont.load_default()

# Header
draw.rectangle([(0, 0), (width, 80)], fill="#0f172a")
draw.text((300, 20), "Salary Slip", fill="white", font=font_title)
draw.text((50, 100), "Infosys Limited", fill="black", font=font_title)
draw.text((50, 150), "Pay Slip for the month of February 2026", fill="#64748b", font=font_text)

# Line break
draw.line([(50, 180), (750, 180)], fill="black", width=2)

# Employee Details (Mismatched Name/PAN on purpose)
draw.text((50, 210), "Employee Name:", fill="black", font=font_bold)
draw.text((250, 210), "Rajesh Kumar", fill="black", font=font_text)

draw.text((50, 240), "Designation:", fill="black", font=font_bold)
draw.text((250, 240), "Senior Analyst", fill="black", font=font_text)

# The WRONG PAN designed to trip the OCR
draw.text((50, 280), "Personal PAN:", fill="black", font=font_bold)
draw.text((250, 280), "ZZZZZ9999Z", fill="red", font=font_bold)

# Earnings
draw.text((50, 340), "EARNINGS", fill="#0f172a", font=font_bold)
draw.line([(50, 370), (350, 370)], fill="black", width=1)

draw.text((50, 390), "Basic Salary", fill="black", font=font_text)
draw.text((250, 390), "Rs. 60,000", fill="black", font=font_text)
draw.text((50, 420), "HRA", fill="black", font=font_text)
draw.text((250, 420), "Rs. 25,000", fill="black", font=font_text)

draw.line([(50, 480), (350, 480)], fill="black", width=2)
draw.text((50, 500), "Total Net Pay", fill="black", font=font_bold)
draw.text((250, 500), "Rs. 85,000", fill="black", font=font_bold)

img.save("Rajesh_Kumar_Infosys_Mismatched_Slip.png")
print("✅ Rajesh Kumar salary slip generated successfully!")
