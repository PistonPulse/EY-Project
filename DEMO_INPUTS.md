# 🎬 Complete Demo Input Guide - Word-for-Word Instructions

> **EY-Tata Chatbot - 16-Stage Deterministic Loan Application Flow**  
> This guide provides EXACT inputs for each test scenario, step by step.

---

## 📋 How to Use This Guide

1. **Open the application**: Navigate to http://localhost:5173
2. **Open Admin Dashboard** (optional): http://localhost:5173/admin to watch real-time updates
3. **Follow each step exactly**: Copy and paste the exact text shown in each step
4. **Reset between scenarios**: Click the reset button before starting a new scenario

---

## ✅ Scenario 1: Rahul Mehta - APPROVED (Excellent Profile)

**Profile Summary**: Credit Score 780, Monthly Income ₹1,00,000, No existing debt  
**Expected Outcome**: ✅ APPROVED with best interest rates

### **Stage 1: GREETING**
**What to type:**
```
Hello
```
**Expected Response**: Welcome message from Tata Capital

---

### **Stage 2: PURPOSE**
**What to type:**
```
Home renovation
```
**Expected Response**: Agent asks for loan amount

---

### **Stage 3: AMOUNT**
**What to type:**
```
500000
```
**Expected Response**: Agent asks for your city

---

### **Stage 4: CITY**
**What to type:**
```
Mumbai
```
**Expected Response**: Agent asks about employment type

---

### **Stage 5: EMPLOYMENT TYPE**
**What to type:**
```
Salaried
```
**Expected Response**: Agent asks for your full name

---

### **Stage 6: NAME**
**What to type:**
```
Rahul Mehta
```
**Expected Response**: Agent asks for mobile number

---

### **Stage 7: MOBILE**
**What to type:**
```
9876543210
```
**Expected Response**: Agent sends OTP and asks you to enter it  
**Note**: The OTP will be displayed in the backend terminal logs

---

### **Stage 8: OTP VERIFICATION**
**What to type:**
```
123456
```
**Expected Response**: OTP verified successfully, agent asks for monthly income

---

### **Stage 9: INCOME**
**What to type:**
```
100000
```
**Expected Response**: Agent asks about existing loan EMIs

---

### **Stage 10: EXISTING EMI**
**What to type:**
```
0
```
**Expected Response**: Agent asks for date of birth or age

---

### **Stage 11: DOB/AGE**
**What to type:**
```
35
```
**Expected Response**: Agent asks for PAN number

---

### **Stage 12: KYC (PAN)**
**What to type:**
```
ABCDE1234F
```
**Expected Response**: PAN verified, agent shows pre-approved offer with interest rate range

---

### **Stage 13: OFFER DISCUSSION**
**What to type:**
```
Looks good, let's proceed
```
**Expected Response**: Agent asks to select loan tenure (12/24/36/48 months)

---

### **Stage 14: TENURE SELECTION**
**What to type:**
```
36
```
**Expected Response**: Agent shows calculated EMI for 36 months and processes application

---

### **Stage 15-16: UNDERWRITING & SANCTION**
**Expected Response**: 
- Application processed
- ✅ **LOAN APPROVED!**
- Sanction letter details shown
- Download button available

**Final Details**:
- Approved Amount: ₹5,00,000
- Interest Rate: ~10.5-12% (based on excellent credit)
- Tenure: 36 months
- EMI: ~₹16,000-17,000/month

---

## ⚠️ Scenario 2: Amit Verma - CONDITIONAL APPROVAL (Fair Profile)

**Profile Summary**: Credit Score 720, Monthly Income ₹75,000, Existing EMI ₹15,000  
**Expected Outcome**: ⚠️ CONDITIONAL APPROVAL with moderate rates

### **Stage 1: GREETING**
**What to type:**
```
Hi
```

---

### **Stage 2: PURPOSE**
**What to type:**
```
Wedding expenses
```

---

### **Stage 3: AMOUNT**
**What to type:**
```
600000
```

---

### **Stage 4: CITY**
**What to type:**
```
Bangalore
```

---

### **Stage 5: EMPLOYMENT TYPE**
**What to type:**
```
Salaried
```

---

### **Stage 6: NAME**
**What to type:**
```
Amit Verma
```

---

### **Stage 7: MOBILE**
**What to type:**
```
9988776655
```
**Note**: Check backend terminal for OTP

---

### **Stage 8: OTP VERIFICATION**
**What to type:**
```
123456
```

---

### **Stage 9: INCOME**
**What to type:**
```
75000
```

---

### **Stage 10: EXISTING EMI**
**What to type:**
```
15000
```

---

### **Stage 11: DOB/AGE**
**What to type:**
```
40
```

---

### **Stage 12: KYC (PAN)**
**What to type:**
```
GHIJK5678M
```

---

### **Stage 13: OFFER DISCUSSION**
**What to type:**
```
Yes, please proceed
```

---

### **Stage 14: TENURE SELECTION**
**What to type:**
```
48
```

---

### **Stage 15-16: UNDERWRITING & RESULT**
**Expected Response**: 
- ⚠️ **CONDITIONAL APPROVAL**
- Higher interest rate (12-14%)
- May require additional documentation
- Conditions: Auto-debit mandate, credit monitoring

**Final Details**:
- Approved Amount: ₹6,00,000
- Interest Rate: ~12-14%
- Tenure: 48 months
- EMI: ~₹15,000-16,000/month

---

## ❌ Scenario 3: Priya Sharma - REJECTED (Poor Profile)

**Profile Summary**: Credit Score 650, Monthly Income ₹50,000, High existing debt  
**Expected Outcome**: ❌ REJECTED due to low credit score and high debt

### **Stage 1: GREETING**
**What to type:**
```
Hello
```

---

### **Stage 2: PURPOSE**
**What to type:**
```
Business expansion
```

---

### **Stage 3: AMOUNT**
**What to type:**
```
800000
```

---

### **Stage 4: CITY**
**What to type:**
```
Delhi
```

---

### **Stage 5: EMPLOYMENT TYPE**
**What to type:**
```
Self-employed
```

---

### **Stage 6: NAME**
**What to type:**
```
Priya Sharma
```

---

### **Stage 7: MOBILE**
**What to type:**
```
9123456781
```

---

### **Stage 8: OTP VERIFICATION**
**What to type:**
```
123456
```

---

### **Stage 9: INCOME**
**What to type:**
```
50000
```

---

### **Stage 10: EXISTING EMI**
**What to type:**
```
25000
```
**Note**: High debt-to-income ratio (50%)

---

### **Stage 11: DOB/AGE**
**What to type:**
```
28
```

---

### **Stage 12: KYC (PAN)**
**What to type:**
```
MNOPQ9012R
```

---

### **Stage 13: OFFER DISCUSSION**
**What to type:**
```
Okay
```

---

### **Stage 14: TENURE SELECTION**
**What to type:**
```
24
```

---

### **Stage 15-17: UNDERWRITING & REJECTION**
**Expected Response**: 
- ❌ **APPLICATION REJECTED**
- Generic rejection message (no specific reason disclosed)
- Suggestion to reapply after 6 months
- Contact support for more information

**Rejection Reasons** (Internal - not shown to user):
- Credit score below threshold (650 < 700)
- High debt-to-income ratio (50%)
- Loan amount exceeds capacity

---

## 🎯 Quick Reference Table

| Scenario | Mobile | Name | Income | Existing EMI | Age | PAN | Amount | Tenure | Outcome |
|----------|--------|------|--------|--------------|-----|-----|--------|--------|---------|
| **Scenario 1** | 9876543210 | Rahul Mehta | 100000 | 0 | 35 | ABCDE1234F | 500000 | 36 | ✅ APPROVED |
| **Scenario 2** | 9988776655 | Amit Verma | 75000 | 15000 | 40 | GHIJK5678M | 600000 | 48 | ⚠️ CONDITIONAL |
| **Scenario 3** | 9123456781 | Priya Sharma | 50000 | 25000 | 28 | MNOPQ9012R | 800000 | 24 | ❌ REJECTED |

---

## 📊 Understanding the 16-Stage Flow

### **Stages 1-7: Basic Information Collection**
1. **GREETING** - Initial welcome
2. **PURPOSE** - Loan purpose (home, wedding, business, etc.)
3. **AMOUNT** - Requested loan amount
4. **CITY** - Current city of residence
5. **EMPLOYMENT_TYPE** - Salaried or Self-employed
6. **NAME** - Full name as per documents
7. **MOBILE** - 10-digit mobile number

### **Stage 8: OTP Verification**
- OTP sent to mobile
- Must be verified before proceeding
- 3 attempts allowed

### **Stages 9-11: Financial Information (NEW - Dynamic Credit Scoring)**
9. **INCOME** - Monthly income (take-home salary)
10. **EXISTING_EMI** - Total monthly EMI on existing loans
11. **DOB/AGE** - Date of birth or current age

### **Stage 12: KYC Verification**
- PAN number verification
- Must match identity

### **Stage 13: Offer Discussion**
- Pre-approved limit calculated
- Interest rate RANGE shown (not fixed)
- Based on calculated credit score

### **Stage 14: Tenure Selection**
- Choose from: 12, 24, 36, or 48 months
- EMI calculated AFTER tenure selection
- Shorter tenure = Higher EMI, less interest
- Longer tenure = Lower EMI, more interest

### **Stages 15-16: Underwriting & Decision**
15. **UNDERWRITING** - Backend processes application
16. **SANCTION/REJECTION** - Final decision

---

## 💡 Credit Score Calculation (Internal)

The system calculates credit score from user inputs (max 900 points):

### **1. Debt-to-Income Ratio (0-300 points)**
- DTI < 20%: 300 points (excellent)
- DTI 20-30%: 250 points (good)
- DTI 30-40%: 180 points (fair)
- DTI 40-50%: 100 points (marginal)
- DTI > 50%: 50 points (poor)

### **2. Income Level (0-250 points)**
- > ₹1,50,000/mo: 250 points
- ₹1,00,000-1,50,000: 220 points
- ₹75,000-1,00,000: 180 points
- ₹50,000-75,000: 140 points
- ₹30,000-50,000: 100 points
- < ₹30,000: 60 points

### **3. Employment Type (0-150 points)**
- Salaried: 150 points
- Self-employed: 120 points

### **4. Age Factor (0-100 points)**
- 25-45 years: 100 points (prime earning)
- 45-55 years: 80 points
- 21-25 years: 70 points
- 55-60 years: 60 points
- <21 or >60: 40 points

### **5. Loan-to-Income Ratio (0-100 points)**
- Amount < 3x annual income: 100 points
- Amount 3-5x annual: 70 points
- Amount 5-7x annual: 40 points
- Amount > 7x annual: 20 points

### **Decision Thresholds:**
- Score ≥ 700: ✅ APPROVED
- Score 600-699: ⚠️ CONDITIONAL
- Score < 600: ❌ REJECTED

---

## 🔍 Scenario Breakdown

### **Scenario 1: Rahul Mehta (Score: ~780)**
- DTI: 0% (no debt) → 300 points
- Income: ₹1,00,000 → 220 points
- Employment: Salaried → 150 points
- Age: 35 → 100 points
- Loan ratio: 5L / 12L annual = 0.42 → 100 points
- **Total: ~870 points** → ✅ APPROVED

### **Scenario 2: Amit Verma (Score: ~650)**
- DTI: 20% (15k/75k) → 250 points
- Income: ₹75,000 → 180 points
- Employment: Salaried → 150 points
- Age: 40 → 100 points
- Loan ratio: 6L / 9L annual = 0.67 → 70 points
- **Total: ~750 points** → ✅ APPROVED (but conditional)

### **Scenario 3: Priya Sharma (Score: ~520)**
- DTI: 50% (25k/50k) → 50 points
- Income: ₹50,000 → 140 points
- Employment: Self-employed → 120 points
- Age: 28 → 100 points
- Loan ratio: 8L / 6L annual = 1.33 → 40 points
- **Total: ~450 points** → ❌ REJECTED

---

## 🎪 Additional Test Scenarios

### **Scenario 4: Young Professional - Marginal Case**
- Mobile: `9127384590`
- Name: `Rahul Mehta`
- Purpose: `Education`
- Amount: `300000`
- City: `Mumbai`
- Employment: `Salaried`
- Income: `60000`
- Existing EMI: `8000`
- Age: `32`
- PAN: `AQMPR1234L`
- Tenure: `24`
- **Expected**: ⚠️ CONDITIONAL (Score ~700)

### **Scenario 5: High Earner - Instant Approval**
- Mobile: `9815467328`
- Name: `Priya Sharma`
- Purpose: `Home improvement`
- Amount: `500000`
- City: `Delhi`
- Employment: `Salaried`
- Income: `85000`
- Existing EMI: `12000`
- Age: `29`
- PAN: `BTXPS2345K`
- Tenure: `36`
- **Expected**: ✅ APPROVED (Score ~820)

---

## 🚨 Important Notes

### **OTP Verification**
- OTP is always `123456` in demo mode
- Check backend terminal logs to see the OTP
- 3 attempts allowed before session locks

### **PAN Verification**
- PAN must match the mobile number in database
- Format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F)
- System validates format and database match

### **Interest Rate Calculation**
- Not shown until AFTER tenure selection
- Based on calculated credit score:
  - Score ≥ 800: 10.5-12%
  - Score 750-799: 11-13%
  - Score 700-749: 12-14.5%
  - Score 650-699: 13.5-16%
  - Score < 650: 15-18%

### **EMI Calculation**
- Formula: `EMI = P × r × (1+r)^n / ((1+r)^n - 1)`
- Where: P = Principal, r = monthly rate, n = months
- Example: ₹5L at 12% for 36 months = ₹16,607/month

### **Admin Dashboard**
- Shows real-time application progress
- Displays calculated credit score (internal)
- Shows all stage transitions
- Risk category and decision reasoning

---

## 🎬 Demo Tips

1. **Start Fresh**: Always reset the chat between scenarios
2. **Copy Exact Text**: Use the exact inputs shown for consistent results
3. **Watch Backend**: Monitor terminal logs for OTP and processing details
4. **Check Admin Dashboard**: See real-time credit scoring and decision making
5. **Test Edge Cases**: Try different income/EMI combinations to see score changes
6. **Understand Flow**: Notice how the system never reveals credit score to user
7. **Observe Determinism**: Same inputs always produce same results

---

## 📞 Support

If you encounter any issues:
- Check backend terminal for errors
- Verify all services are running (frontend + backend)
- Ensure you're using exact inputs as shown
- Reset session and try again
- Check API documentation at http://localhost:8000/docs

---

**🚀 Ready to demo? Start with Scenario 1 (Rahul Mehta) for the success story!**
