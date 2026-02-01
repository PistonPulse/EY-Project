"""
================================================================================
STRICT INPUT VALIDATOR FOR NBFC LOAN CHATBOT
================================================================================

THIS MODULE IS THE GATEKEEPER FOR ALL USER INPUT.

================================================================================
WHY STRICT INPUT VALIDATION IS REQUIRED IN BANKING
================================================================================

1. REGULATORY COMPLIANCE:
   - NBFC regulations require verifiable, auditable customer journeys
   - Each step must be documented and traceable
   - Skipping steps violates RBI guidelines

2. FRAUD PREVENTION:
   - Attackers cannot bypass KYC by entering random text
   - Identity verification MUST complete before data access
   - OTP cannot be skipped through prompt injection

3. DATA INTEGRITY:
   - Each field has a specific format (PAN, Aadhaar, mobile, OTP)
   - Invalid formats are rejected BEFORE processing
   - No "creative interpretation" of user input

4. PREDICTABLE BEHAVIOR:
   - Same input in same stage = same result EVERY TIME
   - No LLM randomness in flow decisions
   - Users get consistent experience

================================================================================
WHY LLMs ARE RESTRICTED TO WORDING ONLY
================================================================================

LLMs are EXCELLENT at:
- Natural language generation
- Explaining complex concepts simply
- Maintaining conversational tone

LLMs are TERRIBLE at:
- Deterministic logic (same input ≠ same output)
- Following strict rules (prompt injection attacks)
- Maintaining state (context window limitations)

THEREFORE:
- LLM generates the WORDS of the response
- Backend generates the FLOW of the conversation
- LLM NEVER decides what happens next

================================================================================
"""

from enum import Enum
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | INPUT_VALIDATOR | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('strict_input_validator')


# ================================================================================
# EXPECTED INPUT TYPES - WHAT EACH STAGE EXPECTS
# ================================================================================

class ExpectedInputType(Enum):
    """
    The ONLY valid input types the system can expect.
    Each stage expects EXACTLY ONE of these types.
    """
    ANY_TEXT = "ANY_TEXT"           # Greeting, general response
    LOAN_PURPOSE = "LOAN_PURPOSE"   # Text describing why user needs loan
    LOAN_AMOUNT = "LOAN_AMOUNT"     # Number (in lakhs, crores, or direct)
    CITY = "CITY"                   # City name
    EMPLOYMENT = "EMPLOYMENT"       # Salaried / Self-employed / Business
    FULL_NAME = "FULL_NAME"         # Person's name (2-4 words)
    MOBILE_NUMBER = "MOBILE_NUMBER" # 10-digit Indian mobile
    OTP_CODE = "OTP_CODE"           # 4-6 digit OTP
    PAN_NUMBER = "PAN_NUMBER"       # XXXXX0000X format
    AADHAAR_NUMBER = "AADHAAR_NUMBER"  # 12 digits
    CONFIRMATION = "CONFIRMATION"   # Yes/No/Proceed
    DOCUMENT = "DOCUMENT"           # File upload (handled separately)


# ================================================================================
# INPUT VALIDATION RESULTS
# ================================================================================

@dataclass
class ValidationResult:
    """
    Result of input validation.
    
    If valid=False, the system should RE-ASK the same question.
    The LLM can rephrase the re-ask, but the question remains the same.
    """
    valid: bool
    input_type: ExpectedInputType
    extracted_value: Optional[Any] = None
    error_message: Optional[str] = None
    should_reask: bool = False
    reask_hint: Optional[str] = None


# ================================================================================
# NORMALIZATION - CLEAN INPUT BEFORE VALIDATION
# ================================================================================

def normalize_input(raw_input: str) -> str:
    """
    Normalize user input BEFORE validation.
    
    This is CONTROLLED normalization:
    - Remove extra whitespace
    - Remove emojis
    - Remove special characters (except those needed for data)
    - Convert to consistent case where appropriate
    
    This is NOT "creative interpretation" - it's data cleaning.
    """
    if not raw_input:
        return ""
    
    # Remove emojis and special unicode
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', raw_input)
    
    # Normalize whitespace
    cleaned = ' '.join(cleaned.split())
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


# ================================================================================
# VALIDATORS FOR EACH INPUT TYPE
# ================================================================================

def validate_any_text(text: str) -> ValidationResult:
    """Validate any text input (for greetings, general responses)."""
    normalized = normalize_input(text)
    if len(normalized) > 0:
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.ANY_TEXT,
            extracted_value=normalized
        )
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.ANY_TEXT,
        error_message="Please enter a message.",
        should_reask=True
    )


def validate_loan_purpose(text: str) -> ValidationResult:
    """
    Validate loan purpose input.
    
    Valid purposes include:
    - Home renovation, home improvement
    - Wedding, marriage
    - Education, studies
    - Medical, health
    - Business, startup
    - Travel, vacation
    - Debt consolidation
    - Personal needs
    """
    normalized = normalize_input(text).lower()
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.LOAN_PURPOSE,
            error_message="Please tell us the purpose of your loan.",
            should_reask=True,
            reask_hint="home renovation, wedding, education, medical, business, etc."
        )
    
    # Common purposes keywords
    purpose_keywords = [
        'home', 'house', 'renovation', 'improvement', 'repair', 'construction',
        'wedding', 'marriage', 'shaadi',
        'education', 'study', 'college', 'university', 'school', 'course',
        'medical', 'health', 'hospital', 'treatment', 'surgery',
        'business', 'startup', 'shop', 'company',
        'travel', 'vacation', 'holiday', 'trip',
        'debt', 'consolidation', 'loan', 'emi',
        'personal', 'emergency', 'expense', 'need',
        'car', 'vehicle', 'bike', 'scooter',
        'appliance', 'furniture', 'electronics'
    ]
    
    # Check if any purpose keyword is present
    purpose_found = any(keyword in normalized for keyword in purpose_keywords)
    
    # Also accept if it's a reasonable length (3+ words describing something)
    word_count = len(normalized.split())
    
    if purpose_found or word_count >= 2:
        # Extract a clean purpose
        purpose = normalized.title()
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.LOAN_PURPOSE,
            extracted_value=purpose
        )
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.LOAN_PURPOSE,
        error_message="I couldn't understand the loan purpose.",
        should_reask=True,
        reask_hint="Please mention why you need the loan, like home renovation, wedding, education, etc."
    )


def validate_loan_amount(text: str) -> ValidationResult:
    """
    Validate loan amount input.
    
    Accepts:
    - "5 lakhs", "5L", "5 lacs"
    - "1 crore", "1 cr"
    - "500000" (direct number)
    - "Rs 5,00,000"
    
    MUST be a number. Text without numbers = invalid.
    """
    normalized = normalize_input(text).lower()
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.LOAN_AMOUNT,
            error_message="Please enter the loan amount.",
            should_reask=True,
            reask_hint="Enter amount like '5 lakhs', '10L', or '500000'"
        )
    
    # Pattern: X lakhs/lacs/L
    lakh_pattern = r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b'
    match = re.search(lakh_pattern, normalized)
    if match:
        amount = float(match.group(1)) * 100000
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.LOAN_AMOUNT,
            extracted_value=amount
        )
    
    # Pattern: X crore
    crore_pattern = r'(\d+(?:\.\d+)?)\s*(?:crore|crores|cr)\b'
    match = re.search(crore_pattern, normalized)
    if match:
        amount = float(match.group(1)) * 10000000
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.LOAN_AMOUNT,
            extracted_value=amount
        )
    
    # Pattern: Direct number (5+ digits or with commas)
    # Remove Rs, INR, rupees prefixes
    cleaned = re.sub(r'(?:rs\.?\s*|inr\s*|rupees?\s*)', '', normalized)
    number_pattern = r'(\d{1,3}(?:,\d{2})*(?:,\d{3})|\d+)'
    match = re.search(number_pattern, cleaned)
    if match:
        amount_str = match.group(1).replace(',', '')
        try:
            amount = float(amount_str)
            # Must be at least 10000 (10 thousand) to be a loan amount
            if amount >= 10000:
                return ValidationResult(
                    valid=True,
                    input_type=ExpectedInputType.LOAN_AMOUNT,
                    extracted_value=amount
                )
        except ValueError:
            pass
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.LOAN_AMOUNT,
        error_message="I couldn't understand the amount.",
        should_reask=True,
        reask_hint="Please enter the loan amount like '5 lakhs' or '500000'"
    )


def validate_city(text: str) -> ValidationResult:
    """
    Validate city name input.
    
    Must be a recognizable Indian city or a reasonable city name.
    """
    normalized = normalize_input(text)
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.CITY,
            error_message="Please enter your city.",
            should_reask=True
        )
    
    # List of major Indian cities (case-insensitive)
    indian_cities = {
        'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 'chennai',
        'kolkata', 'pune', 'ahmedabad', 'jaipur', 'lucknow', 'kanpur',
        'nagpur', 'indore', 'thane', 'bhopal', 'visakhapatnam', 'vizag',
        'patna', 'vadodara', 'ghaziabad', 'ludhiana', 'agra', 'nashik',
        'faridabad', 'meerut', 'rajkot', 'varanasi', 'srinagar', 'aurangabad',
        'dhanbad', 'amritsar', 'allahabad', 'prayagraj', 'ranchi', 'howrah',
        'coimbatore', 'jabalpur', 'gwalior', 'vijayawada', 'jodhpur', 'madurai',
        'raipur', 'kota', 'chandigarh', 'gurgaon', 'gurugram', 'noida',
        'guwahati', 'solapur', 'hubli', 'mysore', 'mysuru', 'tiruchirappalli',
        'bareilly', 'aligarh', 'tiruppur', 'moradabad', 'jalandhar', 'bhubaneswar',
        'salem', 'warangal', 'guntur', 'bhiwandi', 'saharanpur', 'gorakhpur',
        'bikaner', 'amravati', 'noida', 'jamshedpur', 'bhilai', 'cuttack',
        'firozabad', 'kochi', 'cochin', 'thiruvananthapuram', 'trivandrum',
        'navi mumbai', 'new delhi', 'greater noida'
    }
    
    # Check if input matches a known city
    city_lower = normalized.lower()
    
    # Direct match
    if city_lower in indian_cities:
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.CITY,
            extracted_value=normalized.title()
        )
    
    # Partial match (in case user types "I'm from Mumbai" or "Mumbai city")
    for city in indian_cities:
        if city in city_lower:
            return ValidationResult(
                valid=True,
                input_type=ExpectedInputType.CITY,
                extracted_value=city.title()
            )
    
    # Accept any single word that looks like a city name (capital letter, no numbers)
    words = normalized.split()
    if len(words) <= 3 and not any(c.isdigit() for c in normalized):
        # Looks like it could be a city name
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.CITY,
            extracted_value=normalized.title()
        )
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.CITY,
        error_message="Please enter a valid city name.",
        should_reask=True,
        reask_hint="For example: Mumbai, Delhi, Bangalore, etc."
    )


def validate_employment_type(text: str) -> ValidationResult:
    """
    Validate employment type input.
    
    Must be one of:
    - Salaried (employee of a company)
    - Self-employed (freelancer, consultant)
    - Business owner
    """
    normalized = normalize_input(text).lower()
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.EMPLOYMENT,
            error_message="Please tell us your employment type.",
            should_reask=True,
            reask_hint="Are you salaried, self-employed, or a business owner?"
        )
    
    # Salaried keywords
    if any(kw in normalized for kw in ['salaried', 'salary', 'job', 'employee', 'employed', 'work for', 'company']):
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.EMPLOYMENT,
            extracted_value="SALARIED"
        )
    
    # Self-employed keywords
    if any(kw in normalized for kw in ['self-employed', 'self employed', 'selfemployed', 'freelance', 'consultant', 'freelancer']):
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.EMPLOYMENT,
            extracted_value="SELF_EMPLOYED"
        )
    
    # Business owner keywords
    if any(kw in normalized for kw in ['business', 'owner', 'entrepreneur', 'startup', 'shop', 'store', 'company owner', 'proprietor']):
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.EMPLOYMENT,
            extracted_value="BUSINESS_OWNER"
        )
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.EMPLOYMENT,
        error_message="I couldn't understand your employment type.",
        should_reask=True,
        reask_hint="Please tell us if you're salaried, self-employed, or a business owner."
    )


def validate_full_name(text: str) -> ValidationResult:
    """
    Validate full name input.
    
    Must be 2-4 words, no numbers, no special characters.
    """
    normalized = normalize_input(text)
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.FULL_NAME,
            error_message="Please enter your full name.",
            should_reask=True
        )
    
    # Remove common prefixes
    prefixes_to_remove = ['my name is', 'i am', "i'm", 'this is', 'name is', 'naam hai', 'naam']
    for prefix in prefixes_to_remove:
        if normalized.lower().startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    
    # Check for numbers (names shouldn't have numbers)
    if any(c.isdigit() for c in normalized):
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.FULL_NAME,
            error_message="Name should not contain numbers.",
            should_reask=True,
            reask_hint="Please enter your full name (e.g., Rahul Sharma)"
        )
    
    # Split into words
    words = normalized.split()
    
    # Name should be 1-4 words
    if len(words) < 1 or len(words) > 5:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.FULL_NAME,
            error_message="Please enter a valid name.",
            should_reask=True,
            reask_hint="Enter your full name, like 'Rahul Sharma'"
        )
    
    # Words that are definitely not names
    not_names = {
        'hello', 'hi', 'hey', 'yes', 'no', 'ok', 'okay', 'loan', 'money',
        'help', 'please', 'thanks', 'thank', 'good', 'morning', 'evening'
    }
    
    if any(word.lower() in not_names for word in words):
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.FULL_NAME,
            error_message="That doesn't look like a name.",
            should_reask=True,
            reask_hint="Please share your full name for verification."
        )
    
    # Format name properly (capitalize each word)
    formatted_name = ' '.join(word.capitalize() for word in words)
    
    return ValidationResult(
        valid=True,
        input_type=ExpectedInputType.FULL_NAME,
        extracted_value=formatted_name
    )


def validate_mobile_number(text: str) -> ValidationResult:
    """
    Validate Indian mobile number.
    
    Must be exactly 10 digits starting with 6, 7, 8, or 9.
    """
    normalized = normalize_input(text)
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.MOBILE_NUMBER,
            error_message="Please enter your mobile number.",
            should_reask=True
        )
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', normalized)
    
    # Remove country code if present
    if digits_only.startswith('91') and len(digits_only) == 12:
        digits_only = digits_only[2:]
    elif digits_only.startswith('0') and len(digits_only) == 11:
        digits_only = digits_only[1:]
    
    # Check if it's a valid 10-digit Indian mobile number
    if len(digits_only) == 10 and digits_only[0] in '6789':
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.MOBILE_NUMBER,
            extracted_value=digits_only
        )
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.MOBILE_NUMBER,
        error_message="Please enter a valid 10-digit mobile number.",
        should_reask=True,
        reask_hint="Indian mobile numbers start with 6, 7, 8, or 9"
    )


def validate_otp_code(text: str) -> ValidationResult:
    """
    Validate OTP code.
    
    Must be 4-6 digits only.
    """
    normalized = normalize_input(text)
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.OTP_CODE,
            error_message="Please enter the OTP.",
            should_reask=True
        )
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', normalized)
    
    # OTP is 4-6 digits
    if 4 <= len(digits_only) <= 6:
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.OTP_CODE,
            extracted_value=digits_only
        )
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.OTP_CODE,
        error_message="OTP must be 4-6 digits.",
        should_reask=True,
        reask_hint="Please enter the OTP sent to your mobile."
    )


def validate_pan_number(text: str) -> ValidationResult:
    """
    Validate PAN number.
    
    Format: XXXXX0000X (5 letters, 4 digits, 1 letter)
    """
    normalized = normalize_input(text).upper()
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.PAN_NUMBER,
            error_message="Please enter your PAN number.",
            should_reask=True
        )
    
    # Remove common prefixes
    prefixes = ['my pan is', 'pan is', 'pan:', 'pan number is', 'pan number:']
    for prefix in prefixes:
        if normalized.lower().startswith(prefix):
            normalized = normalized[len(prefix):].strip().upper()
    
    # PAN pattern: XXXXX0000X
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
    
    # Try to find PAN in the text
    pan_match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]', normalized)
    
    if pan_match:
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.PAN_NUMBER,
            extracted_value=pan_match.group()
        )
    
    # Check if the entire input matches
    if re.match(pan_pattern, normalized):
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.PAN_NUMBER,
            extracted_value=normalized
        )
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.PAN_NUMBER,
        error_message="Please enter a valid PAN number.",
        should_reask=True,
        reask_hint="PAN format: ABCDE1234F (5 letters, 4 digits, 1 letter)"
    )


def validate_aadhaar_number(text: str) -> ValidationResult:
    """
    Validate Aadhaar number.
    
    Must be exactly 12 digits, not starting with 0 or 1.
    """
    normalized = normalize_input(text)
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.AADHAAR_NUMBER,
            error_message="Please enter your Aadhaar number.",
            should_reask=True
        )
    
    # Remove all non-digit characters (spaces, dashes)
    digits_only = re.sub(r'\D', '', normalized)
    
    # Aadhaar is 12 digits, not starting with 0 or 1
    if len(digits_only) == 12 and digits_only[0] not in '01':
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.AADHAAR_NUMBER,
            extracted_value=digits_only
        )
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.AADHAAR_NUMBER,
        error_message="Please enter a valid 12-digit Aadhaar number.",
        should_reask=True,
        reask_hint="Aadhaar is 12 digits, not starting with 0 or 1"
    )


def validate_confirmation(text: str) -> ValidationResult:
    """
    Validate yes/no confirmation.
    
    Accepts various forms of yes/no/proceed/cancel.
    """
    normalized = normalize_input(text).lower()
    
    if not normalized:
        return ValidationResult(
            valid=False,
            input_type=ExpectedInputType.CONFIRMATION,
            error_message="Please confirm with yes or no.",
            should_reask=True
        )
    
    # Affirmative responses
    affirmatives = ['yes', 'yep', 'yeah', 'ya', 'yup', 'ok', 'okay', 'sure', 
                    'proceed', 'continue', 'confirm', 'agree', 'haan', 'ji', 
                    'correct', 'right', 'accepted']
    
    # Negative responses
    negatives = ['no', 'nope', 'nah', 'cancel', 'stop', 'wrong', 'incorrect',
                 'nahi', 'galat', 'decline', 'reject']
    
    if any(aff in normalized for aff in affirmatives):
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.CONFIRMATION,
            extracted_value="YES"
        )
    
    if any(neg in normalized for neg in negatives):
        return ValidationResult(
            valid=True,
            input_type=ExpectedInputType.CONFIRMATION,
            extracted_value="NO"
        )
    
    return ValidationResult(
        valid=False,
        input_type=ExpectedInputType.CONFIRMATION,
        error_message="I couldn't understand. Please say yes or no.",
        should_reask=True
    )


# ================================================================================
# MAIN VALIDATION FUNCTION
# ================================================================================

def validate_input(
    raw_input: str,
    expected_type: ExpectedInputType
) -> ValidationResult:
    """
    MAIN VALIDATION FUNCTION - The single point of input validation.
    
    Args:
        raw_input: User's raw input
        expected_type: What type of input the current stage expects
    
    Returns:
        ValidationResult with:
        - valid: Whether input matches expected type
        - extracted_value: The cleaned/extracted value
        - should_reask: Whether to re-ask the same question
        - error_message: What to tell the user
    
    CRITICAL:
    - If input doesn't match expected type, should_reask=True
    - The system will NOT advance stage on invalid input
    - The LLM will rephrase the re-ask, but question stays the same
    """
    logger.info(f"Validating input for expected type: {expected_type.value}")
    logger.info(f"Raw input: {raw_input[:50]}...")
    
    validators = {
        ExpectedInputType.ANY_TEXT: validate_any_text,
        ExpectedInputType.LOAN_PURPOSE: validate_loan_purpose,
        ExpectedInputType.LOAN_AMOUNT: validate_loan_amount,
        ExpectedInputType.CITY: validate_city,
        ExpectedInputType.EMPLOYMENT: validate_employment_type,
        ExpectedInputType.FULL_NAME: validate_full_name,
        ExpectedInputType.MOBILE_NUMBER: validate_mobile_number,
        ExpectedInputType.OTP_CODE: validate_otp_code,
        ExpectedInputType.PAN_NUMBER: validate_pan_number,
        ExpectedInputType.AADHAAR_NUMBER: validate_aadhaar_number,
        ExpectedInputType.CONFIRMATION: validate_confirmation,
    }
    
    validator = validators.get(expected_type, validate_any_text)
    result = validator(raw_input)
    
    logger.info(f"Validation result: valid={result.valid}, extracted={result.extracted_value}")
    
    return result


# ================================================================================
# STAGE TO EXPECTED INPUT MAPPING
# ================================================================================

# Maps each (stage, step) combination to expected input type
STAGE_EXPECTED_INPUT = {
    # GREETING - expects any text (greeting response)
    ("GREETING", "GREETING_WELCOME"): ExpectedInputType.ANY_TEXT,
    
    # NEEDS_DISCOVERY - purpose then amount
    ("NEEDS_DISCOVERY", "NEEDS_ASK_PURPOSE"): ExpectedInputType.LOAN_PURPOSE,
    ("NEEDS_DISCOVERY", "NEEDS_ASK_AMOUNT"): ExpectedInputType.LOAN_AMOUNT,
    
    # BASIC_ELIGIBILITY - city then employment
    ("BASIC_ELIGIBILITY", "ELIG_ASK_CITY"): ExpectedInputType.CITY,
    ("BASIC_ELIGIBILITY", "ELIG_ASK_EMPLOYMENT"): ExpectedInputType.EMPLOYMENT,
    
    # KYC_COLLECTION - name then mobile
    ("KYC_COLLECTION", "KYC_ASK_NAME"): ExpectedInputType.FULL_NAME,
    ("KYC_COLLECTION", "KYC_ASK_MOBILE"): ExpectedInputType.MOBILE_NUMBER,
    
    # OTP_VERIFICATION - OTP code
    ("OTP_VERIFICATION", "OTP_ASK_CODE"): ExpectedInputType.OTP_CODE,
    
    # KYC_VERIFICATION - PAN then Aadhaar
    ("KYC_VERIFICATION", "KYC_ASK_PAN"): ExpectedInputType.PAN_NUMBER,
    ("KYC_VERIFICATION", "KYC_ASK_AADHAAR"): ExpectedInputType.AADHAAR_NUMBER,
    
    # OFFER_DISCOVERY - confirmation
    ("OFFER_DISCOVERY", "OFFER_CONFIRM"): ExpectedInputType.CONFIRMATION,
    
    # INCOME_DOC_UPLOAD - document (handled separately)
    ("INCOME_DOC_UPLOAD", "UPLOAD_DOC"): ExpectedInputType.DOCUMENT,
    
    # UNDERWRITING - no input expected (processing)
    ("UNDERWRITING", "PROCESSING"): ExpectedInputType.ANY_TEXT,
    
    # Terminal states - no input expected
    ("SANCTION", "COMPLETE"): ExpectedInputType.ANY_TEXT,
    ("REJECTION", "COMPLETE"): ExpectedInputType.ANY_TEXT,
}


def get_expected_input_type(stage: str, step: str) -> ExpectedInputType:
    """
    Get the expected input type for a given stage and step.
    
    Args:
        stage: Current stage (e.g., "NEEDS_DISCOVERY")
        step: Current step within stage (e.g., "NEEDS_ASK_PURPOSE")
    
    Returns:
        ExpectedInputType for validation
    """
    key = (stage, step)
    return STAGE_EXPECTED_INPUT.get(key, ExpectedInputType.ANY_TEXT)
