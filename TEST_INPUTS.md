# 🧪 Test Inputs for Deterministic Flow

This document provides step-by-step test inputs to verify the **HARD RESET** implementation of the loan chatbot.

---

## 🎯 Test Scenarios

### ✅ **Scenario 1: APPROVED - Happy Path (Rahul Mehta)**
**Credit Score: 750+ | Pre-approved: ₹10L | Expected: SANCTION**

| Stage | Input | Expected Bot Response |
|-------|-------|----------------------|
| 1. GREETING | `Hi` or `Hello` | "Hi there! 👋 Welcome to Tata Capital. I'm here to help you get a personal loan quickly and hassle-free. Are you looking for a loan today?" |
| 2. PURPOSE | `home renovation` | "Wonderful! 😊 I'd love to help you out. Could you tell me what you need the loan for? It could be home renovation, education, medical expenses, a wedding, travel, or anything else!" |
| 3. AMOUNT | `5 lakhs` | "Perfect choice - Home Renovation! 👍 How much are you looking to borrow? Just give me an amount (e.g., 5 lakhs or 500000)." |
| 4. CITY | `Mumbai` | "Got it! ₹5,00,000 - I've noted that down ✅ Which city do you currently reside in? This helps us check branch availability near you." |
| 5. EMPLOYMENT_TYPE | `salaried` | "Great, Mumbai is well-covered! 📍 One quick question - are you salaried or self-employed? This helps us find the best rates for you." |
| 6. NAME | `Rahul Mehta` | "Excellent! Now, may I have your full name exactly as it appears on your PAN card? This is important for verification. 📝" |
| 7. MOBILE | `9876543210` | "Thank you, Rahul Mehta! 😊 Please share your 10-digit mobile number. We'll send a quick OTP to verify - takes just a few seconds!" |
| 8. OTP | `123456` | "📱 OTP sent to your mobile! Please check your messages and enter the 6-digit verification code. It should arrive within a few seconds." |
| 9. KYC | `ABCDE1234F` | "Wonderful! Your mobile number is verified ✅ Now I need your PAN number for identity verification. Please enter your 10-character PAN (e.g., ABCDE1234F)." |
| 10. OFFER_DISCUSSION | `yes` | "🎉 Fantastic news, Rahul Mehta! Based on your profile, you're pre-approved for up to ₹10,00,000! 🎊 📊 Interest Rate: 10.5% - 18% per annum. Would you like to proceed with your application? Just say 'yes'!" |
| 11. TENURE_SELECTION | `24 months` | "Great! Now let's choose a repayment plan that works for you 📅 Here are your EMI options: 📌 12 months, 📌 24 months, 📌 36 months, 📌 48 months. Just type your preferred tenure!" |
| 12. UNDERWRITING | *automatic* | "Your application is being processed... ⏳ Our underwriting team is reviewing your profile. This usually takes just a moment - hang tight!" |
| 13. SANCTION | *automatic* | "🎊🎉 CONGRATULATIONS, Rahul Mehta! Your loan is APPROVED! 🎉🎊 💰 Loan Amount: ₹5,00,000 📈 Interest Rate: 10.5% p.a. 📅 Tenure: 24 months 💳 Monthly EMI: ₹22,500. Welcome to the Tata Capital family! 🙏" |

**Expected Final State:**
- ✅ Approved amount: ₹5,00,000
- ✅ Interest rate: 10.5% (excellent credit)
- ✅ Tenure: 24 months
- ✅ EMI: ~₹22,500/month

**Loading States Shown During Processing:**
- KYC Stage: "Connecting to NSDL server..." → "Fetching PAN details..." → "Verifying identity..." → "Connecting to CRM server..." → "Fetching customer profile..." → "KYC verified!"
- Offer Stage: "Connecting to Credit Bureau API..." → "Fetching credit score..." → "Connecting to Offer Mart server..." → "Checking pre-approved offers..." → "Calculating eligibility..." → "Offer ready!"
- Underwriting Stage: "Initiating underwriting engine..." → "Analyzing credit history..." → "Checking debt-to-income ratio..." → "Verifying employment stability..." → "Running fraud checks..." → "Calculating risk score..." → "Finalizing decision..."

---

### ❌ **Scenario 2: REJECTED - Low Credit (Priya Sharma)**
**Credit Score: 650 | Expected: REJECTION**

| Stage | Input | Expected Bot Response |
|-------|-------|----------------------|
| 1. GREETING | `Hello` | "Hi there! 👋 Welcome to Tata Capital. I'm here to help you get a personal loan quickly and hassle-free. Are you looking for a loan today?" |
| 2. PURPOSE | `personal loan` | "Wonderful! 😊 I'd love to help you out. Could you tell me what you need the loan for?" |
| 3. AMOUNT | `3 lakhs` | "Perfect choice - Personal Loan! 👍 How much are you looking to borrow?" |
| 4. CITY | `Delhi` | "Got it! ₹3,00,000 - I've noted that down ✅ Which city do you currently reside in?" |
| 5. EMPLOYMENT_TYPE | `self employed` | "Great, Delhi is well-covered! 📍 One quick question - are you salaried or self-employed?" |
| 6. NAME | `Priya Sharma` | "Excellent! Now, may I have your full name exactly as it appears on your PAN card? 📝" |
| 7. MOBILE | `9123456781` | "Thank you, Priya Sharma! 😊 Please share your 10-digit mobile number." |
| 8. OTP | `123456` | "📱 OTP sent to your mobile! Please check your messages and enter the 6-digit verification code." |
| 9. KYC | `MNOPQ9012R` | "Wonderful! Your mobile number is verified ✅ Now I need your PAN number for identity verification." |
| 10. OFFER_DISCUSSION | `okay` | "🎉 Fantastic news, Priya Sharma! Based on your profile, you're pre-approved for up to ₹3,00,000! 🎊" |
| 11. TENURE_SELECTION | `36 months` | "Great! Now let's choose a repayment plan that works for you 📅" |
| 12. UNDERWRITING | *automatic* | "Your application is being processed... ⏳ Our underwriting team is reviewing your profile." |
| 13. REJECTION | *automatic* | "I'm really sorry, Priya Sharma 😔 Unfortunately, we couldn't approve your loan application at this time based on our eligibility criteria. You're welcome to reapply after 6 months." |

**Expected Final State:**
- ❌ Rejection reason: `CREDIT_CRITERIA_NOT_MET`
- ❌ Message: Generic ("eligibility criteria not met")
- ❌ **NEVER mentions credit score**

---

### ⚠️ **Scenario 3: REJECTED - Amount Exceeds Limit (Amit Verma)**
**Credit Score: 720 | Pre-approved: ₹5L | Requested: ₹8L | Expected: REJECTION**

| Stage | Input | Expected Bot Response |
|-------|-------|----------------------|
| 1. GREETING | `Hi there` | "Hi there! 👋 Welcome to Tata Capital. I'm here to help you get a personal loan quickly and hassle-free. Are you looking for a loan today?" |
| 2. PURPOSE | `business loan` | "Wonderful! 😊 I'd love to help you out. Could you tell me what you need the loan for?" |
| 3. AMOUNT | `8 lakhs` | "Perfect choice - Business Loan! 👍 How much are you looking to borrow?" |
| 4. CITY | `Bangalore` | "Got it! ₹8,00,000 - I've noted that down ✅ Which city do you currently reside in?" |
| 5. EMPLOYMENT_TYPE | `salaried` | "Great, Bangalore is well-covered! 📍 One quick question - are you salaried or self-employed?" |
| 6. NAME | `Amit Verma` | "Excellent! Now, may I have your full name exactly as it appears on your PAN card? 📝" |
| 7. MOBILE | `9988776655` | "Thank you, Amit Verma! 😊 Please share your 10-digit mobile number." |
| 8. OTP | `123456` | "📱 OTP sent to your mobile! Please check your messages and enter the 6-digit verification code." |
| 9. KYC | `GHIJK5678M` | "Wonderful! Your mobile number is verified ✅ Now I need your PAN number for identity verification." |
| 10. OFFER_DISCUSSION | `yes` | "🎉 Fantastic news, Amit Verma! Based on your profile, you're pre-approved for up to ₹5,00,000! 🎊" |
| 11. TENURE_SELECTION | `48 months` | "Great! Now let's choose a repayment plan that works for you 📅" |
| 12. UNDERWRITING | *automatic* | "Your application is being processed... ⏳ Our underwriting team is reviewing your profile." |
| 13. REJECTION | *automatic* | "I'm really sorry, Amit Verma 😔 Unfortunately, we couldn't approve your loan application at this time based on our eligibility criteria. You're welcome to reapply after 6 months." |

**Expected Final State:**
- ❌ Rejection reason: `AMOUNT_EXCEEDS_ELIGIBILITY`
- ❌ Message: Generic ("eligibility criteria not met")
- ❌ **NEVER mentions exact limit**

---

## 🧪 Edge Case Testing

### Test 4: Out-of-Order Input (Should be IGNORED)

```
Stage: AMOUNT (asking for loan amount)
User Input: "My PAN is ABCDE1234F"
Expected: Bot IGNORES PAN, RE-ASKS for amount
```

**Verification:**
- ✅ PAN is not stored at AMOUNT stage
- ✅ Bot repeats: "Got it - [Purpose]! 👍 How much do you need? (e.g., 5 lakhs)"
- ✅ Stage does NOT advance

---

### Test 5: Invalid OTP (3 attempts freeze)

```
Stage: OTP (asking for OTP)
Attempt 1: "999999" → Wrong OTP, retry
Attempt 2: "888888" → Wrong OTP, retry
Attempt 3: "777777" → Session FROZEN
Expected: "Too many incorrect attempts. Session locked."
```

**Verification:**
- ✅ Session frozen after 3 wrong attempts
- ✅ Cannot continue journey
- ✅ Must start new session

---

### Test 6: Invalid Tenure (Should not advance)

```
Stage: TENURE_SELECTION (asking for tenure)
User Input: "18 months"
Expected: Bot rejects (only 12/24/36/48 allowed), re-asks
```

**Verification:**
- ✅ Invalid tenure rejected
- ✅ Bot says: "Choose your EMI tenure: • 12 months • 24 months • 36 months • 48 months"
- ✅ Stage does NOT advance

---

### Test 7: Cross-User PAN (IDENTITY MISMATCH)

```
Stage 1-7: User provides mobile 9876543210
Stage 8: OTP verified → Identity LOCKED for Rahul Mehta
Stage 9: User provides PAN "MNOPQ9012R" (belongs to Priya Sharma)
Expected: HALTED - "Verification issue. Contact support."
```

**Verification:**
- ✅ Identity mismatch detected
- ✅ Session halted immediately
- ✅ Admin dashboard shows: `CROSS_USER_DOCUMENT`

---

## 🔄 Multi-Step Loading States

The chatbot shows realistic loading states during processing:

### KYC Verification (4 seconds total)
```
1. "Connecting to NSDL server..."
2. "Fetching KYC records..."
3. "Verifying PAN details..."
4. "Fetching customer profile..."
5. "Validating identity..."
6. "Finalizing verification..."
```

### Offer Generation (5 seconds total)
```
1. "Connecting to Credit Bureau API..."
2. "Fetching credit history..."
3. "Connecting to Offer Mart server..."
4. "Calculating eligibility..."
5. "Fetching customer profile from CRM..."
6. "Generating personalized offer..."
```

### Underwriting (6 seconds total)
```
1. "Connecting to underwriting engine..."
2. "Analyzing credit profile..."
3. "Verifying income details..."
4. "Checking debt-to-income ratio..."
5. "Running risk assessment..."
6. "Generating final decision..."
7. "Preparing loan documents..."
```

---

## 📊 Admin Dashboard Verification

After each test scenario, verify admin dashboard shows:

**For Approved Application:**
```json
{
  "application_id": "APP-20260201-XXXXXXXX",
  "stage": {
    "current_stage": "SANCTION",
    "stage_number": 13,
    "progress_percent": 100,
    "is_terminal": true
  },
  "kyc": {
    "otp_verified": true,
    "pan_verified": true,
    "identity_locked": true
  },
  "decision": {
    "underwriting_result": "APPROVED",
    "rejection_reason": null
  }
}
```

**For Rejected Application:**
```json
{
  "stage": {
    "current_stage": "REJECTION",
    "is_terminal": true
  },
  "decision": {
    "underwriting_result": "REJECTED",
    "rejection_reason": "CREDIT_CRITERIA_NOT_MET"
  }
}
```

---

## 🔍 What to Verify

### ✅ Flow is Strictly Linear
- [ ] Cannot skip stages
- [ ] Out-of-order input is ignored
- [ ] Stage advances only when required data collected

### ✅ No File Upload Exists
- [ ] No "upload document" button in UI
- [ ] `income_source` always shows "CUSTOMER_DATABASE"
- [ ] Income comes from mock_data.py

### ✅ EMI is Tenure-Based
- [ ] EMI NOT shown at OFFER stage
- [ ] EMI calculated ONLY after tenure selection
- [ ] Different tenures show different EMIs

### ✅ Interest is a Range
- [ ] Offer shows: "10.5% to 18% per annum"
- [ ] Final rate set after underwriting
- [ ] Based on credit score (not user input)

### ✅ Decisions are Deterministic
- [ ] Credit < 700 → Always reject
- [ ] Credit ≥ 700 → Continue to amount check
- [ ] Amount > limit → Reject
- [ ] Same input = same output (always)

### ✅ Admin Always Matches Chat
- [ ] Admin dashboard stage = chat stage
- [ ] Admin shows exact backend state
- [ ] No "inferred" or "guessed" values

### ✅ LLM Cannot Hallucinate
- [ ] LLM NEVER mentions credit score
- [ ] LLM NEVER calculates EMI
- [ ] LLM NEVER decides approval/rejection
- [ ] Backend controls all logic

---

## 🎨 Test User Database

| Name | Mobile | PAN | Credit Score | Pre-approved | Expected |
|------|--------|-----|--------------|--------------|----------|
| Rahul Mehta | 9876543210 | ABCDE1234F | 750+ | ₹10,00,000 | ✅ APPROVED |
| Amit Verma | 9988776655 | GHIJK5678M | 720 | ₹5,00,000 | ⚠️ Amount-dependent |
| Priya Sharma | 9123456781 | MNOPQ9012R | 650 | ₹3,00,000 | ❌ REJECTED |

**OTP for all test users:** `123456`

---

## 🚀 Quick Start

1. **Start Backend:** `cd src/backend && python3 main.py`
2. **Start Frontend:** `npm run dev`
3. **Open Chat:** http://localhost:5173
4. **Open Admin:** http://localhost:5173/admin
5. **Run Test:** Follow Scenario 1 inputs above
6. **Verify:** Check admin dashboard matches backend state

---

## ✅ Success Criteria

All 121 tests pass:
```bash
cd src/backend
python3 -m pytest test_deterministic_flow.py -v
```

Expected output:
```
============================= 121 passed in 0.19s ==============================
```
