#!/usr/bin/env python3
"""
================================================================================
CONTROLLED INTELLIGENCE MODULE
================================================================================
Banking-Compliant Smart Input Processing

This module implements CONTROLLED INTELLIGENCE for input handling in a 
banking chatbot. It adds smart understanding while maintaining strict
stage-based progression rules.

CORE PRINCIPLE: Understanding != Progression

Intent detection is for UNDERSTANDING only.
STAGE MACHINE controls progression.

KEY FEATURES:
1. Bounded intent recognition (only allowed intents)
2. Stage-bound filtering (only accept matching intent)
3. Fuzzy input handling (typos, variants)
4. Format flexibility (amounts, names)
5. Multi-answer buffering (store for later)
6. Ambiguity detection (ask for clarification)
7. Safety guards (premature inputs, anomalies)

================================================================================
"""

import re
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logger = logging.getLogger("CTRL_INTEL")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(handler)


# ================================================================================
# PART 1: ALLOWED INTENTS (STRICT LIST - NO EXCEPTIONS)
# ================================================================================

class AllowedIntent(Enum):
    """
    The ONLY intents our system recognizes.
    
    This is a CLOSED set. Any input that doesn't map to these
    intents is classified as UNKNOWN.
    
    WHY CLOSED SET:
    - Prevents intent injection attacks
    - Makes behavior predictable
    - Simplifies compliance auditing
    - Reduces edge case handling
    """
    # Core loan application intents
    LOAN_PURPOSE = "loan_purpose"
    LOAN_AMOUNT = "loan_amount"
    CITY = "city"
    EMPLOYMENT_TYPE = "employment_type"
    
    # Identity intents
    NAME = "name"
    MOBILE_NUMBER = "mobile_number"
    OTP = "otp"
    PAN = "pan"
    AADHAAR = "aadhaar"
    
    # Control intents
    CONFIRMATION = "confirmation"
    GREETING = "greeting"
    HELP = "help"
    
    # Fallback
    UNKNOWN = "unknown"


# ================================================================================
# PART 2: STAGE-TO-INTENT MAPPING
# ================================================================================

# Maps each stage to the SINGLE intent it expects
# If user's intent doesn't match, their answer is BUFFERED, not accepted
STAGE_EXPECTED_INTENT: Dict[str, AllowedIntent] = {
    # Initial stages
    "NEEDS_PURPOSE": AllowedIntent.LOAN_PURPOSE,
    "NEEDS_LOAN_PURPOSE": AllowedIntent.LOAN_PURPOSE,
    
    # Amount stage
    "NEEDS_AMOUNT": AllowedIntent.LOAN_AMOUNT,
    "NEEDS_LOAN_AMOUNT": AllowedIntent.LOAN_AMOUNT,
    
    # Location stage
    "NEEDS_CITY": AllowedIntent.CITY,
    
    # Employment stage
    "NEEDS_EMPLOYMENT": AllowedIntent.EMPLOYMENT_TYPE,
    "NEEDS_EMPLOYMENT_TYPE": AllowedIntent.EMPLOYMENT_TYPE,
    
    # Identity stages
    "NEEDS_NAME": AllowedIntent.NAME,
    "NEEDS_MOBILE": AllowedIntent.MOBILE_NUMBER,
    "NEEDS_MOBILE_NUMBER": AllowedIntent.MOBILE_NUMBER,
    "AWAITING_OTP": AllowedIntent.OTP,
    "NEEDS_OTP": AllowedIntent.OTP,
    
    # KYC stages
    "NEEDS_PAN": AllowedIntent.PAN,
    "NEEDS_AADHAAR": AllowedIntent.AADHAAR,
    
    # Confirmation stages
    "AWAITING_CONFIRMATION": AllowedIntent.CONFIRMATION,
    "NEEDS_CONFIRMATION": AllowedIntent.CONFIRMATION,
    "LOAN_OFFER_PRESENTED": AllowedIntent.CONFIRMATION,
    
    # Greeting/Start
    "GREETING": AllowedIntent.GREETING,
    "START": AllowedIntent.GREETING,
}

# Reverse mapping for debugging
INTENT_TO_STAGES: Dict[AllowedIntent, List[str]] = {}
for stage, intent in STAGE_EXPECTED_INTENT.items():
    if intent not in INTENT_TO_STAGES:
        INTENT_TO_STAGES[intent] = []
    INTENT_TO_STAGES[intent].append(stage)


# ================================================================================
# PART 3: FUZZY INPUT HANDLING - SPELLING CORRECTIONS
# ================================================================================

# Dictionary-based corrections (NO ML, fully auditable)
SPELLING_CORRECTIONS: Dict[str, str] = {
    # City name corrections (common typos)
    "mumabi": "mumbai",
    "mubmai": "mumbai",
    "bombay": "mumbai",
    "dlehi": "delhi",
    "dehli": "delhi",
    "new dehli": "new delhi",
    "banglaore": "bangalore",
    "banglore": "bangalore",
    "bengaluru": "bangalore",
    "bangaluru": "bangalore",
    "hydrabad": "hyderabad",
    "hyderbad": "hyderabad",
    "chenai": "chennai",
    "madras": "chennai",
    "calcutta": "kolkata",
    "kolkatta": "kolkata",
    "kolkota": "kolkata",
    "pune": "pune",
    "poona": "pune",
    "ahemdabad": "ahmedabad",
    "ahmadabad": "ahmedabad",
    "ahmedabd": "ahmedabad",
    "jaiupr": "jaipur",
    "jaipru": "jaipur",
    "lucknwo": "lucknow",
    "luckno": "lucknow",
    "gurgaon": "gurugram",
    "nodia": "noida",
    "noidaa": "noida",
    "ghaziabda": "ghaziabad",
    "faridabd": "faridabad",
    
    # Employment type corrections
    "salried": "salaried",
    "salareid": "salaried",
    "saleried": "salaried",
    "self empolyed": "self employed",
    "self-empolyed": "self employed",
    "selfemployed": "self employed",
    "self-employed": "self employed",
    "busines": "business",
    "buisness": "business",
    "bussiness": "business",
    "profesional": "professional",
    "proffesional": "professional",
    "professonal": "professional",
    "freelacner": "freelancer",
    "freelanser": "freelancer",
    "freelncer": "freelancer",
    
    # Loan purpose corrections
    "rennovation": "renovation",
    "renovaton": "renovation",
    "homerenovation": "home renovation",
    "home renovaton": "home renovation",
    "home improvment": "home improvement",
    "home improvemnt": "home improvement",
    "edcuation": "education",
    "educaton": "education",
    "educatoin": "education",
    "medcial": "medical",
    "medicla": "medical",
    "madical": "medical",
    "wedidng": "wedding",
    "weding": "wedding",
    "marriege": "marriage",
    "marraige": "marriage",
    "tarvel": "travel",
    "travle": "travel",
    "vacaton": "vacation",
    "vaccation": "vacation",
    "personel": "personal",
    "persoanl": "personal",
    "busness": "business",
    "busniss": "business",
    
    # Confirmation corrections
    "yse": "yes",
    "eys": "yes",
    "yess": "yes",
    "yup": "yes",
    "yep": "yes",
    "yea": "yes",
    "yeah": "yes",
    "ya": "yes",
    "ok": "yes",
    "okay": "yes",
    "sure": "yes",
    "correct": "yes",
    "right": "yes",
    "nope": "no",
    "nah": "no",
    "noo": "no",
    "naah": "no",
    "wrong": "no",
    "incorrect": "no",
}

# Number word to digit mapping
NUMBER_WORDS: Dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100,
    "thousand": 1000, "lakh": 100000, "lakhs": 100000,
    "lac": 100000, "lacs": 100000, "crore": 10000000, "crores": 10000000,
    "million": 1000000, "millions": 1000000,
    "billion": 1000000000, "billions": 1000000000,
}


# ================================================================================
# PART 4: DATA CLASSES FOR PROCESSING
# ================================================================================

@dataclass
class DetectedIntent:
    """Represents a detected intent with its extracted value."""
    intent: AllowedIntent
    value: Any
    confidence: float = 1.0  # Dictionary-based = always 1.0
    raw_match: str = ""  # The portion of input that matched


@dataclass
class BufferedAnswer:
    """An answer stored for a future stage."""
    intent: AllowedIntent
    value: Any
    detected_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 300  # 5 minutes default


@dataclass
class ProcessingResult:
    """Result of processing user input through controlled intelligence."""
    accepted: bool  # Was the input accepted for current stage?
    extracted_value: Any = None  # The value extracted (if accepted)
    normalized_input: str = ""  # Input after normalization
    buffered_intents: List[DetectedIntent] = field(default_factory=list)
    clarification_needed: bool = False
    clarification_prompt: str = ""
    safety_warning: Optional[str] = None
    detected_intents: List[DetectedIntent] = field(default_factory=list)
    stage_expected: Optional[AllowedIntent] = None
    rejection_reason: str = ""


# ================================================================================
# PART 5: SAFE INPUT NORMALIZER
# ================================================================================

class SafeInputNormalizer:
    """
    Normalizes user input using DICTIONARY-BASED corrections.
    
    WHY DICTIONARY-BASED:
    - Fully auditable (every correction is explicit)
    - No ML model drift
    - Predictable behavior
    - Easy to add/remove corrections
    - Compliant with banking regulations
    
    WHAT IT DOES:
    - Fixes common typos
    - Converts amount formats (5L -> 500000)
    - Standardizes city names
    - Normalizes yes/no variations
    
    WHAT IT DOESN'T DO:
    - Infer meaning from context
    - Correct unknown words
    - Change the semantic meaning
    """
    
    def __init__(self):
        self.corrections = SPELLING_CORRECTIONS
        self.number_words = NUMBER_WORDS
        
    def normalize(self, text: str) -> str:
        """
        Apply all normalizations to input text.
        
        Args:
            text: Raw user input
            
        Returns:
            Normalized text with corrections applied
        """
        if not text:
            return ""
            
        # Strip and lowercase
        normalized = text.strip().lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Apply dictionary corrections
        words = normalized.split()
        corrected_words = []
        for word in words:
            # Check single word
            if word in self.corrections:
                corrected_words.append(self.corrections[word])
            else:
                corrected_words.append(word)
                
        normalized = ' '.join(corrected_words)
        
        # Check multi-word corrections
        for wrong, right in self.corrections.items():
            if wrong in normalized:
                normalized = normalized.replace(wrong, right)
                
        return normalized
    
    def convert_amount(self, text: str) -> Optional[float]:
        """
        Convert amount text to number.
        
        Handles:
        - "5 lakhs" -> 500000
        - "5L" -> 500000
        - "5,00,000" -> 500000
        - "Rs 500000" -> 500000
        - "INR 5 lakh" -> 500000
        - "five lakhs" -> 500000
        - "50K" -> 50000
        - "1.5 crore" -> 15000000
        - "15 lacs" -> 1500000
        
        Args:
            text: Amount text to convert
            
        Returns:
            Float amount or None if not parseable
        """
        if not text:
            return None
            
        text = text.strip().lower()
        
        # Remove currency symbols and words
        text = re.sub(r'[₹$]', '', text)
        text = re.sub(r'\b(rs\.?|inr|rupees?)\b', '', text, flags=re.IGNORECASE)
        text = text.strip()
        
        # Remove commas (Indian and international format)
        text = text.replace(',', '')
        
        # Handle K/L/Cr suffixes
        # 5K, 50k -> multiply by 1000
        match = re.match(r'^([\d.]+)\s*k$', text)
        if match:
            return float(match.group(1)) * 1000
            
        # 5L, 5lac, 5lakh, 5lakhs
        match = re.match(r'^([\d.]+)\s*(l|lac|lacs|lakh|lakhs?)$', text)
        if match:
            return float(match.group(1)) * 100000
            
        # 5cr, 5crore, 5crores
        match = re.match(r'^([\d.]+)\s*(cr|crore|crores?)$', text)
        if match:
            return float(match.group(1)) * 10000000
            
        # Handle word numbers: "five lakhs"
        for word, value in self.number_words.items():
            if word in text:
                # Extract number before the multiplier
                # "5 lakhs" -> 5 * 100000
                # "five lakhs" -> 5 * 100000
                if word in ['lakh', 'lakhs', 'lac', 'lacs']:
                    # Find the number before lakh
                    num_match = re.search(r'([\d.]+)\s*' + word, text)
                    if num_match:
                        return float(num_match.group(1)) * 100000
                    # Check for word number
                    for num_word, num_val in self.number_words.items():
                        if num_word in text and num_val < 100:
                            return num_val * 100000
                elif word in ['crore', 'crores']:
                    num_match = re.search(r'([\d.]+)\s*' + word, text)
                    if num_match:
                        return float(num_match.group(1)) * 10000000
                    for num_word, num_val in self.number_words.items():
                        if num_word in text and num_val < 100:
                            return num_val * 10000000
                            
        # Try direct number parsing
        try:
            # Handle "500000" or "5.5"
            return float(text)
        except ValueError:
            pass
            
        # Handle word numbers without multipliers: "fifty thousand"
        total = 0
        current = 0
        for word in text.split():
            if word in self.number_words:
                val = self.number_words[word]
                if val >= 1000:
                    if current == 0:
                        current = 1
                    total += current * val
                    current = 0
                elif val >= 100:
                    current *= val
                else:
                    current += val
        if current > 0:
            total += current
        if total > 0:
            return float(total)
            
        return None


# ================================================================================
# PART 6: CONTROLLED INTENT DETECTOR
# ================================================================================

class ControlledIntentDetector:
    """
    Detects user intents from input text.
    
    CRITICAL RULES:
    1. Only detects intents from AllowedIntent enum
    2. Uses pattern matching, not ML
    3. Returns ALL detected intents (multi-intent support)
    4. Does NOT decide which intent to use (that's the stage filter's job)
    5. High precision over high recall (better to miss than misclassify)
    """
    
    def __init__(self):
        self.normalizer = SafeInputNormalizer()
        
        # Valid cities list (expandable)
        self.valid_cities = {
            "mumbai", "delhi", "new delhi", "bangalore", "bengaluru",
            "hyderabad", "chennai", "kolkata", "pune", "ahmedabad",
            "jaipur", "lucknow", "kanpur", "nagpur", "indore",
            "thane", "bhopal", "visakhapatnam", "patna", "vadodara",
            "ghaziabad", "ludhiana", "agra", "nashik", "faridabad",
            "meerut", "rajkot", "varanasi", "srinagar", "aurangabad",
            "dhanbad", "amritsar", "navi mumbai", "allahabad", "ranchi",
            "howrah", "coimbatore", "jabalpur", "gwalior", "vijayawada",
            "jodhpur", "madurai", "raipur", "kota", "chandigarh",
            "guwahati", "solapur", "hubli", "mysore", "tiruchirappalli",
            "bareilly", "aligarh", "tiruppur", "moradabad", "jalandhar",
            "bhubaneswar", "salem", "warangal", "guntur", "bhiwandi",
            "saharanpur", "gorakhpur", "bikaner", "amravati", "noida",
            "jamshedpur", "bhilai", "cuttack", "firozabad", "kochi",
            "nellore", "bhavnagar", "dehradun", "durgapur", "asansol",
            "rourkela", "nanded", "kolhapur", "ajmer", "akola",
            "gulbarga", "jamnagar", "ujjain", "loni", "siliguri",
            "jhansi", "ulhasnagar", "jammu", "sangli", "mangalore",
            "erode", "belgaum", "ambattur", "tirunelveli", "malegaon",
            "gaya", "jalgaon", "udaipur", "maheshtala", "gurugram",
        }
        
        # Loan purpose keywords
        self.purpose_keywords = {
            "home renovation": ["home renovation", "renovation", "renovate", "remodel", "remodeling"],
            "home improvement": ["home improvement", "improve home", "upgrade home", "repairs"],
            "education": ["education", "studies", "study", "college", "university", "school", "course", "tuition"],
            "medical": ["medical", "health", "hospital", "treatment", "surgery", "healthcare"],
            "wedding": ["wedding", "marriage", "shaadi"],
            "travel": ["travel", "vacation", "holiday", "trip", "tour"],
            "business": ["business", "startup", "shop", "store", "inventory", "working capital"],
            "debt consolidation": ["debt", "consolidation", "pay off", "clear loans", "settle"],
            "personal": ["personal", "personal use", "personal needs"],
            "vehicle": ["car", "vehicle", "bike", "two wheeler", "automobile"],
            "emergency": ["emergency", "urgent", "immediate"],
        }
        
        # Employment type keywords
        self.employment_keywords = {
            "salaried": ["salaried", "salary", "employed", "job", "working", "employee", "service"],
            "self employed": ["self employed", "self-employed", "own business", "proprietor", "entrepreneur"],
            "business": ["business", "businessman", "businesswoman", "shop owner", "trader"],
            "professional": ["professional", "doctor", "lawyer", "ca", "chartered accountant", "consultant"],
            "freelancer": ["freelancer", "freelance", "contractor", "gig", "independent"],
            "retired": ["retired", "pension", "pensioner"],
            "student": ["student", "studying"],
        }
        
    def detect_all(self, text: str) -> List[DetectedIntent]:
        """
        Detect ALL intents present in the input.
        
        Args:
            text: User input
            
        Returns:
            List of all detected intents with values
        """
        if not text:
            return []
            
        # Normalize first
        normalized = self.normalizer.normalize(text)
        detected = []
        
        # Check each intent type
        # Order matters: more specific checks first
        
        # 1. Check for OTP (6 digits)
        otp = self._detect_otp(normalized)
        if otp:
            detected.append(DetectedIntent(AllowedIntent.OTP, otp, raw_match=otp))
            
        # 2. Check for PAN (AAAAA9999A format)
        pan = self._detect_pan(text)  # Use original for case sensitivity
        if pan:
            detected.append(DetectedIntent(AllowedIntent.PAN, pan, raw_match=pan))
            
        # 3. Check for Aadhaar (12 digits)
        aadhaar = self._detect_aadhaar(normalized)
        if aadhaar:
            detected.append(DetectedIntent(AllowedIntent.AADHAAR, aadhaar, raw_match=aadhaar))
            
        # 4. Check for mobile (10 digits)
        mobile = self._detect_mobile(normalized)
        if mobile:
            detected.append(DetectedIntent(AllowedIntent.MOBILE_NUMBER, mobile, raw_match=mobile))
            
        # 5. Check for amount
        amount = self._detect_amount(normalized)
        if amount:
            detected.append(DetectedIntent(AllowedIntent.LOAN_AMOUNT, amount, raw_match=str(amount)))
            
        # 6. Check for city
        city = self._detect_city(normalized)
        if city:
            detected.append(DetectedIntent(AllowedIntent.CITY, city, raw_match=city))
            
        # 7. Check for employment type
        employment = self._detect_employment(normalized)
        if employment:
            detected.append(DetectedIntent(AllowedIntent.EMPLOYMENT_TYPE, employment, raw_match=employment))
            
        # 8. Check for loan purpose
        purpose = self._detect_purpose(normalized)
        if purpose:
            detected.append(DetectedIntent(AllowedIntent.LOAN_PURPOSE, purpose, raw_match=purpose))
            
        # 9. Check for name (if looks like a name)
        name = self._detect_name(text)  # Use original for case
        if name:
            detected.append(DetectedIntent(AllowedIntent.NAME, name, raw_match=name))
            
        # 10. Check for confirmation
        confirmation = self._detect_confirmation(normalized)
        if confirmation is not None:
            detected.append(DetectedIntent(AllowedIntent.CONFIRMATION, confirmation, raw_match=str(confirmation)))
            
        # 11. Check for greeting
        if self._is_greeting(normalized):
            detected.append(DetectedIntent(AllowedIntent.GREETING, True, raw_match=normalized))
            
        # If nothing detected, mark as UNKNOWN
        if not detected:
            detected.append(DetectedIntent(AllowedIntent.UNKNOWN, text, raw_match=text))
            
        return detected
    
    def _detect_otp(self, text: str) -> Optional[str]:
        """Detect 6-digit OTP."""
        # Look for exactly 6 digits
        match = re.search(r'\b(\d{6})\b', text)
        if match:
            return match.group(1)
        return None
    
    def _detect_pan(self, text: str) -> Optional[str]:
        """Detect PAN number (AAAAA9999A format)."""
        # PAN is 5 letters, 4 digits, 1 letter
        match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text.upper())
        if match:
            return match.group(1)
        return None
    
    def _detect_aadhaar(self, text: str) -> Optional[str]:
        """Detect Aadhaar number (12 digits)."""
        # Remove spaces and look for 12 digits
        clean = re.sub(r'\s', '', text)
        match = re.search(r'\b(\d{12})\b', clean)
        if match:
            return match.group(1)
        # Also check with spaces (XXXX XXXX XXXX format)
        match = re.search(r'(\d{4}\s?\d{4}\s?\d{4})', text)
        if match:
            return re.sub(r'\s', '', match.group(1))
        return None
    
    def _detect_mobile(self, text: str) -> Optional[str]:
        """Detect 10-digit mobile number."""
        # Remove country code prefixes at start (not single 0s anywhere)
        clean = text
        clean = re.sub(r'^\+91\s*', '', clean)  # +91 at start
        clean = re.sub(r'^91\s*', '', clean)    # 91 at start
        clean = re.sub(r'^0\s*', '', clean)     # 0 at start (STD prefix)
        clean = re.sub(r'[\s\-]', '', clean)
        # Look for 10 digits starting with 6-9
        match = re.search(r'([6-9]\d{9})', clean)
        if match:
            return match.group(1)
        return None
    
    def _detect_amount(self, text: str) -> Optional[float]:
        """Detect loan amount. Excludes 10-digit numbers that look like phone numbers."""
        # First check if this looks like a phone number (10 digits starting with 6-9)
        clean = re.sub(r'[\s\-,]', '', text)
        phone_match = re.search(r'^[6-9]\d{9}$', clean)
        if phone_match:
            return None  # This is a phone number, not an amount
        return self.normalizer.convert_amount(text)
    
    def _detect_city(self, text: str) -> Optional[str]:
        """Detect city name."""
        normalized = self.normalizer.normalize(text)
        words = normalized.split()
        
        # Check for city in valid cities list
        for city in self.valid_cities:
            if city in normalized:
                return city.title()
                
        # Check individual words
        for word in words:
            if word in self.valid_cities:
                return word.title()
                
        return None
    
    def _detect_employment(self, text: str) -> Optional[str]:
        """Detect employment type."""
        text_lower = text.lower()
        
        for emp_type, keywords in self.employment_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return emp_type
        return None
    
    def _detect_purpose(self, text: str) -> Optional[str]:
        """Detect loan purpose."""
        text_lower = text.lower()
        
        for purpose, keywords in self.purpose_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return purpose
        return None
    
    def _detect_name(self, text: str) -> Optional[str]:
        """
        Detect if input looks like a name.
        
        Heuristics:
        - 2-4 words
        - Each word starts with capital (in original)
        - No numbers
        - Not a command or question
        """
        # Skip if contains numbers (except name suffixes like III)
        if re.search(r'\d', text):
            return None
            
        # Skip if it's a command or question
        skip_patterns = [
            r'^(hi|hello|hey|yes|no|ok|okay)',
            r'\?$',
            r'^(what|how|when|where|why|can|will|is|are)',
        ]
        for pattern in skip_patterns:
            if re.search(pattern, text.lower()):
                return None
                
        # Check word count (2-4 words typical for names)
        words = text.split()
        if len(words) < 1 or len(words) > 5:
            return None
            
        # Check if looks like proper noun (each word capitalized)
        # Allow "my name is X" pattern
        name_match = re.search(r"(?:my name is|i am|i'm|this is)\s+(.+)", text, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
            return name.title()
            
        # If single word or all words start with caps
        if all(word[0].isupper() for word in words if word):
            return text.strip()
            
        return None
    
    def _detect_confirmation(self, text: str) -> Optional[bool]:
        """Detect yes/no confirmation."""
        text = text.lower().strip()
        
        yes_patterns = ['yes', 'yep', 'yup', 'yeah', 'ya', 'y', 'ok', 'okay', 'sure', 
                        'correct', 'right', 'confirm', 'proceed', 'continue', 'accept',
                        'agreed', 'agree', 'fine', 'alright', 'absolutely', 'definitely']
        no_patterns = ['no', 'nope', 'nah', 'n', 'wrong', 'incorrect', 'cancel', 
                       'stop', 'reject', 'decline', 'negative', 'not', "don't"]
        
        for pattern in yes_patterns:
            if pattern == text or text.startswith(pattern + ' '):
                return True
                
        for pattern in no_patterns:
            if pattern == text or text.startswith(pattern + ' '):
                return False
                
        return None
    
    def _is_greeting(self, text: str) -> bool:
        """Check if input is a greeting."""
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 
                     'good evening', 'namaste', 'namaskar', 'howdy']
        text = text.lower().strip()
        return text in greetings or any(text.startswith(g) for g in greetings)
    
    def filter_by_stage(self, intents: List[DetectedIntent], current_stage: str) -> Tuple[Optional[DetectedIntent], List[DetectedIntent]]:
        """
        Filter detected intents based on current stage.
        
        Args:
            intents: All detected intents
            current_stage: Current stage from state machine
            
        Returns:
            Tuple of (accepted_intent, buffered_intents)
        """
        expected = STAGE_EXPECTED_INTENT.get(current_stage)
        if not expected:
            logger.warning(f"Unknown stage: {current_stage}, no expected intent")
            return None, intents
            
        accepted = None
        buffered = []
        
        for intent in intents:
            if intent.intent == expected:
                accepted = intent
            elif intent.intent != AllowedIntent.UNKNOWN:
                buffered.append(intent)
                
        return accepted, buffered


# ================================================================================
# PART 7: AMBIGUITY DETECTOR
# ================================================================================

class AmbiguityDetector:
    """
    Detects when user input is ambiguous and needs clarification.
    
    TRIGGERS CLARIFICATION:
    - "maybe", "around", "approximately"
    - "or" between options
    - Question marks in answers
    - Ranges ("5-10 lakhs")
    - Hedging language
    
    WHY THIS MATTERS:
    - Banking decisions need precise inputs
    - Ambiguous data leads to disputes
    - Better to ask than assume
    """
    
    # Ambiguity markers
    UNCERTAINTY_MARKERS = [
        "maybe", "perhaps", "probably", "might", "could be",
        "around", "approximately", "about", "roughly", "nearly",
        "somewhere", "something like", "more or less",
        "i think", "i guess", "not sure", "unsure",
        "i believe", "possibly"
    ]
    
    RANGE_PATTERNS = [
        r'\d+\s*-\s*\d+',  # 5-10
        r'\d+\s*to\s*\d+',  # 5 to 10
        r'between\s*\d+\s*and\s*\d+',  # between 5 and 10
    ]
    
    OR_PATTERN = r'\b(or|/)\b'  # "mumbai or delhi" or "mumbai/delhi"
    
    def __init__(self):
        pass
        
    def check_ambiguity(self, text: str, expected_intent: AllowedIntent) -> Tuple[bool, str]:
        """
        Check if input is ambiguous for the expected intent.
        
        Args:
            text: User input
            expected_intent: What we're expecting
            
        Returns:
            Tuple of (is_ambiguous, clarification_prompt)
        """
        text_lower = text.lower()
        
        # Check for uncertainty markers
        for marker in self.UNCERTAINTY_MARKERS:
            if marker in text_lower:
                return True, self._get_clarification_prompt(expected_intent, "uncertainty")
                
        # Check for ranges
        for pattern in self.RANGE_PATTERNS:
            if re.search(pattern, text_lower):
                return True, self._get_clarification_prompt(expected_intent, "range")
                
        # Check for "or" alternatives
        if re.search(self.OR_PATTERN, text_lower):
            return True, self._get_clarification_prompt(expected_intent, "alternatives")
            
        # Check for question in answer
        if '?' in text and expected_intent not in [AllowedIntent.GREETING, AllowedIntent.HELP]:
            return True, self._get_clarification_prompt(expected_intent, "question")
            
        return False, ""
    
    def _get_clarification_prompt(self, intent: AllowedIntent, reason: str) -> str:
        """Generate appropriate clarification prompt."""
        prompts = {
            AllowedIntent.LOAN_AMOUNT: {
                "uncertainty": "Please provide the exact loan amount you need. For example: '5 lakhs' or '500000'.",
                "range": "Please specify a single amount rather than a range. What exact amount do you need?",
                "alternatives": "Please choose one specific amount for your loan application.",
                "question": "Let me help clarify. What exact loan amount would you like to apply for?",
            },
            AllowedIntent.CITY: {
                "uncertainty": "Please confirm your city of residence.",
                "range": "Please specify your primary city of residence.",
                "alternatives": "Please provide your primary city of residence.",
                "question": "Which city do you currently live in?",
            },
            AllowedIntent.EMPLOYMENT_TYPE: {
                "uncertainty": "Please confirm your employment type: salaried, self-employed, or business owner?",
                "range": "Please specify your primary employment type.",
                "alternatives": "Please select your primary employment type.",
                "question": "Are you salaried, self-employed, or a business owner?",
            },
            AllowedIntent.LOAN_PURPOSE: {
                "uncertainty": "Please specify the exact purpose for this loan.",
                "range": "Please provide your primary purpose for the loan.",
                "alternatives": "Please mention the main purpose for this loan.",
                "question": "What will you use this loan for?",
            },
            AllowedIntent.CONFIRMATION: {
                "uncertainty": "Please confirm with a clear 'yes' or 'no'.",
                "range": "Please respond with 'yes' to confirm or 'no' to decline.",
                "alternatives": "Please provide a clear confirmation: yes or no?",
                "question": "Would you like to proceed? Please reply yes or no.",
            },
        }
        
        default_prompts = {
            "uncertainty": "Please provide a clear, specific answer.",
            "range": "Please provide a single specific value.",
            "alternatives": "Please choose one option.",
            "question": "I need your answer to proceed.",
        }
        
        intent_prompts = prompts.get(intent, default_prompts)
        return intent_prompts.get(reason, default_prompts[reason])


# ================================================================================
# PART 8: INPUT SAFETY GUARD
# ================================================================================

class InputSafetyGuard:
    """
    Guards against unsafe or suspicious input patterns.
    
    CHECKS:
    1. Premature input (PAN before KYC stage)
    2. Out-of-context input (emojis, scripts, SQL)
    3. Re-answer attempts (already provided this)
    4. Session anomalies (too fast, pattern gaming)
    """
    
    # Stages where KYC data should NOT be provided
    PRE_KYC_STAGES = {
        "GREETING", "START", "NEEDS_PURPOSE", "NEEDS_LOAN_PURPOSE",
        "NEEDS_AMOUNT", "NEEDS_LOAN_AMOUNT", "NEEDS_CITY",
        "NEEDS_EMPLOYMENT", "NEEDS_EMPLOYMENT_TYPE",
    }
    
    # Suspicious patterns
    SQL_PATTERNS = [
        r"(\b(select|insert|update|delete|drop|union|exec|execute)\b.*\b(from|into|where|table)\b)",
        r"(--|\"|;|'|\*|=)",
        r"(\bor\b\s+\d+\s*=\s*\d+)",
    ]
    
    SCRIPT_PATTERNS = [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
        r"\{\{.*\}\}",
    ]
    
    def __init__(self):
        self.answer_history: Dict[str, List[Tuple[str, datetime]]] = {}
        
    def check_premature_input(self, text: str, current_stage: str) -> Optional[str]:
        """
        Check if user is providing KYC data before appropriate stage.
        
        Args:
            text: User input
            current_stage: Current stage
            
        Returns:
            Warning message if premature, None otherwise
        """
        if current_stage not in self.PRE_KYC_STAGES:
            return None
            
        # Check for PAN
        if re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', text.upper()):
            return "I noticed you've shared what looks like a PAN number. We'll ask for KYC details at the appropriate stage to keep your data secure."
            
        # Check for Aadhaar
        if re.search(r'\b\d{12}\b', text.replace(' ', '')):
            return "I noticed you've shared what looks like an Aadhaar number. We'll ask for KYC details when we reach that stage."
            
        return None
    
    def check_out_of_context(self, text: str) -> Optional[str]:
        """
        Check for potentially malicious or out-of-context input.
        
        Args:
            text: User input
            
        Returns:
            Warning message if suspicious, None otherwise
        """
        # Check SQL injection patterns
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, text.lower()):
                logger.warning(f"Potential SQL injection detected: {text[:50]}")
                return "Your input contains characters that our system cannot process. Please provide a simple text response."
                
        # Check script injection
        for pattern in self.SCRIPT_PATTERNS:
            if re.search(pattern, text.lower()):
                logger.warning(f"Potential script injection detected: {text[:50]}")
                return "Your input contains characters that our system cannot process. Please provide a simple text response."
                
        # Check for excessive special characters
        special_count = len(re.findall(r'[^a-zA-Z0-9\s.,\'"-]', text))
        if special_count > len(text) * 0.3:
            return "Your input contains too many special characters. Please provide a simple text response."
            
        return None
    
    def check_re_answer(self, intent: AllowedIntent, value: Any, session_id: str) -> Optional[str]:
        """
        Check if user is re-providing an already-answered value.
        
        Args:
            intent: The detected intent
            value: The value provided
            session_id: Current session ID
            
        Returns:
            Info message if re-answer, None otherwise
        """
        key = f"{session_id}_{intent.value}"
        history = self.answer_history.get(key, [])
        
        # Check if same value provided before
        for prev_value, timestamp in history:
            if str(prev_value).lower() == str(value).lower():
                time_diff = (datetime.now() - timestamp).seconds
                if time_diff < 60:  # Within 1 minute
                    return f"I already have this information recorded. Let me continue with the next question."
                    
        # Record this answer
        if key not in self.answer_history:
            self.answer_history[key] = []
        self.answer_history[key].append((value, datetime.now()))
        
        # Keep only last 5 answers
        self.answer_history[key] = self.answer_history[key][-5:]
        
        return None
    
    def check_session_anomaly(self, session_id: str, current_stage: str, 
                             input_count: int, session_duration_seconds: int) -> Optional[str]:
        """
        Check for session-level anomalies.
        
        Args:
            session_id: Session identifier
            current_stage: Current stage
            input_count: Number of inputs in session
            session_duration_seconds: How long session has been active
            
        Returns:
            Warning if anomaly detected, None otherwise
        """
        # Check for unusually fast progression
        if input_count > 10 and session_duration_seconds < 30:
            logger.warning(f"Session {session_id}: Unusually fast input rate")
            return None  # Log but don't block
            
        # Check for stuck in same stage
        # (This would need more context - left as placeholder)
        
        return None


# ================================================================================
# PART 9: ANSWER BUFFER
# ================================================================================

class AnswerBuffer:
    """
    Buffers answers that don't match the current stage.
    
    When user provides multiple answers at once:
    - Accept the one for current stage
    - Buffer the rest for later
    - Auto-fill when we reach those stages
    
    Example:
    User: "I'm Rahul from Mumbai, need 5 lakhs"
    Stage: NEEDS_PURPOSE
    
    - Accept: Nothing (no purpose mentioned)
    - Buffer: NAME=Rahul, CITY=Mumbai, AMOUNT=500000
    
    Later, at NEEDS_NAME stage:
    - System: "What is your name?"
    - Auto-fill from buffer: "I have your name as Rahul. Is that correct?"
    """
    
    def __init__(self, ttl_seconds: int = 300):
        self.buffer: Dict[str, Dict[AllowedIntent, BufferedAnswer]] = {}
        self.ttl_seconds = ttl_seconds
        
    def store(self, session_id: str, intent: AllowedIntent, value: Any) -> None:
        """Store a value in the buffer."""
        if session_id not in self.buffer:
            self.buffer[session_id] = {}
            
        self.buffer[session_id][intent] = BufferedAnswer(
            intent=intent,
            value=value,
            detected_at=datetime.now(),
            ttl_seconds=self.ttl_seconds
        )
        logger.info(f"Buffered {intent.value}={value} for session {session_id}")
        
    def get(self, session_id: str, intent: AllowedIntent) -> Optional[Any]:
        """Get a buffered value if it exists and hasn't expired."""
        if session_id not in self.buffer:
            return None
            
        if intent not in self.buffer[session_id]:
            return None
            
        buffered = self.buffer[session_id][intent]
        
        # Check TTL
        age = (datetime.now() - buffered.detected_at).seconds
        if age > buffered.ttl_seconds:
            del self.buffer[session_id][intent]
            return None
            
        return buffered.value
        
    def get_all(self, session_id: str) -> Dict[AllowedIntent, Any]:
        """Get all non-expired buffered values for a session."""
        if session_id not in self.buffer:
            return {}
            
        result = {}
        expired = []
        
        for intent, buffered in self.buffer[session_id].items():
            age = (datetime.now() - buffered.detected_at).seconds
            if age <= buffered.ttl_seconds:
                result[intent] = buffered.value
            else:
                expired.append(intent)
                
        # Clean up expired
        for intent in expired:
            del self.buffer[session_id][intent]
            
        return result
        
    def remove(self, session_id: str, intent: AllowedIntent) -> None:
        """Remove a value from the buffer (after it's been used)."""
        if session_id in self.buffer and intent in self.buffer[session_id]:
            del self.buffer[session_id][intent]
            
    def clear_session(self, session_id: str) -> None:
        """Clear all buffered values for a session."""
        if session_id in self.buffer:
            del self.buffer[session_id]


# ================================================================================
# PART 10: MAIN PROCESSOR
# ================================================================================

class ControlledIntelligenceProcessor:
    """
    Main processor that orchestrates all controlled intelligence components.
    
    PROCESSING PIPELINE:
    1. Normalize input (typos, formatting)
    2. Detect all intents
    3. Filter by current stage
    4. Check for ambiguity
    5. Apply safety guards
    6. Buffer non-matching intents
    7. Return processing result
    
    The processor NEVER decides stage progression.
    It only returns what it understood and whether it's valid for current stage.
    """
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.normalizer = SafeInputNormalizer()
        self.intent_detector = ControlledIntentDetector()
        self.ambiguity_detector = AmbiguityDetector()
        self.safety_guard = InputSafetyGuard()
        self.buffer = AnswerBuffer()
        
    def process(self, text: str, current_stage: str) -> ProcessingResult:
        """
        Process user input through the controlled intelligence pipeline.
        
        Args:
            text: Raw user input
            current_stage: Current stage from state machine
            
        Returns:
            ProcessingResult with all relevant information
        """
        result = ProcessingResult(accepted=False)
        
        if not text or not text.strip():
            result.rejection_reason = "Empty input"
            return result
            
        # Step 1: Safety checks
        safety_warning = self.safety_guard.check_out_of_context(text)
        if safety_warning:
            result.safety_warning = safety_warning
            
        premature_warning = self.safety_guard.check_premature_input(text, current_stage)
        if premature_warning:
            result.safety_warning = premature_warning
            
        # Step 2: Normalize input
        normalized = self.normalizer.normalize(text)
        result.normalized_input = normalized
        
        # Step 3: Detect all intents
        detected = self.intent_detector.detect_all(text)
        result.detected_intents = detected
        
        # Step 4: Get expected intent for stage
        expected_intent = STAGE_EXPECTED_INTENT.get(current_stage)
        result.stage_expected = expected_intent
        
        if not expected_intent:
            logger.warning(f"Unknown stage: {current_stage}")
            result.rejection_reason = f"Unknown stage: {current_stage}"
            return result
            
        # Step 5: Filter by stage
        accepted, buffered = self.intent_detector.filter_by_stage(detected, current_stage)
        result.buffered_intents = buffered
        
        # Step 6: Buffer non-matching intents
        for intent in buffered:
            if intent.intent != AllowedIntent.UNKNOWN:
                self.buffer.store(self.session_id, intent.intent, intent.value)
                
        # Step 7: Check for buffered value for current stage
        if not accepted:
            buffered_value = self.buffer.get(self.session_id, expected_intent)
            if buffered_value:
                accepted = DetectedIntent(
                    intent=expected_intent,
                    value=buffered_value,
                    raw_match=str(buffered_value)
                )
                self.buffer.remove(self.session_id, expected_intent)
                logger.info(f"Using buffered value for {expected_intent.value}: {buffered_value}")
                
        # Step 8: If we have an accepted intent, check for ambiguity
        if accepted:
            is_ambiguous, clarification = self.ambiguity_detector.check_ambiguity(
                text, accepted.intent
            )
            if is_ambiguous:
                result.clarification_needed = True
                result.clarification_prompt = clarification
                result.rejection_reason = "Ambiguous input requires clarification"
                return result
                
            # Check for re-answer
            re_answer_msg = self.safety_guard.check_re_answer(
                accepted.intent, accepted.value, self.session_id
            )
            if re_answer_msg:
                logger.info(re_answer_msg)
                
            result.accepted = True
            result.extracted_value = accepted.value
        else:
            result.rejection_reason = f"No {expected_intent.value} detected in input"
            
        return result
    
    def get_buffered(self, intent: AllowedIntent) -> Optional[Any]:
        """Get a buffered value."""
        return self.buffer.get(self.session_id, intent)
        
    def get_all_buffered(self) -> Dict[AllowedIntent, Any]:
        """Get all buffered values."""
        return self.buffer.get_all(self.session_id)
        
    def clear_buffer(self) -> None:
        """Clear the buffer."""
        self.buffer.clear_session(self.session_id)


# ================================================================================
# CONVENIENCE FUNCTIONS
# ================================================================================

def normalize_input(text: str) -> str:
    """Convenience function to normalize user input."""
    return SafeInputNormalizer().normalize(text)


def detect_intents(text: str) -> List[DetectedIntent]:
    """Convenience function to detect all intents in text."""
    return ControlledIntentDetector().detect_all(text)


def process_input(text: str, current_stage: str, session_id: str = "default") -> ProcessingResult:
    """
    Convenience function to process input through controlled intelligence.
    
    Args:
        text: User input
        current_stage: Current stage from state machine
        session_id: Session identifier
        
    Returns:
        ProcessingResult
    """
    processor = ControlledIntelligenceProcessor(session_id)
    return processor.process(text, current_stage)


def convert_amount(text: str) -> Optional[float]:
    """Convenience function to convert amount text to number."""
    return SafeInputNormalizer().convert_amount(text)
