"""
TataSmartAgent - LangGraph State Machine
Implements the Agentic AI Loan Officer using LangGraph with Google Gemini
"""

import os
import json
import re
from typing import TypedDict, Annotated, Literal, Optional, Dict, Any, List
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field

from mock_data import MockDataProvider

# =========================================================
# ⚙️ SYSTEM CONFIGURATION - DUAL MODE ARCHITECTURE
# =========================================================
# Set to TRUE for Hackathon Demo (Scripted Mode - 100% Reliable)
# Set to FALSE for Production (Real Gemini AI - Full Intelligence)
# =========================================================
DEMO_MODE = True

# When DEMO_MODE = True:
# - Uses pre-scripted flows for phone number triggers
# - Zero API costs, zero latency, zero failure risk
# - Perfect for stage presentations
#
# When DEMO_MODE = False:
# - Uses real Gemini 1.5 Flash API for AI processing
# - Natural language understanding
# - Full production-grade intelligence
# =========================================================

# ==================== DEMO SCRIPTED MODE ====================
# HUMANIZED MULTI-AGENT DEMO WITH NEGOTIATION - Friendly conversation with rate bargaining
DEMO_SCRIPTS = {
    "priya_sharma": {
        "triggers": ["priya", "9876543210"],
        "required_docs": 3,
        "negotiation_rates": [11.99, 11.49, 10.99, 10.75, 10.5, 10.25],  # 6 rates from high to low
        "final_rate": 10.25,  # Absolute minimum
        "conversation": [
            {
                "step": 1,
                "trigger_keywords": ["priya", "9876543210"],
                "response": "Hey Priya! 👋 Great to hear from you!\n\nLet me quickly pull up your details... *typing*\n\n⏳ Connecting to our customer database...\n⏳ Fetching your credit profile...\n\nAh perfect! I found you in our system! 🎉\n\n**Your Profile:**\n• Name: Priya Sharma  \n• Phone: 9876543210  \n• Credit Score: **785/900** (That's excellent! 🌟)\n• Pre-approved Limit: ₹10,00,000\n\nWow, you've got an amazing credit history! This is really going to help speed things up.\n\nSo tell me - how much are you looking to borrow? And what's it for, if you don't mind me asking? 😊",
                "decision": "INITIAL",
                "show_upload": False,
                "extracted": {"name": "Priya Sharma", "phone": "9876543210"},
                "admin_logs": [
                    {"agent": "Master Agent", "message": "→ Customer inquiry initiated: Priya Sharma", "type": "info"},
                    {"agent": "Master Agent", "message": "→ Routing to Verification Agent", "type": "info"},
                    {"agent": "Verification Agent", "message": "✓ CRM database lookup: SUCCESS", "type": "success"},
                    {"agent": "Verification Agent", "message": "✓ Credit Score: 785/900 (EXCELLENT)", "type": "success"},
                    {"agent": "Verification Agent", "message": "→ Returning to Master Agent", "type": "info"}
                ]
            },
            {
                "step": 2,
                "trigger_keywords": ["5", "500000", "five", "lakh", "loan", "need", "want"],
                "response": "₹5 lakhs - perfect! That's well within your pre-approved limit! 💪\n\n⏳ Let me route this to our Sales Team...\n⏳ Checking current market rates...\n\n**Initial Offer:**  \n💰 Amount: ₹5,00,000  \n📈 Interest Rate: **11.99% per annum**  \n⏰ Tenure: 36 months  \n💳 Monthly EMI: ₹16,643  \n📊 Processing Fee: 2% + GST\n\nThis is our standard rate for personal loans. Your EMI would be around **23% of your monthly income** - very comfortable!\n\nWhat do you think? Would you like to proceed with this, or would you like me to see if I can get you a better rate? 😊",
                "decision": "OFFER_MADE",
                "show_upload": False,
                "negotiation_stage": 1,
                "current_rate": 11.99,
                "extracted": {"loan_amount": 500000},
                "admin_logs": [
                    {"agent": "Master Agent", "message": "→ Routing to Sales Agent", "type": "info"},
                    {"agent": "Sales Agent", "message": "💰 Loan request: ₹5,00,000", "type": "info"},
                    {"agent": "Sales Agent", "message": "📊 Initial rate quoted: 11.99%", "type": "info"},
                    {"agent": "Sales Agent", "message": "⏳ Waiting for customer response", "type": "info"}
                ]
            },
            {
                "step": 3,
                "trigger_keywords": ["better", "lower", "less", "reduce", "nego", "can you", "discount"],
                "response": "I totally understand! Let me check what I can do for you... 🤔\n\n⏳ Consulting with my manager...\n⏳ Checking your credit profile again...\n\nOkay good news! Since you have such an excellent credit score (785), I managed to get approval for a better rate! 🎉\n\n**Revised Offer:**  \n💰 Amount: ₹5,00,000  \n📈 Interest Rate: **11.49% per annum** ⬇️  \n⏰ Tenure: 36 months  \n💳 Monthly EMI: ₹16,477  \n💵 **You save: ₹5,976 over the loan tenure!**\n\nThat's a savings of ₹166/month! Much better right?\n\nShall we go ahead with this? Or would you still like me to try for something even better? 😊",
                "decision": "OFFER_REVISED",
                "show_upload": False,
                "negotiation_stage": 2,
                "current_rate": 11.49,
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "💬 Customer negotiating rate", "type": "info"},
                    {"agent": "Sales Agent", "message": "→ Consulting underwriting for better rate", "type": "info"},
                    {"agent": "Underwriting Agent", "message": "✓ Approved rate reduction: 11.49%", "type": "success"},
                    {"agent": "Sales Agent", "message": "📊 Revised offer: 11.49%", "type": "success"}
                ]
            },
            {
                "step": 4,
                "trigger_keywords": ["better", "lower", "less", "reduce", "still", "more"],
                "response": "You drive a hard bargain! 😄 Let me see what else I can do...\n\n⏳ Checking with senior management...\n⏳ Reviewing your employment stability (3.5 years - excellent!)...\n\nAlright, I spoke to my senior, and because of your stable job and perfect credit history, we can offer:\n\n**Special Offer:**  \n💰 Amount: ₹5,00,000  \n📈 Interest Rate: **10.99% per annum** ⬇️  \n⏰ Tenure: 36 months  \n💳 Monthly EMI: ₹16,305  \n💵 **Total savings: ₹12,168 compared to initial offer!**\n\nThat's ₹338/month less! This is getting really competitive now.\n\nI think this is a great deal, but if you want, I can make one more attempt? Though I should warn you - we're approaching our floor rate here! 😅",
                "decision": "OFFER_REVISED",
                "show_upload": False,
                "negotiation_stage": 3,
                "current_rate": 10.99,
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "💬 Customer still negotiating", "type": "info"},
                    {"agent": "Sales Agent", "message": "→ Escalating to senior management", "type": "info"},
                    {"agent": "Underwriting Agent", "message": "✓ Approved special rate: 10.99%", "type": "success"},
                    {"agent": "Sales Agent", "message": "⚠️ Approaching minimum rate threshold", "type": "warning"}
                ]
            },
            {
                "step": 5,
                "trigger_keywords": ["better", "lower", "less", "reduce", "try", "one more"],
                "response": "Wow, you really know how to negotiate! Okay, let me pull out all the stops here... 💪\n\n⏳ Checking premium customer criteria...\n⏳ Reviewing market competitiveness...\n\nOkay Priya, you got me! This is our **absolute best offer** - I literally cannot go lower than this:\n\n**FINAL BEST OFFER:**  \n💰 Amount: ₹5,00,000  \n📈 Interest Rate: **10.25% per annum** ⬇️⬇️  \n⏰ Tenure: 36 months  \n💳 Monthly EMI: ₹16,134  \n💵 **Total savings: ₹18,324 from initial offer!**\n\nThis is the same rate we give to our VIP customers! You're saving ₹509/month compared to where we started.\n\n**This is as low as I can go** - if we go any lower, my manager will probably fire me! 😅\n\nSo, shall we move forward with this? I'll need 3 documents to process your approval:\n\n1️⃣ PAN Card  \n2️⃣ Recent Salary Slip  \n3️⃣ Last 2 months Bank Statement\n\nClick the 📎 button below to upload! 🚀",
                "decision": "FINAL_OFFER",
                "show_upload": True,
                "negotiation_stage": 4,
                "current_rate": 10.25,
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "🎯 FINAL OFFER: 10.25%", "type": "success"},
                    {"agent": "Sales Agent", "message": "⚠️ This is the absolute minimum rate", "type": "warning"},
                    {"agent": "Master Agent", "message": "→ Requesting document upload", "type": "info"}
                ]
            },
            {
                "step": 6,
                "trigger_keywords": ["better", "lower", "less", "reduce", "nego"],
                "response": "I really wish I could go lower, but I've genuinely hit our floor rate at 10.25%! 😔\n\nThis is literally the **lowest rate** we offer to anyone - even our own employees get this same rate!\n\nI've already given you:\n✅ 1.74% discount from our standard rate\n✅ VIP customer pricing\n✅ Savings of ₹18,324 over the loan\n\nIf I try to go lower, the system will automatically reject it (I've tried before, trust me! 😅)\n\nLet's lock in this amazing rate before it expires! Just upload your 3 documents and we'll get you approved today:\n\n1️⃣ PAN Card  \n2️⃣ Salary Slip  \n3️⃣ Bank Statement\n\nClick 📎 below to start! ⬇️",
                "decision": "FIRM_FINAL",
                "show_upload": True,
                "negotiation_stage": 5,
                "current_rate": 10.25,
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "💬 Customer attempting further negotiation", "type": "info"},
                    {"agent": "Sales Agent", "message": "✋ Holding firm at 10.25% (floor rate)", "type": "warning"},
                    {"agent": "Sales Agent", "message": "⏳ Encouraging document upload", "type": "info"}
                ]
            },
            {
                "step": 7,
                "docs_uploaded": 1,
                "response": "Perfect! Got your first document! 📄✅\n\nScanning document...\nVerifying authenticity...\n\nDocument 1 verified successfully!\n\nGreat progress! Just 2 more documents to go:\n\n📄 Still needed:\n• Salary Slip (Nov 2025)\n• Bank Statement (Last 2 months)\n\nPlease upload the next document using the 📎 button below!",
                "decision": "DOC_VERIFIED",
                "show_upload": True,
                "admin_logs": [
                    {"agent": "Master Agent", "message": "📄 Document 1/3 received", "type": "info"},
                    {"agent": "Verification Agent", "message": "⏳ Queued for verification", "type": "info"}
                ]
            },
            {
                "step": 8,
                "docs_uploaded": 2,
                "response": "Awesome! Document 2 received! 📄📄✅\n\nProcessing...\nCross-checking with our database...\n\nDocument 2 verified successfully!\n\nYou're almost there! Just 1 more document needed:\n\n📄 Last document:\n• Bank Statement (Oct-Nov 2025)\n\nUpload it using the 📎 button and we'll process your loan immediately!",
                "decision": "DOC_VERIFIED",
                "show_upload": True,
                "admin_logs": [
                    {"agent": "Master Agent", "message": "📄 Document 2/3 received", "type": "info"}
                ]
            },
            {
                "step": 9,
                "docs_uploaded": 3,
                "response": "Excellent! All 3 documents received! 📄📄📄✅\n\nRunning final verification checks...\nRouting to Verification Agent...\nExtracting PAN details...\n✅ PAN: ABCDE1234F - Verified!\n✅ Name matches perfectly!\n\nAnalyzing your Salary Slip...\n✅ Net Salary: Rs 73,500/month\n✅ Employer: Tech Solutions Pvt Ltd\n✅ Employment Duration: 3.5 years (Very stable!)\n\nReviewing Bank Statement...\n✅ Average Balance: Rs 1,45,000 (Impressive!)\n✅ Regular salary credits every month\n✅ No loan defaults or bounced checks\n✅ Healthy savings pattern!\n\nRouting to Underwriting Agent...\nRunning final eligibility check...\n\n✅ Identity: VERIFIED\n✅ Income: CONFIRMED\n✅ Credit Score: 785 (EXCELLENT)\n✅ EMI-to-Income Ratio: 22% (Very comfortable!)\n✅ Employment: STABLE\n✅ Banking Behavior: EXCELLENT\n\nOkay Priya, I've got some great news for you! 🎊\n\n🎉 LOAN APPROVED! 🎉\n\nYour Approved Loan:\n━━━━━━━━━━━━━━━━━━━━━━━\n💰 Amount: Rs 5,00,000\n📈 Interest Rate: 10.25% per annum\n⏰ Tenure: 36 months\n💳 Monthly EMI: Rs 16,134\n📋 Processing Fee: 2% + GST\n💵 Total Payable: Rs 5,80,824\n━━━━━━━━━━━━━━━━━━━━━━━\n\nWhy we approved this:\n✅ Your credit score is excellent (785)\n✅ 3.5 years of stable employment\n✅ Strong financial health\n✅ Comfortable EMI burden (only 22%!)\n\nCongratulations! 🥳 This is one of the fastest approvals I've seen today!\n\nNext Steps:\n1. Download your sanction letter using the button below\n2. Digital signing link will be sent to your registered mobile\n3. Funds will be disbursed within 24 hours after signing\n\nThank you for choosing us, Priya! Welcome to the family! 🎊\n\nIf you have any questions, I'm here to help! 😊",
                "decision": "APPROVED",
                "show_sanction": True,
                "loan_details": {"amount": 500000, "interest_rate": 10.25, "tenure_months": 36, "monthly_emi": 16134},
                "admin_logs": [
                    {"agent": "Master Agent", "message": "📄 Document 3/3 received - Processing", "type": "info"},
                    {"agent": "Master Agent", "message": "→ Routing to Verification Agent", "type": "info"},
                    {"agent": "Verification Agent", "message": "⏳ Extracting PAN card data...", "type": "info"},
                    {"agent": "Verification Agent", "message": "✓ PAN: ABCDE1234F (VALID)", "type": "success"},
                    {"agent": "Verification Agent", "message": "✓ Name match: 100%", "type": "success"},
                    {"agent": "Verification Agent", "message": "⏳ Analyzing salary slip...", "type": "info"},
                    {"agent": "Verification Agent", "message": "✓ Net Salary: ₹73,500/month", "type": "success"},
                    {"agent": "Verification Agent", "message": "✓ Employment: 3.5 years (STABLE)", "type": "success"},
                    {"agent": "Verification Agent", "message": "⏳ Reviewing bank statement...", "type": "info"},
                    {"agent": "Verification Agent", "message": "✓ Avg Balance: ₹1,45,000", "type": "success"},
                    {"agent": "Verification Agent", "message": "✓ No defaults found", "type": "success"},
                    {"agent": "Verification Agent", "message": "→ Returning to Master Agent", "type": "info"},
                    {"agent": "Master Agent", "message": "→ Routing to Underwriting Agent", "type": "info"},
                    {"agent": "Underwriting Agent", "message": "⏳ Final eligibility check...", "type": "info"},
                    {"agent": "Underwriting Agent", "message": "✓ Credit Score: 785 (EXCELLENT)", "type": "success"},
                    {"agent": "Underwriting Agent", "message": "✓ EMI burden: 22% (LOW)", "type": "success"},
                    {"agent": "Underwriting Agent", "message": "✓ All criteria met", "type": "success"},
                    {"agent": "Underwriting Agent", "message": "✓ APPROVAL GRANTED", "type": "success"},
                    {"agent": "Underwriting Agent", "message": "→ Returning to Master Agent", "type": "info"},
                    {"agent": "Master Agent", "message": "→ Routing to Sanction Letter Generator", "type": "info"},
                    {"agent": "Sanction Letter Generator", "message": "✓ Generating sanction letter...", "type": "success"},
                    {"agent": "Sanction Letter Generator", "message": "✓ Letter ready for download", "type": "success"},
                    {"agent": "Sanction Letter Generator", "message": "→ Returning to Master Agent", "type": "info"},
                    {"agent": "Master Agent", "message": "✅ Application APPROVED - Customer notified", "type": "success"}
                ],
                "final": True
            }
        ]
    },
    "rajesh_kumar": {
        "triggers": ["rajesh", "9988776655"],
        "required_docs": 2,
        "conversation": [
            {
                "step": 1,
                "trigger_keywords": ["rajesh", "9988776655"],
                "response": "Hi Rajesh! 👋\n\n⏳ Pulling up your profile...\n⏳ Fetching credit report...\n\n**Your Details:**\n• Name: Rajesh Kumar  \n• Phone: 9988776655  \n• Credit Score: **350/900** (Poor)  \n⚠️ **Risk Level:** HIGH\n\n---\n\nOkay, I'm going to be honest with you Rajesh - your credit score is quite low (350). This will significantly impact loan eligibility and rates.\n\nHow much were you looking to borrow? Let me see what options might be available, if any. 🤔",
                "decision": "HIGH_RISK",
                "show_upload": False,
                "extracted": {"name": "Rajesh Kumar", "phone": "9988776655"},
                "admin_logs": [
                    {"agent": "Master Agent", "message": "→ Customer inquiry: Rajesh Kumar", "type": "info"},
                    {"agent": "Verification Agent", "message": "🚨 Credit Score: 350 (VERY POOR)", "type": "error"},
                    {"agent": "Master Agent", "message": "⚠️ HIGH RISK - Enhanced verification needed", "type": "warning"}
                ]
            },
            {
                "step": 2,
                "trigger_keywords": ["15", "1500000", "fifteen", "lakh", "urgent", "business", "self", "employed", "2.5"],
                "response": "₹15 lakhs for business purposes... Let me check this urgently. 🚨\n\n⏳ Running enhanced verification...\n⏳ Cross-checking with fraud databases...\n⏳ Analyzing NPCI records...\n\n**CRITICAL ALERTS DETECTED:**\n\n🚨 **NPCI FRAUD DATABASE:** Phone 9988776655 **FLAGGED**\n🚨 **Multiple Applications:** 8 different NBFCs in last 30 days\n🚨 **Identity Theft Reports:** 2 cases linked to this number\n🚨 **Credit Score:** 350/900 (VERY POOR)\n🚨 **Active Defaults:** ₹3,45,000 outstanding\n🚨 **Loan Shopping Pattern:** 15 inquiries in 90 days\n\nRajesh, these are extremely serious red flags. Before I can proceed, I need to verify your documents immediately:\n\n1️⃣ **PAN Card**  \n2️⃣ **CIBIL Report**\n\nClick 📎 to upload these documents. I need to verify your identity given these alerts. ⬇️",
                "decision": "FRAUD_ALERT",
                "show_upload": True,
                "extracted": {"loan_amount": 1500000},
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "💰 Request: ₹15,00,000 (HIGH AMOUNT)", "type": "warning"},
                    {"agent": "Master Agent", "message": "→ Routing to Verification Agent", "type": "info"},
                    {"agent": "Verification Agent", "message": "⏳ Running fraud checks...", "type": "warning"},
                    {"agent": "Verification Agent", "message": "🚨 NPCI FRAUD ALERT: ACTIVE", "type": "error"},
                    {"agent": "Verification Agent", "message": "🚨 Phone flagged across 8 NBFCs", "type": "error"},
                    {"agent": "Verification Agent", "message": "🚨 Credit Score: 350 (CRITICAL)", "type": "error"},
                    {"agent": "Master Agent", "message": "⚠️ URGENT: Document verification required", "type": "error"}
                ]
            },
            {
                "step": 3,
                "docs_uploaded": 1,
                "response": "Got the PAN Card. Checking... ⏳\n\n**Document Analysis:**\n✅ PAN: BBQPK1234M  \n⚠️ **PAN Name:** Rajesh Kumar  \n⚠️ **Photo quality suspicious**  \n🚨 **Metadata:** Recent edits detected\n\n📎 Waiting for CIBIL Report...",
                "decision": "PROCESSING",
                "show_upload": True,
                "admin_logs": [
                    {"agent": "Verification Agent", "message": "📄 PAN Card received", "type": "info"},
                    {"agent": "Verification Agent", "message": "⏳ Analyzing document...", "type": "warning"},
                    {"agent": "Trust & Safety Agent", "message": "🔍 Metadata analysis in progress", "type": "warning"},
                    {"agent": "Trust & Safety Agent", "message": "⚠️ Photo quality suspicious", "type": "warning"},
                    {"agent": "Trust & Safety Agent", "message": "🚨 Document shows signs of tampering", "type": "error"}
                ]
            },
            {
                "step": 4,
                "docs_uploaded": 2,
                "response": "Both documents received. Running deep verification... 🔍\n\n⏳ Cross-checking PAN with Income Tax records...\n⏳ Analyzing CIBIL data authenticity...\n⏳ Facial recognition on PAN photo...\n⏳ Comparing with NPCI fraud database...\n\n**FINAL VERIFICATION RESULTS:**\n\n❌ PAN document: **TAMPERED** (metadata analysis shows recent edits)  \n❌ CIBIL report: **FORGED** (font inconsistencies detected)  \n❌ Photo mismatch: 87% probability of different person  \n❌ NPCI flag: Confirmed active fraud case  \n❌ Multiple loan rejections: 8 NBFCs in 30 days  \n❌ Credit Score: 350/900 with active defaults  \n❌ Outstanding debt: ₹3,45,000\n\n━━━━━━━━━━━━━━━━━━━━━━━\n🚫 **APPLICATION REJECTED** 🚫\n━━━━━━━━━━━━━━━━━━━━━━━\n\n**Rejection Reasons:**\n1. Document tampering detected\n2. NPCI fraud database match\n3. Multiple simultaneous loan attempts\n4. Identity verification failed\n5. Credit score 350/900 with active defaults\n6. Outstanding debt: ₹3,45,000\n\nRajesh, this case has been flagged for investigation and will be reported to:\n• NPCI Fraud Prevention Team\n• Credit Bureau Authorities\n• Law Enforcement (if required)\n\n**This application is permanently REJECTED.**\n\nNo further action can be taken. Thank you.",
                "decision": "REJECTED_FRAUD",
                "show_upload": False,
                "admin_logs": [
                    {"agent": "Verification Agent", "message": "📄 CIBIL Report received", "type": "info"},
                    {"agent": "Verification Agent", "message": "⏳ Running deep analysis...", "type": "warning"},
                    {"agent": "Trust & Safety Agent", "message": "🔍 Cross-checking with IT database", "type": "warning"},
                    {"agent": "Trust & Safety Agent", "message": "🚨 PAN document TAMPERED", "type": "error"},
                    {"agent": "Trust & Safety Agent", "message": "🚨 CIBIL report FORGED", "type": "error"},
                    {"agent": "Trust & Safety Agent", "message": "🚨 Facial recognition: 87% mismatch", "type": "error"},
                    {"agent": "Trust & Safety Agent", "message": "🚨 NPCI match confirmed", "type": "error"},
                    {"agent": "Underwriting Agent", "message": "❌ LOAN REJECTED - FRAUD", "type": "error"},
                    {"agent": "Master Agent", "message": "🚫 Case flagged for investigation", "type": "error"},
                    {"agent": "Master Agent", "message": "📊 Reporting to authorities", "type": "error"}
                ]
            }
        ]
    },
    "amit_patel": {
        "triggers": ["amit", "9123456789"],
        "required_docs": 3,
        "negotiation_rates": [13.99, 13.49, 12.99, 12.49, 12.25],
        "final_rate": 12.25,
        "conversation": [
            {
                "step": 1,
                "trigger_keywords": ["amit", "9123456789"],
                "response": "Hi Amit! 👋\n\n⏳ Looking up your profile...\n\n**Your Details:**\n• Name: Amit Patel  \n• Phone: 9123456789  \n• Credit Score: **680/900** (Fair - room for improvement!)  \n• Pre-approved Limit: ₹6,00,000\n\nOkay, so your credit score is decent but not in the excellent range yet. Still, you've got a pre-approved limit!\n\nHow much were you thinking of borrowing? 😊",
                "decision": "INITIAL",
                "show_upload": False,
                "extracted": {"name": "Amit Patel", "phone": "9123456789"},
                "admin_logs": [
                    {"agent": "Master Agent", "message": "→ Customer inquiry: Amit Patel", "type": "info"},
                    {"agent": "Verification Agent", "message": "✓ Credit Score: 680 (FAIR)", "type": "warning"},
                    {"agent": "Master Agent", "message": "⚠️ Lower credit tier - adjusted rates", "type": "warning"}
                ]
            },
            {
                "step": 2,
                "trigger_keywords": ["8", "800000", "eight", "lakh"],
                "response": "₹8 lakhs - got it! 💰\n\nHmm, I see you're asking for ₹8L but your pre-approved limit is ₹6L. Let me see what I can do...\n\n⏳ Consulting with underwriting...\n⏳ Checking eligibility...\n\nOkay, I managed to get approval for **₹6.5 lakhs** - that's the maximum we can offer based on your current credit profile.\n\n**Initial Offer:**  \n💰 Amount: ₹6,50,000 (adjusted)  \n📈 Interest Rate: **13.99% per annum**  \n⏰ Tenure: 48 months  \n💳 Monthly EMI: ₹21,873  \n📊 Processing Fee: 2.5% + GST\n\nI know it's not the full ₹8L you wanted, but this is safer for your budget. Your EMI would be around **46% of your monthly income** - still manageable.\n\nWhat do you think? Want to proceed with this, or should I try to get you a better rate? 🤔",
                "decision": "OFFER_MADE",
                "show_upload": False,
                "negotiation_stage": 1,
                "current_rate": 13.99,
                "extracted": {"loan_amount": 650000},
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "💰 Request: ₹8,00,000", "type": "info"},
                    {"agent": "Underwriting Agent", "message": "⚠️ Exceeds pre-approved limit", "type": "warning"},
                    {"agent": "Underwriting Agent", "message": "✓ Adjusted to ₹6,50,000", "type": "success"},
                    {"agent": "Sales Agent", "message": "📊 Initial rate: 13.99%", "type": "info"}
                ]
            },
            {
                "step": 3,
                "trigger_keywords": ["better", "lower", "less", "reduce", "high"],
                "response": "Totally understand! Let me work on that rate for you... 💪\n\n⏳ Checking your employment history...\n⏳ Reviewing payment patterns...\n\nGood news! I see you've been with your employer for 2 years - that helps!\n\n**Improved Offer:**  \n💰 Amount: ₹6,50,000  \n📈 Interest Rate: **13.49% per annum** ⬇️  \n⏰ Tenure: 48 months  \n💳 Monthly EMI: ₹21,679  \n💵 **You save: ₹9,312 over the loan!**\n\nThat's ₹194/month less! Getting better, right?\n\nShall we go with this? Or want me to push for more? 😊",
                "decision": "OFFER_REVISED",
                "show_upload": False,
                "negotiation_stage": 2,
                "current_rate": 13.49,
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "💬 Customer negotiating", "type": "info"},
                    {"agent": "Underwriting Agent", "message": "✓ Rate reduced: 13.49%", "type": "success"}
                ]
            },
            {
                "step": 4,
                "trigger_keywords": ["better", "lower", "less", "reduce", "still"],
                "response": "You're good at this! 😄 Let me check with my senior...\n\n⏳ Escalating to management...\n⏳ Reviewing your complete profile...\n\nAlright, because you have consistent income and no recent defaults, I got approval for:\n\n**Special Offer:**  \n💰 Amount: ₹6,50,000  \n📈 Interest Rate: **12.99% per annum** ⬇️  \n⏰ Tenure: 48 months  \n💳 Monthly EMI: ₹21,476  \n💵 **Total savings: ₹19,008 from initial offer!**\n\nNow we're talking! That's ₹397/month less than where we started.\n\nThis is getting close to our floor rate for your credit profile. Should I try one more time? 🤞",
                "decision": "OFFER_REVISED",
                "show_upload": False,
                "negotiation_stage": 3,
                "current_rate": 12.99,
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "💬 Continued negotiation", "type": "info"},
                    {"agent": "Sales Agent", "message": "→ Senior management approval", "type": "info"},
                    {"agent": "Underwriting Agent", "message": "✓ Special rate: 12.99%", "type": "success"}
                ]
            },
            {
                "step": 5,
                "trigger_keywords": ["better", "lower", "less", "reduce", "one more"],
                "response": "Alright, you're really pushing me here! 😅 Let me make one final attempt...\n\n⏳ Final check with underwriting...\n⏳ Reviewing minimum rate criteria...\n\nOkay Amit, this is the **absolute best** I can do:\n\n**FINAL OFFER:**  \n💰 Amount: ₹6,50,000  \n📈 Interest Rate: **12.25% per annum** ⬇️⬇️  \n⏰ Tenure: 48 months  \n💳 Monthly EMI: ₹21,292  \n💵 **Total savings: ₹27,888 from initial offer!**\n\n**This is as low as I can go** - honestly! For a credit score of 680, this is an excellent rate. Most banks would charge 14-15% for this profile.\n\nYou're saving ₹581/month compared to the initial offer!\n\nTo move forward, I need 3 documents:\n\n1️⃣ Salary Slip  \n2️⃣ Bank Statement  \n3️⃣ CIBIL Report\n\nClick 📎 to upload! 🚀",
                "decision": "FINAL_OFFER",
                "show_upload": True,
                "negotiation_stage": 4,
                "current_rate": 12.25,
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "🎯 FINAL OFFER: 12.25%", "type": "success"},
                    {"agent": "Sales Agent", "message": "⚠️ Floor rate for credit 680", "type": "warning"},
                    {"agent": "Master Agent", "message": "→ Document upload required", "type": "info"}
                ]
            },
            {
                "step": 6,
                "trigger_keywords": ["better", "lower", "less", "reduce"],
                "response": "I really wish I could, but 12.25% is genuinely our **floor rate** for your credit score (680). 😔\n\nTo give you context:\n• Credit Score 750+: We offer 10-11%\n• Credit Score 680-749: **12-13%** (you're at the lowest end!)\n• Credit Score below 680: 14-16%\n\nYou're already getting VIP pricing for your tier! If I go any lower, the system will auto-reject it.\n\n**Good news though:** After 12 months of timely payments, your credit score will improve to 720+ and you can refinance at 11-11.5%! 📈\n\nLet's lock in this great rate! Upload your 3 documents:\n\n1️⃣ Salary Slip  \n2️⃣ Bank Statement  \n3️⃣ CIBIL Report\n\nClick 📎 below! ⬇️",
                "decision": "FIRM_FINAL",
                "show_upload": True,
                "negotiation_stage": 5,
                "current_rate": 12.25,
                "admin_logs": [
                    {"agent": "Sales Agent", "message": "💬 Further negotiation attempted", "type": "info"},
                    {"agent": "Sales Agent", "message": "✋ Holding at 12.25% (floor)", "type": "warning"},
                    {"agent": "Sales Agent", "message": "💡 Suggested refinance path", "type": "info"}
                ]
            },
            {
                "step": 7,
                "docs_uploaded": 1,
                "response": "Perfect! First document received! 📄✅\n\nVerifying...\n\nDocument 1 verified!\n\n📄 Still needed (2 more):\n• Bank Statement (Last 2 months)\n• CIBIL Report\n\nPlease upload using the 📎 button below!",
                "decision": "DOC_VERIFIED",
                "show_upload": True,
                "admin_logs": [
                    {"agent": "Verification Agent", "message": "📄 Doc 1/3 received", "type": "success"}
                ]
            },
            {
                "step": 8,
                "docs_uploaded": 2,
                "response": "Great! Second document received! 📄📄✅\n\nProcessing...\n\nDocument 2 verified!\n\n📄 Last document needed:\n• CIBIL Report\n\nUpload using 📎 button below!",
                "decision": "DOC_VERIFIED",
                "show_upload": True,
                "admin_logs": [
                    {"agent": "Verification Agent", "message": "📄 Doc 2/3 received", "type": "success"}
                ]
            },
            {
                "step": 9,
                "docs_uploaded": 3,
                "response": "Excellent! All 3 documents received! 📄📄📄✅\n\nFinal verification...\nUnderwriting analysis...\n\n✅ Salary Slip: Rs 47,850/month verified\n✅ Bank Statement: Regular deposits confirmed\n✅ CIBIL: Credit score 680 confirmed\n✅ EMI Burden: 44% (acceptable range)\n\n🎉 LOAN APPROVED! 🎉\n\nAPPROVAL SUMMARY\n━━━━━━━━━━━━━━━━━━━━━━━\n👤 Name: Amit Patel\n💰 Approved Amount: Rs 6,50,000\n📈 Interest Rate: 12.25% per annum\n⏰ Tenure: 48 months\n💳 Monthly EMI: Rs 21,292\n📊 Credit Score: 680 (FAIR)\n✅ Status: CONDITIONALLY APPROVED\n━━━━━━━━━━━━━━━━━━━━━━━\n\nConditions:\n• First 3 EMIs: Auto-debit required\n• Credit monitoring: Active\n• Refinance option: Available after 12 months\n\nNext Steps:\n1. Download your sanction letter using the button below\n2. Digital signing link via SMS\n3. Disbursal within 48 hours\n\nCongratulations Amit! 🎊",
                "decision": "APPROVED_CONDITIONAL",
                "show_upload": False,
                "show_sanction": True,
                "loan_details": {"amount": 650000, "interest_rate": 12.25, "tenure_months": 48, "monthly_emi": 21292},
                "admin_logs": [
                    {"agent": "Verification Agent", "message": "✓ All docs verified", "type": "success"},
                    {"agent": "Underwriting Agent", "message": "✓ Income confirmed: ₹47,850", "type": "success"},
                    {"agent": "Underwriting Agent", "message": "⚠️ EMI burden: 44% (acceptable)", "type": "warning"},
                    {"agent": "Underwriting Agent", "message": "✅ CONDITIONALLY APPROVED", "type": "success"},
                    {"agent": "Sanction Letter Generator", "message": "✓ Letter generated", "type": "success"}
                ]
            }
        ]
    }
}

# ==================== STATE DEFINITION ====================
class AgentState(TypedDict):
    """Complete state maintained throughout the conversation"""
    # User Input
    messages: Annotated[List, operator.add]
    current_message: str
    
    # Extracted Entities
    name: Optional[str]
    phone: Optional[str]
    pan: Optional[str]
    intent: Optional[str]
    
    # Verification Status
    customer_verified: bool
    customer_profile: Optional[Dict[str, Any]]
    verification_status: Optional[str]
    
    # Risk Analysis
    trust_score: int  # 0-100
    trust_reasoning: str
    fraud_flags: List[str]
    
    # Decision
    loan_decision: Optional[str]  # APPROVED, DECLINED, YELLOW_FLAG
    interest_rate: Optional[float]
    loan_amount_eligible: Optional[int]
    conditions: List[str]
    
    # Response
    ai_response: str
    
    # Metadata
    conversation_stage: str
    missing_info: List[str]
    admin_log: List[Dict[str, Any]]  # For God Mode Dashboard
    
    # Demo Mode State
    demo_script: Optional[str]  # Active demo scenario: priya_sharma, amit_patel, rajesh_kumar
    demo_step: Optional[int]  # Current step in demo conversation flow
    docs_uploaded: Optional[int]  # Number of documents uploaded (for multi-doc workflows)
    
    # UI Control Flags
    show_upload: Optional[bool]  # Show document upload button in UI
    show_sanction_letter: Optional[bool]  # Show sanction letter download button
    loan_details: Optional[Dict[str, Any]]  # Loan details for sanction letter (amount, rate, tenure, etc.)
    is_scripted: Optional[bool]  # Whether response came from script or AI


# ==================== PYDANTIC MODELS FOR STRUCTURED OUTPUT ====================
class ExtractedEntities(BaseModel):
    """Structured output for entity extraction"""
    name: Optional[str] = Field(None, description="Customer's full name")
    phone: Optional[str] = Field(None, description="10-digit phone number")
    pan: Optional[str] = Field(None, description="PAN card number (10 characters)")
    intent: Optional[Literal["apply", "status_check", "upload_doc", "inquiry", "complaint"]] = Field(
        None, description="Primary intent of the user"
    )
    loan_type: Optional[Literal["personal", "home", "business", "education"]] = Field(
        None, description="Type of loan requested"
    )
    loan_amount: Optional[int] = Field(None, description="Requested loan amount in INR")
    confidence: float = Field(default=0.5, description="Confidence in extraction (0-1)")


class TrustAnalysis(BaseModel):
    """Structured output for trust & safety analysis"""
    risk_score: int = Field(..., ge=0, le=100, description="Risk score from 0 (safe) to 100 (dangerous)")
    trust_score: int = Field(..., ge=0, le=100, description="Trust score from 0 (untrusted) to 100 (trusted)")
    reasoning: str = Field(..., description="Explanation for the scores")
    red_flags: List[str] = Field(default_factory=list, description="List of concerning behaviors detected")
    is_scripted: bool = Field(default=False, description="Whether the message appears scripted/bot-like")
    urgency_level: Literal["low", "medium", "high", "extreme"] = Field(
        default="low", description="Financial desperation level"
    )


# ==================== GEMINI SETUP ====================
class GeminiAgent:
    """Wrapper for Google Gemini API interactions"""
    
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7,
            convert_system_message_to_human=True
        )
        
        self.llm_structured = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.3,  # Lower temperature for structured extraction
            convert_system_message_to_human=True
        )
        
        # Configure native Gemini SDK for advanced features
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.native_model = genai.GenerativeModel('gemini-1.5-flash')
    
    async def extract_entities(self, user_message: str, conversation_history: List) -> ExtractedEntities:
        """Extract structured entities using Gemini function calling - NO REGEX"""
        system_prompt = """You are an expert entity extractor for a loan application system.
Extract the following information from the user's message - USE NATURAL LANGUAGE UNDERSTANDING, NOT PATTERNS.

Fields to extract:
- name: Full name of the customer (look for "I am X", "my name is X", "this is X", or just names mentioned)
- phone: Indian mobile number (10 digits, may have spaces/dashes/+91 - clean it to just digits)
- pan: PAN card number (10 characters: 5 letters, 4 digits, 1 letter - e.g., ABCDE1234F)
- intent: What the user wants (apply, status_check, upload_doc, inquiry, complaint)
- loan_type: Type of loan if mentioned (personal, home, business, education)
- loan_amount: Amount requested in INR

Intelligence required:
- If someone says "I need 5 lakhs", extract loan_amount as 500000
- If phone has spaces "98765 43210", clean to "9876543210"
- If they say "PAN is ABCDE1234F" or just "ABCDE1234F", extract it
- Be flexible with phrasing: "My number is", "call me on", "contact on", "phone:", etc.

If information is not present, return None for that field.
DO NOT use regex patterns - use your language understanding."""

        messages = [
            SystemMessage(content=system_prompt),
            *conversation_history[-5:],  # Last 5 messages for context
            HumanMessage(content=user_message)
        ]
        
        structured_llm = self.llm_structured.with_structured_output(ExtractedEntities)
        result = await structured_llm.ainvoke(messages)
        return result
    
    async def analyze_trust(self, user_message: str, typing_metadata: Optional[Dict] = None) -> TrustAnalysis:
        """Analyze trust and safety using Gemini"""
        system_prompt = """You are a fraud detection and trust analysis expert for a financial institution.

Analyze the user's message for:
1. Financial desperation signals (begging, extreme urgency, sob stories)
2. Aggression or threatening behavior
3. Scripted/bot-like patterns (too formal, template language)
4. Inconsistencies or suspicious claims
5. Pressure tactics or unrealistic promises

Return:
- risk_score: 0-100 (0 = completely safe, 100 = clear fraud)
- trust_score: 0-100 (0 = untrustworthy, 100 = highly trustworthy)
- reasoning: Clear explanation
- red_flags: List of specific concerns
- is_scripted: Whether this looks automated
- urgency_level: low/medium/high/extreme

Be balanced - most customers are genuine. Only flag real concerns."""

        metadata_context = ""
        if typing_metadata:
            metadata_context = f"\n\nTyping Metadata: {json.dumps(typing_metadata)}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Message: {user_message}{metadata_context}")
        ]
        
        structured_llm = self.llm_structured.with_structured_output(TrustAnalysis)
        result = await structured_llm.ainvoke(messages)
        return result
    
    async def generate_response(
        self, 
        decision: Dict[str, Any], 
        customer_name: str,
        conversation_context: List,
        stage: str
    ) -> str:
        """Generate natural, empathetic response based on decision - ZERO TEMPLATES"""
        
        # Build context-aware prompt that tells Gemini the situation
        if decision["loan_decision"] == "APPROVED":
            decision_context = f"""
The loan has been APPROVED with these details:
- Customer: {customer_name}
- Approved Amount: ₹{decision['loan_amount_eligible']:,}
- Interest Rate: {decision['interest_rate']}%
- Conditions: {', '.join(decision['conditions']) if decision['conditions'] else 'None - instant approval!'}

Your task: Congratulate the customer enthusiastically. This is great news!
Mention the rate and amount clearly. Keep it warm and professional.
If there are conditions, mention them as "just a formality" or "quick verification needed".
Maximum 60 words. Be celebratory but not over-the-top."""

        elif decision["loan_decision"] == "YELLOW_FLAG":
            decision_context = f"""
The loan is CONDITIONALLY APPROVED - we need additional documents:
- Customer: {customer_name}  
- Approved Amount: ₹{decision['loan_amount_eligible']:,}
- Interest Rate: {decision['interest_rate']}%
- Required Documents: {', '.join(decision['conditions'])}

Your task: Explain this is NOT a rejection - the loan is approved pending verification.
Be encouraging and helpful. Make document submission sound easy.
Explain this is standard procedure for their profile.
Maximum 70 words. Be supportive and clear."""

        elif decision["loan_decision"] == "DECLINED":
            decline_reason = decision.get('decline_reason', 'current eligibility criteria not met')
            decision_context = f"""
Unfortunately, the loan cannot be approved at this time.
- Customer: {customer_name}
- Reason: {decline_reason}

Your task: Deliver this news with empathy and professionalism.
Suggest constructive next steps:
  - Improving credit score (if that's the issue)
  - Reducing existing debt (if high DTI)
  - Reapplying in 6 months after improvements
  
Be kind but clear. Don't give false hope. 
Maximum 80 words. Show you care about their financial future."""

        else:  # Information gathering stage
            missing_info = decision.get('missing_info', [])
            decision_context = f"""
We're still gathering information from the customer.
Current stage: {stage}
Missing: {', '.join(missing_info) if missing_info else 'unclear'}

Your task: Politely ask for the missing information.
Be conversational - don't sound like a form.
Examples:
  - Instead of "Please provide name", say "May I have your name?"
  - Instead of "Enter phone number", say "What's the best number to reach you?"

Keep it friendly and natural. Maximum 50 words."""

        # Now let Gemini generate the response with FULL CREATIVE FREEDOM
        system_prompt = f"""You are a friendly, professional Tata Capital loan officer having a natural conversation.

Context: {decision_context}

Style guidelines:
- Sound human and warm, not robotic
- Use natural phrases, not templates
- Vary your language based on context
- If good news: be genuinely happy for them
- If bad news: show empathy and offer help
- If asking for info: be conversational

DO NOT use templates. Generate unique, contextual responses every time.
"""

        messages = [
            SystemMessage(content=system_prompt),
            *conversation_context[-3:],  # Recent conversation for continuity
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content


# ==================== GRAPH NODES ====================
class LoanAgentGraph:
    """The main LangGraph state machine"""
    
    def __init__(self, gemini_api_key: str):
        self.gemini = GeminiAgent(gemini_api_key)
        self.data_provider = MockDataProvider()
        self.graph = self._build_graph()
        
        # Display system configuration
        print("\n" + "="*60)
        print("🎯 TATA CAPITAL AI UNDERWRITER - INITIALIZED")
        print("="*60)
        print(f"📍 Mode: {'🎬 DEMO MODE (Scripted)' if DEMO_MODE else '🤖 PRODUCTION MODE (Gemini AI)'}")
        if DEMO_MODE:
            print("   • Zero API costs")
            print("   • Instant responses")
            print("   • Perfect for presentations")
            print("   • Triggers: priya, rajesh, amit")
        else:
            print("   • Full Gemini AI intelligence")
            print("   • Natural language understanding")
            print("   • Dynamic decision making")
            print("   • Production-grade processing")
        print("="*60 + "\n")
        print("✅ LoanAgentGraph ready for requests")
    
    def _build_graph(self) -> StateGraph:
        """Build the state graph with all nodes and edges"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("listener", self.listener_node)
        workflow.add_node("gatekeeper", self.gatekeeper_node)
        workflow.add_node("analyst", self.analyst_node)
        workflow.add_node("underwriter", self.underwriter_node)
        workflow.add_node("voice", self.voice_node)
        
        # Define edges
        workflow.set_entry_point("listener")
        
        workflow.add_conditional_edges(
            "listener",
            self.route_after_listener,
            {
                "gatekeeper": "gatekeeper",
                "voice": "voice",  # If missing info, go straight to response
            }
        )
        
        workflow.add_edge("gatekeeper", "analyst")
        workflow.add_edge("analyst", "underwriter")
        workflow.add_edge("underwriter", "voice")
        workflow.add_edge("voice", END)
        
        return workflow.compile()
    
    # ========== SCRIPTED DEMO HANDLER ==========
    def get_scripted_response(self, state: AgentState) -> Optional[Dict]:
        """INTERACTIVE STAGED DEMO - Step-by-step conversation flow"""
        user_msg = state["current_message"].lower().strip()
        
        # Get current script state
        active_script = state.get("demo_script")
        current_step = state.get("demo_step", 1)  # Start at step 1
        
        # STEP 1: Detect which script to activate (on trigger keywords)
        if not active_script:
            for script_name, script_data in DEMO_SCRIPTS.items():
                for trigger in script_data["triggers"]:
                    if trigger in user_msg:
                        active_script = script_name
                        state["demo_script"] = script_name
                        state["demo_step"] = 1  # Set to step 1
                        current_step = 1
                        print(f"\n{'='*60}")
                        print(f"🚀 SYSTEM MODE: 🎬 DEMO MODE")
                        print(f"{'='*60}\n")
                        print(f"🎬 SCRIPT ACTIVATED: {script_name.upper()}")
                        break
                if active_script:
                    break
            
            # No script matched - return None (will use AI)
            if not active_script:
                return None
        
        # STEP 2: Get script data
        script = DEMO_SCRIPTS.get(active_script)
        if not script:
            print(f"⚠️ Script {active_script} not found")
            return None
        
        # STEP 3: Find the matching step based on user input AND docs_uploaded count
        matching_step = None
        docs_uploaded = state.get("docs_uploaded", 0)
        
        for step_obj in script["conversation"]:
            # PRIORITY 1: Document upload steps (match by docs_uploaded count)
            if "docs_uploaded" in step_obj:
                if step_obj["docs_uploaded"] == docs_uploaded:
                    matching_step = step_obj
                    break
            # PRIORITY 2: Regular conversation steps (match by keywords)
            elif "trigger_keywords" in step_obj:
                keywords = step_obj["trigger_keywords"]
                # Check if ANY keyword matches the user message
                if any(keyword.lower() in user_msg for keyword in keywords):
                    matching_step = step_obj
                    break
        
        # If no matching step found, provide helpful guidance based on current step
        if not matching_step:
            print(f"⚠️ No matching step found for input '{user_msg}' (docs: {docs_uploaded}) in script {active_script}")
            current_step_num = state.get("demo_step", 1)
            
            # Provide context-aware guidance
            if current_step_num == 1:
                return {
                    "response": "I'd love to help! But first, could you tell me how much loan amount you're looking for?\n\nFor example, you can say: \"I need 5 lakhs\" or \"I want to borrow 3 lakh rupees\"",
                    "show_upload": False,
                    "show_sanction": False,
                    "admin_logs": [{"agent": "Master Agent", "message": "Clarifying loan amount requirement", "type": "info"}],
                    "is_scripted": True
                }
            elif current_step_num == 2:
                return {
                    "response": "Great question! To move forward with your loan application, I'll need you to upload the required documents.\n\nPlease click the 📎 upload button below to submit your documents. You can upload them one by one!",
                    "show_upload": True,
                    "show_sanction": False,
                    "admin_logs": [{"agent": "Master Agent", "message": "Reminding about document upload", "type": "info"}],
                    "is_scripted": True
                }
            else:
                # During document upload phase
                # Get required docs list based on active script
                script_data = DEMO_SCRIPTS.get(active_script, {})
                required_docs_count = script_data.get("required_docs", 3)
                docs_uploaded = state.get("docs_uploaded", 0)
                remaining = required_docs_count - docs_uploaded
                
                if active_script == "priya_sharma":
                    if remaining == 3:
                        docs_list = "\n• PAN Card\n• Salary Slip (Nov 2025)\n• Bank Statement (Last 2 months)"
                    elif remaining == 2:
                        docs_list = "\n• Salary Slip (Nov 2025)\n• Bank Statement (Last 2 months)"
                    elif remaining == 1:
                        docs_list = "\n• Bank Statement (Oct-Nov 2025)"
                    else:
                        docs_list = ""
                elif active_script == "amit_patel":
                    if remaining == 3:
                        docs_list = "\n• Salary Slip\n• Bank Statement (Last 2 months)\n• CIBIL Report"
                    elif remaining == 2:
                        docs_list = "\n• Bank Statement (Last 2 months)\n• CIBIL Report"
                    elif remaining == 1:
                        docs_list = "\n• CIBIL Report"
                    else:
                        docs_list = ""
                elif active_script == "rajesh_kumar":
                    if remaining == 2:
                        docs_list = "\n• PAN Card\n• CIBIL Report"
                    elif remaining == 1:
                        docs_list = "\n• CIBIL Report"
                    else:
                        docs_list = ""
                else:
                    docs_list = ""
                
                return {
                    "response": f"I'm currently processing your application. Please continue uploading the required documents using the 📎 button below.\n\n📄 Documents needed ({remaining} remaining):{docs_list}\n\nOnce all documents are received, I'll complete your verification! 😊",
                    "show_upload": True,
                    "show_sanction": False,
                    "admin_logs": [{"agent": "Master Agent", "message": f"Waiting for {remaining} more documents", "type": "info"}],
                    "is_scripted": True
                }
        
        step_data = matching_step
        next_step = step_data["step"] + 1
        
        # STEP 4: Update state with extracted data
        if "extracted" in step_data:
            for key, value in step_data["extracted"].items():
                state[key] = value
        
        # STEP 5: Set decision and loan details
        if "decision" in step_data:
            state["loan_decision"] = step_data["decision"]
            if step_data["decision"] == "APPROVED":
                state["loan_amount_eligible"] = step_data.get("loan_details", {}).get("amount", 500000)
                state["interest_rate"] = step_data.get("loan_details", {}).get("interest_rate", 10.5)
            elif step_data["decision"] == "DECLINED":
                state["loan_amount_eligible"] = 0
        
        # STEP 6: Increment step for next message
        state["demo_step"] = next_step
        
        # STEP 7: Mark as final if specified
        if step_data.get("final"):
            state["demo_complete"] = True
        
        print(f"📝 STEP {step_data['step']}/{len(script['conversation'])} | {active_script}")
        print(f"⚡ INSTANT RESPONSE | Script: {active_script}")
        
        # STEP 8: Return response with UI flags and admin logs
        return {
            "response": step_data["response"],
            "show_upload": step_data.get("show_upload", False),
            "show_sanction": step_data.get("show_sanction", False),
            "loan_details": step_data.get("loan_details"),
            "admin_logs": step_data.get("admin_logs", []),
            "is_scripted": True
        }
    
    # ========== NODE A: LISTENER (Entity Extractor) ==========
    async def listener_node(self, state: AgentState) -> AgentState:
        """
        NODE A: Entity Extraction & Message Understanding
        
        DUAL MODE ARCHITECTURE:
        - DEMO_MODE = True  → Use scripted flows (instant, no API)
        - DEMO_MODE = False → Use Gemini AI (intelligent, real NLP)
        """
        log_entry = {
            "node": "listener",
            "timestamp": datetime.now().isoformat(),
            "action": "entity_extraction"
        }
        
        # =========================================================
        # MODE 1: DEMO MODE (Scripted Flows)
        # =========================================================
        if DEMO_MODE:
            print("🎬 DEMO MODE ACTIVE - Using scripted responses")
            
            # Check for scripted response
            scripted = self.get_scripted_response(state)
            if scripted:
                print(f"⚡ INSTANT RESPONSE | Script: {state.get('demo_script', 'Unknown')}")
                state["ai_response"] = scripted["response"]
                state["show_upload"] = scripted.get("show_upload", False)
                state["show_sanction_letter"] = scripted.get("show_sanction", False)
                state["loan_details"] = scripted.get("loan_details")
                state["is_scripted"] = True
                
                # Add admin logs for agent orchestration visibility
                if "admin_logs" in scripted:
                    state.setdefault("admin_log", []).extend(scripted["admin_logs"])
                
                # DYNAMIC TRUST SCORE & BEHAVIORAL ANALYSIS based on script progression
                active_script = state.get("demo_script", "")
                current_step = state.get("demo_step", 1)
                docs_uploaded = state.get("docs_uploaded", 0)
                
                # Calculate dynamic trust score and behavioral metrics
                if "priya" in active_script.lower():
                    # Priya: Starts at 65, increases to 90 as documents are verified
                    if current_step == 1:
                        state["trust_score"] = 65
                        behavioral_score = 70
                        risk_category = "LOW"
                    elif current_step <= 6:
                        state["trust_score"] = 65 + (current_step - 1) * 2  # 65, 67, 69, 71, 73, 75
                        behavioral_score = 70 + (current_step - 1) * 3
                        risk_category = "LOW"
                    elif docs_uploaded == 1:
                        state["trust_score"] = 78
                        behavioral_score = 82
                        risk_category = "LOW"
                    elif docs_uploaded == 2:
                        state["trust_score"] = 82
                        behavioral_score = 88
                        risk_category = "LOW"
                    elif docs_uploaded == 3:
                        state["trust_score"] = 90
                        behavioral_score = 95
                        risk_category = "LOW"
                    else:
                        state["trust_score"] = 75
                        behavioral_score = 80
                        risk_category = "LOW"
                        
                elif "amit" in active_script.lower():
                    # Amit: Starts at 55, increases to 75 with documents
                    if current_step == 1:
                        state["trust_score"] = 55
                        behavioral_score = 65
                        risk_category = "MEDIUM"
                    elif current_step <= 6:
                        state["trust_score"] = 55 + (current_step - 1) * 2  # 55, 57, 59, 61, 63, 65
                        behavioral_score = 65 + (current_step - 1) * 2
                        risk_category = "MEDIUM"
                    elif docs_uploaded == 1:
                        state["trust_score"] = 68
                        behavioral_score = 72
                        risk_category = "MEDIUM"
                    elif docs_uploaded == 2:
                        state["trust_score"] = 70
                        behavioral_score = 76
                        risk_category = "MEDIUM"
                    elif docs_uploaded == 3:
                        state["trust_score"] = 75
                        behavioral_score = 82
                        risk_category = "MEDIUM"
                    else:
                        state["trust_score"] = 65
                        behavioral_score = 70
                        risk_category = "MEDIUM"
                        
                elif "rajesh" in active_script.lower():
                    # Rajesh: Starts at 35, decreases to 10 as fraud detected
                    if current_step == 1:
                        state["trust_score"] = 35
                        behavioral_score = 40
                        risk_category = "HIGH"
                    elif current_step == 2:
                        state["trust_score"] = 25  # Fraud alerts detected
                        behavioral_score = 28
                        risk_category = "CRITICAL"
                    elif docs_uploaded == 1:
                        state["trust_score"] = 20  # Document tampering suspected
                        behavioral_score = 22
                        risk_category = "CRITICAL"
                    elif docs_uploaded == 2:
                        state["trust_score"] = 10  # Fraud confirmed
                        behavioral_score = 15
                        risk_category = "FRAUD_CONFIRMED"
                    else:
                        state["trust_score"] = 30
                        behavioral_score = 35
                        risk_category = "HIGH"
                else:
                    state["trust_score"] = 50  # Default neutral
                    behavioral_score = 50
                    risk_category = "UNKNOWN"
                
                # Create/update customer profile with dynamic behavioral analysis
                state["customer_profile"] = {
                    "name": state.get("name", "Unknown"),
                    "phone": state.get("phone", "Unknown"),
                    "credit_score": state.get("credit_score", 0),
                    "behavioral_flags": {
                        "risk_category": risk_category,
                        "behavioral_score": behavioral_score,
                        "urgency_level": "HIGH" if "rajesh" in active_script.lower() else "MEDIUM",
                        "conversation_quality": "EXCELLENT" if "priya" in active_script.lower() else "GOOD" if "amit" in active_script.lower() else "POOR",
                        "document_authenticity": "VERIFIED" if docs_uploaded >= 2 and "priya" in active_script.lower() else "PENDING" if docs_uploaded < 2 else "SUSPICIOUS" if "rajesh" in active_script.lower() else "UNDER_REVIEW"
                    }
                }
                
                log_entry["mode"] = "demo_scripted"
                log_entry["script"] = state.get("demo_script")
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            # No script matched - provide friendly generic response
            print("⚠️ No demo script matched - providing generic response")
            state["ai_response"] = "Hey there! 👋 I'm your AI Loan Assistant from Tata Capital.\n\nI can help you get a personal loan approved in minutes! Just tell me your name and phone number to get started.\n\nFor example: \"Hi, I'm Priya and my number is 9876543210\""
            state["conversation_stage"] = "initial"
            state["is_scripted"] = True
            log_entry["mode"] = "demo_welcome"
            state.setdefault("admin_log", []).append(log_entry)
            return state
        
        # =========================================================
        # MODE 2: PRODUCTION MODE (Real Gemini AI)
        # =========================================================
        print("🤖 PRODUCTION MODE ACTIVE - Using Gemini AI")
        
        try:
            # Extract entities using Gemini
            entities = await self.gemini.extract_entities(
                state["current_message"],
                state["messages"]
            )
            
            # Update state with extracted information
            if entities.name:
                state["name"] = entities.name
            if entities.phone:
                state["phone"] = entities.phone
            if entities.pan:
                state["pan"] = entities.pan
            if entities.intent:
                state["intent"] = entities.intent
            if entities.loan_type:
                state["loan_type"] = entities.loan_type
            if entities.loan_amount:
                state["loan_amount_requested"] = entities.loan_amount
            
            # Determine what's missing
            missing = []
            if not state.get("name"):
                missing.append("name")
            if not state.get("phone"):
                missing.append("phone")
            if not state.get("pan"):
                missing.append("pan")
            
            state["missing_info"] = missing
            
            log_entry["mode"] = "production_ai"
            log_entry["extracted"] = {
                "name": entities.name,
                "phone": entities.phone,
                "pan": entities.pan,
                "intent": entities.intent
            }
            log_entry["missing_info"] = missing
            
        except Exception as e:
            log_entry["error"] = str(e)
            log_entry["mode"] = "production_ai_error"
            # Default to asking for information
            state["missing_info"] = ["name", "phone", "pan"]
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ========== NODE B: GATEKEEPER (Verification) ==========
    async def gatekeeper_node(self, state: AgentState) -> AgentState:
        """Verify customer identity against mock database"""
        log_entry = {
            "node": "gatekeeper",
            "timestamp": datetime.now().isoformat(),
            "action": "customer_verification"
        }
        
        try:
            verification_result = self.data_provider.verify_customer(
                state["phone"], 
                state["pan"]
            )
            
            state["verification_status"] = verification_result["status"]
            state["customer_verified"] = verification_result["verified"]
            
            if verification_result["verified"]:
                state["customer_profile"] = verification_result["profile"]
                log_entry["status"] = "verified"
                log_entry["customer"] = state["name"]
            elif verification_result["status"] == "NOT_FOUND":
                # Create lead
                lead = self.data_provider.create_lead(
                    state["name"], 
                    state["phone"], 
                    state.get("pan")
                )
                state["customer_profile"] = lead
                log_entry["status"] = "new_lead"
            elif verification_result["status"] == "MISMATCH":
                state["fraud_flags"] = state.get("fraud_flags", [])
                state["fraud_flags"].append("IDENTITY_MISMATCH")
                log_entry["status"] = "mismatch_risk"
            
            log_entry["verification_result"] = verification_result["status"]
            
        except Exception as e:
            log_entry["error"] = str(e)
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ========== NODE C: ANALYST (Trust & Safety) ==========
    async def analyst_node(self, state: AgentState) -> AgentState:
        """Analyze message for fraud, desperation, aggression"""
        log_entry = {
            "node": "analyst",
            "timestamp": datetime.now().isoformat(),
            "action": "trust_analysis"
        }
        
        try:
            # Perform trust analysis
            trust_analysis = await self.gemini.analyze_trust(state["current_message"])
            
            state["trust_score"] = trust_analysis.trust_score
            state["trust_reasoning"] = trust_analysis.reasoning
            
            # Update fraud flags
            if trust_analysis.red_flags:
                state["fraud_flags"] = state.get("fraud_flags", [])
                state["fraud_flags"].extend(trust_analysis.red_flags)
            
            log_entry["trust_score"] = trust_analysis.trust_score
            log_entry["risk_score"] = trust_analysis.risk_score
            log_entry["red_flags"] = trust_analysis.red_flags
            log_entry["urgency"] = trust_analysis.urgency_level
            
        except Exception as e:
            log_entry["error"] = str(e)
            # Default to neutral trust score on error
            state["trust_score"] = 50
            state["trust_reasoning"] = "Unable to analyze - defaulting to neutral"
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ========== NODE D: UNDERWRITER (Decision Engine) ==========
    async def underwriter_node(self, state: AgentState) -> AgentState:
        """Apply strict business rules for loan decision"""
        log_entry = {
            "node": "underwriter",
            "timestamp": datetime.now().isoformat(),
            "action": "loan_decision"
        }
        
        try:
            profile = state.get("customer_profile")
            trust_score = state.get("trust_score", 50)
            fraud_flags = state.get("fraud_flags", [])
            
            # NEW LEAD - Require Documentation
            if not state["customer_verified"]:
                state["loan_decision"] = "YELLOW_FLAG"
                state["interest_rate"] = 18.5
                state["loan_amount_eligible"] = 100000
                state["conditions"] = [
                    "Salary Slip (last 3 months)",
                    "Bank Statement (last 6 months)",
                    "PAN Card",
                    "Aadhaar Card"
                ]
                log_entry["decision"] = "new_customer_requires_docs"
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            # FRAUD FLAGS - Auto Decline
            if fraud_flags or trust_score < 30:
                state["loan_decision"] = "DECLINED"
                state["interest_rate"] = None
                state["loan_amount_eligible"] = 0
                state["conditions"] = []
                state["decline_reason"] = "Failed security verification"
                log_entry["decision"] = "declined_fraud"
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            # EXISTING CUSTOMER - Apply Underwriting Rules
            financial = profile.get("financial_data", {})
            behavioral = profile.get("behavioral_flags", {})
            
            credit_score = financial.get("credit_score", 0)
            debt_ratio = financial.get("debt_to_income_ratio", 0)
            risk_category = behavioral.get("risk_category", "UNKNOWN")
            
            # RULE 1: SUPER PRIME - Best Rates
            if credit_score >= 750 and trust_score >= 80 and debt_ratio < 0.3:
                state["loan_decision"] = "APPROVED"
                state["interest_rate"] = 10.5
                state["loan_amount_eligible"] = min(
                    financial.get("monthly_income", 0) * 60,  # 5 years of income
                    2000000
                )
                state["conditions"] = ["Salary slip for final verification"]
                log_entry["decision"] = "approved_prime"
            
            # RULE 2: PRIME - Good Rates
            elif credit_score >= 700 and trust_score >= 70 and debt_ratio < 0.4:
                state["loan_decision"] = "APPROVED"
                state["interest_rate"] = 12.5
                state["loan_amount_eligible"] = min(
                    financial.get("monthly_income", 0) * 48,
                    1500000
                )
                state["conditions"] = ["Salary slip", "Latest credit report"]
                log_entry["decision"] = "approved_standard"
            
            # RULE 3: MEDIUM RISK - Higher Rates + Documentation
            elif credit_score >= 600 and trust_score >= 50 and debt_ratio < 0.5:
                state["loan_decision"] = "YELLOW_FLAG"
                state["interest_rate"] = 18.5
                state["loan_amount_eligible"] = min(
                    financial.get("monthly_income", 0) * 36,
                    800000
                )
                state["conditions"] = [
                    "Salary slip (last 6 months)",
                    "Bank statement (last 12 months)",
                    "ITR (last 2 years)",
                    "Collateral or guarantor may be required"
                ]
                log_entry["decision"] = "conditional_approval"
            
            # RULE 4: DECLINE
            else:
                state["loan_decision"] = "DECLINED"
                state["interest_rate"] = None
                state["loan_amount_eligible"] = 0
                state["conditions"] = []
                
                # Determine decline reason
                if credit_score < 600:
                    state["decline_reason"] = "Credit score below minimum threshold (600)"
                elif debt_ratio >= 0.5:
                    state["decline_reason"] = "Debt-to-income ratio too high (>50%)"
                elif trust_score < 50:
                    state["decline_reason"] = "Unable to verify application authenticity"
                else:
                    state["decline_reason"] = "Does not meet current eligibility criteria"
                
                log_entry["decision"] = "declined_criteria"
            
            log_entry["credit_score"] = credit_score
            log_entry["trust_score"] = trust_score
            log_entry["final_decision"] = state["loan_decision"]
            
        except Exception as e:
            log_entry["error"] = str(e)
            # Default to decline on error
            state["loan_decision"] = "DECLINED"
            state["decline_reason"] = "System error - please retry"
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ========== NODE E: VOICE (Sales Agent) ==========
    async def voice_node(self, state: AgentState) -> AgentState:
        """Generate natural, empathetic response"""
        log_entry = {
            "node": "voice",
            "timestamp": datetime.now().isoformat(),
            "action": "response_generation"
        }
        
        try:
            # ⚡ SUPER FAST PATH: Use scripted response if already set
            if state.get("ai_response"):
                log_entry["fast_path"] = "scripted_response_already_set"
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            # ⚡ FAST PATH: Pre-written responses for decisions (save API quota)
            decision = state.get("loan_decision")
            name = state.get("name", "there")
            
            if decision == "APPROVED":
                amount = state.get("loan_amount_eligible", 0)
                rate = state.get("interest_rate", 0)
                state["ai_response"] = f"🎉 Congratulations {name}! Your loan application has been APPROVED! You're eligible for ₹{amount:,} at an interest rate of {rate}% per annum. I've generated your sanction letter. Would you like to proceed with the disbursement?"
                log_entry["fast_path"] = "approved_template"
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            elif decision == "YELLOW_FLAG":
                amount = state.get("loan_amount_eligible", 0)
                rate = state.get("interest_rate", 0)
                conditions = state.get("conditions", [])
                cond_text = "\n• ".join(conditions) if conditions else "additional documentation"
                state["ai_response"] = f"Hello {name}! We can offer you ₹{amount:,} at {rate}% per annum, but we need to verify a few things first. Please upload the following:\n• {cond_text}\n\nOnce verified, we can proceed with instant approval!"
                log_entry["fast_path"] = "conditional_template"
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            elif decision == "DECLINED":
                reason = state.get("decline_reason", "internal risk policies")
                state["ai_response"] = f"I apologize {name}, but we are unable to process your application at this time due to {reason}. I recommend checking your credit report and considering re-applying in 6-12 months after improving your credit profile."
                log_entry["fast_path"] = "declined_template"
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            # ⚡ FAST PATH: Missing info request
            if state.get("missing_info"):
                missing = state["missing_info"]
                if "phone" in missing and "name" in missing:
                    state["ai_response"] = "Welcome to Tata Capital! I can help you check your loan eligibility instantly. To begin, please tell me your full name and mobile number."
                elif "pan" in missing:
                    state["ai_response"] = f"Thank you {name}! To proceed with your loan application, I'll need your PAN card number for verification."
                else:
                    state["ai_response"] = f"Thank you for your interest! I need a bit more information to check your eligibility. Could you please provide: {', '.join(missing)}?"
                log_entry["fast_path"] = "missing_info_template"
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            # 🐢 SLOW PATH: Use Gemini for complex/general queries
            conversation_history = []
            for msg in state.get("messages", [])[-3:]:
                if isinstance(msg, dict):
                    if msg.get("role") == "user":
                        conversation_history.append(HumanMessage(content=msg["content"]))
                    elif msg.get("role") == "assistant":
                        conversation_history.append(AIMessage(content=msg["content"]))
            
            decision_info = {
                "loan_decision": decision,
                "interest_rate": state.get("interest_rate"),
                "loan_amount_eligible": state.get("loan_amount_eligible"),
                "conditions": state.get("conditions", []),
                "decline_reason": state.get("decline_reason")
            }
            
            # Generate response
            response = await self.gemini.generate_response(
                decision=decision_info,
                customer_name=name,
                conversation_context=conversation_history,
                stage=state.get("conversation_stage", "unknown")
            )
            
            state["ai_response"] = response
            log_entry["response_length"] = len(response)
            
        except Exception as e:
            log_entry["error"] = str(e)
            # Check if quota error
            if "429" in str(e) or "quota" in str(e).lower():
                state["ai_response"] = "I apologize, but our AI system is currently at capacity. However, I can still help you! Please call our customer service at 1800-209-8800 for immediate assistance."
            else:
                state["ai_response"] = "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ========== ROUTING LOGIC ==========
    def route_after_listener(self, state: AgentState) -> str:
        """
        Decide next node after entity extraction
        
        ROUTING LOGIC:
        - Demo Mode: Always go to voice (response already set in listener)
        - Production Mode: Route based on extracted information
        """
        # DEMO MODE: Go to voice to set response
        if DEMO_MODE or state.get("is_scripted"):
            print("🎬 DEMO ROUTE: Listener → Voice")
            return "voice"
        
        # PRODUCTION MODE: Standard agent flow
        if state.get("missing_info"):
            print("🤖 PRODUCTION ROUTE: Listener → Voice (ask for info)")
            return "voice"  # Ask for missing information
        else:
            print("🤖 PRODUCTION ROUTE: Listener → Gatekeeper (verify)")
            return "gatekeeper"  # Proceed with verification
    
    # ========== MAIN EXECUTION ==========
    async def process_message(self, user_message: str, conversation_history: List = None, previous_state: Dict = None) -> Dict[str, Any]:
        """
        Process a user message through the LangGraph state machine
        
        DUAL MODE OPERATION:
        - DEMO_MODE = True  → Scripted flows, instant responses
        - DEMO_MODE = False → Full Gemini AI processing
        
        Current Mode: {'DEMO (Scripted)' if DEMO_MODE else 'PRODUCTION (Gemini AI)'}
        """
        print(f"\n{'='*60}")
        print(f"🚀 SYSTEM MODE: {'🎬 DEMO MODE' if DEMO_MODE else '🤖 PRODUCTION MODE'}")
        print(f"{'='*60}\n")
        
        # Initialize state with previous state preservation
        initial_state = {
            "messages": conversation_history or [],
            "current_message": user_message,
            "name": None,
            "phone": None,
            "pan": None,
            "intent": None,
            "customer_verified": False,
            "customer_profile": None,
            "verification_status": None,
            "trust_score": 50,
            "trust_reasoning": "",
            "fraud_flags": [],
            "loan_decision": None,
            "interest_rate": None,
            "loan_amount_eligible": None,
            "conditions": [],
            "ai_response": "",
            "conversation_stage": "initial",
            "missing_info": [],
            "admin_log": [],
            # Preserve demo state from previous session
            "demo_script": previous_state.get("demo_script") if previous_state else None,
            "demo_step": previous_state.get("demo_step", 1) if previous_state else 1,
            "docs_uploaded": previous_state.get("docs_uploaded", 0) if previous_state else 0
        }
        
        # Add current message to history
        initial_state["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Execute graph
        final_state = await self.graph.ainvoke(initial_state)
        
        # Debug logging
        print(f"\n📊 FINAL STATE:")
        print(f"Demo Script: {final_state.get('demo_script')}")
        print(f"Demo Step: {final_state.get('demo_step')}")
        print(f"Show Upload: {final_state.get('show_upload')}")
        print(f"Show Sanction: {final_state.get('show_sanction_letter')}\n")
        
        # Add AI response to messages
        final_state["messages"].append({
            "role": "assistant",
            "content": final_state["ai_response"],
            "timestamp": datetime.now().isoformat()
        })
        
        return final_state


# ==================== HELPER FUNCTIONS ====================
async def create_agent(gemini_api_key: str) -> LoanAgentGraph:
    """Factory function to create the agent"""
    return LoanAgentGraph(gemini_api_key)
