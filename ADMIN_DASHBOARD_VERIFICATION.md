# 🎯 Admin Dashboard Verification Guide

## Overview
This guide ensures all admin dashboard elements properly reflect the 3 demo scenarios (Priya, Amit, Rajesh).

---

## ✅ Scenario 1: Priya Sharma (APPROVAL)

### Customer Profile
- **Name**: Priya Sharma
- **Phone**: 9876543210
- **Credit Score**: 785

### Trust Score Progression
| Step | Trust Score | Behavioral Score | Risk Category | Doc Status | Conv Quality |
|------|-------------|------------------|---------------|------------|--------------|
| Step 1 | 65 | 70 | LOW | PENDING | EXCELLENT |
| Step 2 | 67 | 73 | LOW | PENDING | EXCELLENT |
| Step 3 | 69 | 76 | LOW | PENDING | EXCELLENT |
| Step 4 | 71 | 79 | LOW | PENDING | EXCELLENT |
| Step 5 | 73 | 82 | LOW | PENDING | EXCELLENT |
| Step 6 | 75 | 85 | LOW | PENDING | EXCELLENT |
| Doc 1 | 78 | 82 | LOW | PENDING | EXCELLENT |
| Doc 2 | 82 | 88 | LOW | PENDING | EXCELLENT |
| Doc 3 | **90** | **95** | LOW | **VERIFIED** | EXCELLENT |

### Agent Network Progression
1. **Step 1**: Master Agent → Verification Agent → Master Agent
2. **Step 2**: Master Agent → Sales Agent
3. **Steps 3-6**: Sales Agent ↔ Underwriting Agent (negotiation)
4. **Doc Upload**: Verification Agent (active during document processing)
5. **Final Approval**: Underwriting Agent → Sanction Letter Generator

### Expected Admin Logs
- ✅ Master Agent: Customer inquiry initiated
- ✅ Verification Agent: Credit Score 785 (EXCELLENT)
- ✅ Sales Agent: Initial rate quoted 11.99%
- ✅ Underwriting Agent: Rate reductions during negotiation
- ✅ Verification Agent: Document verification messages
- ✅ Underwriting Agent: APPROVAL GRANTED
- ✅ Sanction Letter Generator: Letter ready for download

### Visual Indicators
- **Trust Score Gauge**: Light blue background arc (#E0E7FF)
- **Risk Category Badge**: Green text (LOW)
- **Behavioral Score**: Green text (95/100)
- **Doc Status**: Green text (VERIFIED)
- **Conversation Quality**: Green text (EXCELLENT)
- **Active Agent Nodes**: Blue border with pulse animation
- **Customer Name Header**: "Customer: Priya Sharma" in Agent Network

---

## ⚠️ Scenario 2: Amit Patel (CONDITIONAL APPROVAL)

### Customer Profile
- **Name**: Amit Patel
- **Phone**: 9123456789
- **Credit Score**: 680

### Trust Score Progression
| Step | Trust Score | Behavioral Score | Risk Category | Doc Status | Conv Quality |
|------|-------------|------------------|---------------|------------|--------------|
| Step 1 | 55 | 65 | MEDIUM | PENDING | GOOD |
| Step 2 | 57 | 67 | MEDIUM | PENDING | GOOD |
| Step 3 | 59 | 69 | MEDIUM | PENDING | GOOD |
| Step 4 | 61 | 71 | MEDIUM | PENDING | GOOD |
| Step 5 | 63 | 73 | MEDIUM | PENDING | GOOD |
| Step 6 | 65 | 75 | MEDIUM | PENDING | GOOD |
| Doc 1 | 68 | 72 | MEDIUM | UNDER_REVIEW | GOOD |
| Doc 2 | 70 | 76 | MEDIUM | UNDER_REVIEW | GOOD |
| Doc 3 | **75** | **82** | MEDIUM | **UNDER_REVIEW** | GOOD |

### Agent Network Progression
1. **Step 1**: Master Agent → Verification Agent → Master Agent
2. **Step 2**: Master Agent → Sales Agent → Underwriting Agent (limit adjustment)
3. **Steps 3-6**: Sales Agent ↔ Underwriting Agent (negotiation)
4. **Doc Upload**: Verification Agent (active during processing)
5. **Conditional Approval**: Underwriting Agent → Sanction Letter Generator

### Expected Admin Logs
- ⚠️ Master Agent: Customer inquiry
- ⚠️ Verification Agent: Credit Score 680 (FAIR)
- ⚠️ Underwriting Agent: Exceeds pre-approved limit
- ⚠️ Underwriting Agent: Adjusted to ₹6,50,000
- ⚠️ Sales Agent: Rate reductions during negotiation
- ⚠️ Verification Agent: Document verification
- ⚠️ Underwriting Agent: EMI burden 44% (acceptable)
- ✅ Underwriting Agent: CONDITIONALLY APPROVED
- ✅ Sanction Letter Generator: Letter generated

### Visual Indicators
- **Trust Score Gauge**: Light blue background arc (#E0E7FF)
- **Risk Category Badge**: Amber/Orange text (MEDIUM)
- **Behavioral Score**: Blue/Green text (82/100)
- **Doc Status**: Blue text (UNDER_REVIEW)
- **Conversation Quality**: Blue text (GOOD)
- **Active Agent Nodes**: Blue border with pulse animation
- **Customer Name Header**: "Customer: Amit Patel" in Agent Network

---

## 🚨 Scenario 3: Rajesh Kumar (FRAUD REJECTION)

### Customer Profile
- **Name**: Rajesh Kumar
- **Phone**: 9988776655
- **Credit Score**: 350

### Trust Score Progression
| Step | Trust Score | Behavioral Score | Risk Category | Doc Status | Conv Quality |
|------|-------------|------------------|---------------|------------|--------------|
| Step 1 | 35 | 40 | HIGH | PENDING | POOR |
| Step 2 | 25 | 28 | CRITICAL | PENDING | POOR |
| Doc 1 | 20 | 22 | CRITICAL | SUSPICIOUS | POOR |
| Doc 2 | **10** | **15** | **FRAUD_CONFIRMED** | **SUSPICIOUS** | POOR |

### Agent Network Progression
1. **Step 1**: Master Agent → Verification Agent (HIGH RISK detected)
2. **Step 2**: Master Agent → Sales Agent → Verification Agent (FRAUD ALERTS)
3. **Doc Upload**: Verification Agent (document tampering detection)
4. **Rejection**: Underwriting Agent → REJECTED

### Expected Admin Logs
- 🚨 Master Agent: Customer inquiry: Rajesh Kumar
- 🚨 Verification Agent: Credit Score 350 (VERY POOR)
- 🚨 Master Agent: HIGH RISK - Enhanced verification needed
- 🚨 Sales Agent: Request ₹15,00,000 (HIGH AMOUNT)
- 🚨 Verification Agent: Running fraud checks
- 🚨 Verification Agent: NPCI FRAUD ALERT: ACTIVE
- 🚨 Verification Agent: Phone flagged across 8 NBFCs
- 🚨 Verification Agent: Document tampering suspected
- ❌ Underwriting Agent: APPLICATION REJECTED - FRAUD

### Visual Indicators
- **Trust Score Gauge**: Light blue background arc (#E0E7FF), score 10/100
- **Risk Category Badge**: Dark Red text (FRAUD_CONFIRMED)
- **Behavioral Score**: Red text (15/100)
- **Doc Status**: Red text (SUSPICIOUS)
- **Conversation Quality**: Red text (POOR)
- **Active Agent Nodes**: Blue border (normal activation, no special fraud styling)
- **Customer Name Header**: "Customer: Rajesh Kumar" in Agent Network

---

## 🔍 Verification Checklist

### Before Demo
- [ ] Backend server running (`uvicorn main:app --reload` on port 8000)
- [ ] Frontend server running (`npm run dev` on port 5173)
- [ ] Admin dashboard accessible at `http://localhost:5173/admin`
- [ ] Login working with credentials (admin@tatacapital.com / admin123)

### During Priya Demo
- [ ] Customer name "Priya Sharma" appears in Agent Network header (Step 1)
- [ ] Credit Score shows 785
- [ ] Trust Score starts at 65
- [ ] Trust Score increments: 67→69→71→73→75→78→82→90
- [ ] Risk Category stays "LOW" (green)
- [ ] Conversation Quality shows "EXCELLENT" (green)
- [ ] Agent nodes light up blue during conversation
- [ ] Master Agent → Sales Agent → Verification Agent → Underwriting Agent flow
- [ ] Final status: Doc Status "VERIFIED" (green)
- [ ] Behavioral Score reaches 95/100

### During Amit Demo
- [ ] Customer name "Amit Patel" appears in Agent Network header (Step 1)
- [ ] Credit Score shows 680
- [ ] Trust Score starts at 55
- [ ] Trust Score increments: 57→59→61→63→65→68→70→75
- [ ] Risk Category stays "MEDIUM" (amber)
- [ ] Conversation Quality shows "GOOD" (blue)
- [ ] Agent nodes light up during conversation
- [ ] Underwriting adjusts loan amount (₹8L → ₹6.5L)
- [ ] Final status: Doc Status "UNDER_REVIEW" (blue)
- [ ] Behavioral Score reaches 82/100

### During Rajesh Demo
- [ ] Customer name "Rajesh Kumar" appears in Agent Network header (Step 1)
- [ ] Credit Score shows 350
- [ ] Trust Score starts at 35
- [ ] Trust Score decreases: 35→25→20→10
- [ ] Risk Category progresses: HIGH → CRITICAL → FRAUD_CONFIRMED (red)
- [ ] Conversation Quality shows "POOR" (red)
- [ ] FRAUD ALERTS appear in admin logs (🚨 emojis)
- [ ] Doc Status shows "SUSPICIOUS" (red)
- [ ] Behavioral Score drops to 15/100
- [ ] Final message: APPLICATION REJECTED

### WebSocket Connection
- [ ] WebSocket connects to `ws://localhost:8000/admin/stream`
- [ ] Browser console shows: "🎯 Agent Active Event: sales"
- [ ] Browser console shows: "✅ Active agent updated to: sales"
- [ ] Browser console shows: "👤 Customer Identified: Priya Sharma"
- [ ] Admin logs broadcast in real-time
- [ ] Trust scores update in real-time
- [ ] Customer profile updates immediately on Step 1

### Common Issues
1. **Customer name not showing**: Check WebSocket `customer_identified` broadcast
2. **Trust score not updating**: Check backend trust score calculations
3. **Agents not highlighting**: Check `agent_active` broadcasts and frontend ID mapping
4. **Wrong colors**: Check CSS classes for risk categories and statuses
5. **Trust gauge black arc**: Should be light blue (#E0E7FF), not black (#1e293b)

---

## 🎨 Color Reference

### Risk Categories
- **LOW**: `text-green-600` (#16A34A)
- **MEDIUM**: `text-amber-600` (#D97706)
- **HIGH**: `text-red-600` (#DC2626)
- **CRITICAL**: `text-red-700` (#B91C1C)
- **FRAUD_CONFIRMED**: `text-red-900` (#7F1D1D)

### Doc Status
- **VERIFIED**: `text-green-600` (#16A34A)
- **UNDER_REVIEW**: `text-blue-600` (#2563EB)
- **SUSPICIOUS**: `text-red-600` (#DC2626)
- **PENDING**: `text-gray-500` (#6B7280)

### Conversation Quality
- **EXCELLENT**: `text-green-600` (#16A34A)
- **GOOD**: `text-blue-600` (#2563EB)
- **POOR**: `text-red-600` (#DC2626)

### Primary Colors
- **Tata Capital Dark Blue**: `#004589`
- **Tata Capital Bright Blue**: `#3B82F6`
- **Trust Gauge Background**: `#E0E7FF` (light blue)
- **White Backgrounds**: `bg-white`
- **Gray Borders**: `border-gray-200`

---

## 🚀 Quick Test Commands

### Test Priya (Success)
```
Hi I am Priya and my phone is 9876543210
```

### Test Amit (Conditional)
```
Hi I am Amit and my phone is 9123456789
```

### Test Rajesh (Fraud)
```
Hi I am Rajesh and my phone is 9988776655
```

---

**Last Updated**: Dec 16, 2025  
**Status**: All 3 scenarios fully hardcoded and tested
