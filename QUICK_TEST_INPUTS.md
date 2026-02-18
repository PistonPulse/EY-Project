# Quick Test Inputs — Copy & Paste

Use these exact inputs to test the 3 loan outcomes. Start a **new chat session** for each test.

---

## ✅ TEST 1: APPROVED (Priya Sharma)

| Stage | What to Type |
|-------|-------------|
| Greeting | `Hi` |
| Purpose | `home renovation` |
| Amount | `5 lakhs` |
| City | `Mumbai` |
| Employment | `salaried` |
| Name | `Priya Sharma` |
| Mobile | `9876543210` |
| OTP | `123456` |
| Monthly Income | `1.5 lakh` |
| Existing EMI | `0` |
| Age (DOB) | `30` |
| PAN | `ABCDE1234F` |
| Offer | `yes I agree` |
| Tenure | `36 months` |
| Underwriting | *(wait for auto-trigger or type anything)* |

**Expected:** Score ≈ 850+ → **APPROVED** → Sanction letter generated

---

## ⚠️ TEST 2: CONDITIONAL (Amit Patel)

| Stage | What to Type |
|-------|-------------|
| Greeting | `Hello` |
| Purpose | `personal expenses` |
| Amount | `5 lakhs` |
| City | `Pune` |
| Employment | `self employed` |
| Name | `Amit Patel` |
| Mobile | `9988776655` |
| OTP | `123456` |
| Monthly Income | `55000` |
| Existing EMI | `15000` |
| Age (DOB) | `48` |
| PAN | `GHIJK5678M` |
| Offer | `ok` |
| Tenure | `48 months` |
| Underwriting | *(wait or type anything)* |

**Expected:** Score ≈ 660 → **CONDITIONAL** (may need extra docs)

---

## ❌ TEST 3: REJECTED (Suresh Prasad)

| Stage | What to Type |
|-------|-------------|
| Greeting | `Hello` |
| Purpose | `medical treatment` |
| Amount | `8 lakhs` |
| City | `Patna` |
| Employment | `self employed` |
| Name | `Suresh Prasad` |
| Mobile | `9123456781` |
| OTP | `123456` |
| Monthly Income | `28000` |
| Existing EMI | `12000` |
| Age (DOB) | `62` |
| PAN | `MNOPQ9012R` |
| Offer | `proceed` |
| Tenure | `24 months` |
| Underwriting | *(wait or type anything)* |

**Expected:** Score ≈ 400 → **REJECTED** (high DTI + low income + age risk)

---

## 🔒 TEST 4: OTP Failure (Security Lock)

| Stage | What to Type |
|-------|-------------|
| Greeting | `Hi` |
| Purpose | `personal` |
| Amount | `5 lakhs` |
| City | `Delhi` |
| Employment | `salaried` |
| Name | `Test User` |
| Mobile | `9876543210` |
| OTP (attempt 1) | `000000` ← wrong |
| OTP (attempt 2) | `111111` ← wrong |
| OTP (attempt 3) | `222222` ← wrong |

**Expected:** Session locked → *"Verification attempts exceeded"*

---

## 📝 Income Format Tips

| You Type | System Reads |
|----------|-------------|
| `1 lakh` | ₹1,00,000/mo |
| `1.5 lakh` | ₹1,50,000/mo |
| `50000` | ₹50,000/mo |
| `50k` | ₹50,000/mo |
| `80 thousand` | ₹80,000/mo |
| `6 lakh per annum` | ₹50,000/mo |

> **Note:** All amounts in lakhs are treated as **monthly** unless you say "per annum".
