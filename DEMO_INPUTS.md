# 🎬 Demo Inputs - Complete Workflow Guide

---

## 🌟 Scenario 1: Priya Sharma (Instant Approval - Excellent Credit)

### **Step 1: Initial Contact**
```
Hi I am Priya and my phone is 9876543210
```
**Expected**: Agent shows credit score 785/900 (EXCELLENT) and pre-approved limit ₹10L  
**Dashboard**: Trust Score starts at 65, Risk: LOW

---

### **Step 2: Loan Amount Request**
```
5 lakhs for home renovation
```
**Expected**: Agent offers 11.99% rate, EMI ₹16,643/month  
**Dashboard**: Trust Score → 67

---

### **Step 3-6: Rate Negotiation** (Say "better rate" or "can you lower it?" each time)
- **Input**: `Can you give me a better rate?`
  - **Response**: Rate drops to 11.49%
  - **Dashboard**: Trust Score → 69, 71, 73, 75 (increases with each negotiation)

- **Input**: `Still high, anything lower?`
  - **Response**: Rate drops to 10.99%

- **Input**: `One more try please`
  - **Response**: Rate drops to 10.75%

- **Input**: `Final best offer?`
  - **Response**: **FINAL RATE: 10.25%** + Upload button appears
  - **Dashboard**: Trust Score → 75

---

### **Step 7-9: Document Upload**
**Upload these 3 documents** (click 📎 Upload Document button):
1. `demo_documents/scenario_1_priya_approval/Priya_Sharma_PAN_Card.pdf`
2. `demo_documents/scenario_1_priya_approval/Priya_Sharma_Salary_Slip_Nov_2025.pdf`
3. `demo_documents/scenario_1_priya_approval/Priya_Sharma_Bank_Statement_Oct_Nov_2025.pdf`

**Expected After Each Upload**:
- Document 1: Trust Score → 78, verification starts
- Document 2: Trust Score → 82, income verified
- Document 3: Trust Score → 90, **LOAN APPROVED!** 🎉

---

### **Step 10: Download Sanction Letter**
**Expected**: Green "Download Sanction Letter" button appears  
**Action**: Click to download PDF with loan details  
**Dashboard**: Risk: LOW, Behavioral Score: 95/100, Status: APPROVED

---

## 💼 Scenario 2: Amit Patel (Conditional Approval - Fair Credit)

### **Step 1: Initial Contact**
```
Hi I am Amit and my phone is 9123456789
```
**Expected**: Agent shows credit score 680/900 (FAIR) and pre-approved limit ₹6L  
**Dashboard**: Trust Score starts at 55, Risk: MEDIUM

---

### **Step 2: Loan Amount Request**
```
8 lakhs for wedding
```
**Expected**: Agent adjusts to ₹6.5L (max limit), offers 13.99% rate  
**Dashboard**: Trust Score → 57

---

### **Step 3-6: Rate Negotiation** (Say "better" or "lower rate" each time)
- **Input**: `Can you give me a better rate?`
  - **Response**: Rate drops to 13.49%
  - **Dashboard**: Trust Score → 59, 61, 63, 65

- **Input**: `Still high, can you reduce more?`
  - **Response**: Rate drops to 12.99%

- **Input**: `Try one more time?`
  - **Response**: Rate drops to 12.49%

- **Input**: `Best possible rate?`
  - **Response**: **FINAL RATE: 12.25%** + Upload button appears
  - **Dashboard**: Trust Score → 65

---

### **Step 7-9: Document Upload**
**Upload these 3 documents** (click 📎 Upload Document button):
1. `demo_documents/scenario_2_amit_conditional/Amit_Patel_Salary_Slip_Nov_2025.pdf`
2. `demo_documents/scenario_2_amit_conditional/Amit_Patel_Bank_Statement_Oct_Nov_2025.pdf`
3. `demo_documents/scenario_2_amit_conditional/Amit_Patel_CIBIL_Report.pdf`

**Expected After Each Upload**:
- Document 1: Trust Score → 68, salary verification
- Document 2: Trust Score → 70, banking history verified
- Document 3: Trust Score → 75, **CONDITIONALLY APPROVED!** ⚠️

---

### **Step 10: Download Sanction Letter** ✨ NEW!
**Expected**: Green "Download Sanction Letter" button appears  
**Action**: Click to download PDF with conditional approval terms  
**Dashboard**: Risk: MEDIUM, Behavioral Score: 82/100, Status: APPROVED_CONDITIONAL

**Conditions**: First 3 EMIs auto-debit required, credit monitoring active

---

## 🚨 Scenario 3: Rajesh Kumar (Fraud Rejection - Poor Credit)

### **Step 1: Initial Contact**
```
Hi I am Rajesh and my phone is 9988776655
```
**Expected**: Agent shows credit score 350/900 (VERY POOR), HIGH RISK warning  
**Dashboard**: Trust Score starts at 35, Risk: HIGH

---

### **Step 2: Loan Amount Request + IMMEDIATE FRAUD ALERT** 🚨
```
15 lakhs urgently, business purpose, self-employed, 2.5 lakhs monthly
```

**Expected**:  
🚨 **CRITICAL ALERTS DETECTED:**
- NPCI Fraud Database: Phone FLAGGED
- Multiple Applications: 8 different NBFCs in 30 days
- Identity Theft Reports: 2 cases linked
- Credit Score: 350 (VERY POOR)
- Active Defaults: ₹3,45,000 outstanding
- Loan Shopping Pattern: 15 inquiries in 90 days

**Upload button appears immediately** (no negotiation offered)  
**Dashboard**: Trust Score drops to 25, Risk: CRITICAL

---

### **Step 3-4: Document Upload (Fraud Detection)**
**Upload ANY 2 documents** (system will detect tampering):
1. Any PDF as "PAN Card"
2. Any PDF as "CIBIL Report"

**Expected After Each Upload**:
- Document 1: Trust Score → 20, "Photo quality suspicious, metadata shows tampering"
- Document 2: Trust Score → 10, **APPLICATION REJECTED - FRAUD CONFIRMED** ❌

**Dashboard**: Risk: FRAUD_CONFIRMED, Behavioral Score: 15/100, Status: REJECTED

---

### **Final Response**:
```
❌ LOAN APPLICATION REJECTED

Rejection Reasons:
1. Document tampering detected
2. NPCI fraud database match
3. Multiple simultaneous loan attempts
4. Identity verification failed
5. Credit score 350/900 with active defaults
6. Outstanding debt: ₹3,45,000

Case flagged for investigation and reported to:
• NPCI Fraud Prevention Team
• Credit Bureau Authorities
• Law Enforcement (if required)
```

---

## 📊 Dashboard Metrics (Real-Time Updates)

### **Priya Sharma (LOW RISK)**
- Trust Score: 65 → 90 (increases throughout)
- Behavioral Score: 70 → 95
- Risk Category: LOW → LOW
- Document Authenticity: PENDING → VERIFIED
- Conversation Quality: EXCELLENT

### **Amit Patel (MEDIUM RISK)**
- Trust Score: 55 → 75 (increases with documents)
- Behavioral Score: 65 → 82
- Risk Category: MEDIUM → MEDIUM
- Document Authenticity: PENDING → UNDER_REVIEW
- Conversation Quality: GOOD

### **Rajesh Kumar (CRITICAL/FRAUD)**
- Trust Score: 35 → 10 (decreases as fraud detected)
- Behavioral Score: 40 → 15
- Risk Category: HIGH → CRITICAL → FRAUD_CONFIRMED
- Document Authenticity: PENDING → SUSPICIOUS
- Conversation Quality: POOR

---

## 🎯 Quick Reference Table

| Scenario | Phone | Credit | Initial Offer | Negotiation | Final Rate | Documents | Outcome |
|----------|-------|--------|---------------|-------------|------------|-----------|---------|
| **Priya** | 9876543210 | 785 (Excellent) | 11.99% | 5 rounds | 10.25% | 3 docs | ✅ APPROVED + Sanction Letter |
| **Amit** | 9123456789 | 680 (Fair) | 13.99% | 5 rounds | 12.25% | 3 docs | ⚠️ CONDITIONAL + Sanction Letter |
| **Rajesh** | 9988776655 | 350 (Poor) | N/A | None | N/A | 2 docs | ❌ REJECTED - FRAUD |

---

## 💡 Tips for Demo

1. **Between Scenarios**: Click ↻ Reset button in chat header to clear session
2. **Watch Dashboard**: Admin dashboard shows real-time agent network and trust scores updating
3. **Negotiation**: For Priya/Amit, say "better", "lower", "reduce" to trigger rate drops
4. **Documents**: Upload any PDF files - system accepts all uploads in demo mode
5. **Sanction Letters**: Click green download button after approval (Priya & Amit only)
6. **Fraud Flow**: Rajesh scenario shows immediate fraud detection without negotiation

---

**🚀 Ready to demo? Start with Priya for the success story!**
