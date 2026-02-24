import os
import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Constants for Mock Fallback
MOCK_USER_DATA = {
    "tanish": {"name": "Tanish Gupta", "pan": "ABCDE1234F"},
    "amit": {"name": "Amit Verma", "pan": "GHIJK5678M"}
}


def analyze_document_with_gemini_vision(file_bytes: bytes, mime_type: str = "application/pdf") -> Optional[Dict[str, str]]:
    """
    PRIMARY OCR Worker: Gemini 2.0 Flash Vision API
    Uses a dedicated OCR API key to avoid exhausting the main chat keys.
    Sends the raw document bytes directly to Gemini's multimodal endpoint.
    Returns parsed dict with 'name' and 'pan', or None on failure.
    """
    import requests

    ocr_api_key = os.getenv("GEMINI_OCR_API_KEY", "")
    if not ocr_api_key:
        logger.warning("[OCR] GEMINI_OCR_API_KEY not set. Skipping Gemini Vision.")
        raise ValueError("GEMINI_OCR_API_KEY not configured.")

    import base64
    encoded_data = base64.b64encode(file_bytes).decode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={ocr_api_key}"
    headers = {"Content-Type": "application/json"}

    prompt = """Analyze this salary slip or financial document carefully.
You must return a raw JSON object with no markdown formatting or backticks.

Extract:
1. "extracted_name": String. The exact name of the employee or account holder found on the document.
2. "extracted_pan": String. If you can clearly see a PAN (Permanent Account Number) on the document, extract it. PAN format is 5 uppercase letters + 4 digits + 1 uppercase letter (e.g., ABCDE1234F). If not found, return "".
3. "monthly_income": Number. The net monthly take-home salary. If not found, return 0.

Example output:
{"extracted_name": "Tanish Gupta", "extracted_pan": "ABCDE1234F", "monthly_income": 200000}"""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": encoded_data}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 300,
        }
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                content_parts = candidates[0].get("content", {}).get("parts", [])
                if content_parts:
                    result_text = content_parts[0].get("text", "").strip()

                    # Clean markdown backticks if Gemini adds them
                    if result_text.startswith("```json"):
                        result_text = result_text[7:-3].strip()
                    elif result_text.startswith("```"):
                        result_text = result_text[3:-3].strip()

                    parsed = json.loads(result_text)
                    name = parsed.get("extracted_name", "Unknown")
                    pan = parsed.get("extracted_pan", "")

                    if name or pan:
                        logger.info(f"[OCR] Gemini Vision extracted -> Name: {name}, PAN: {pan}")
                        return {"name": name, "pan": pan.upper() if pan else ""}

        elif resp.status_code == 429:
            logger.warning("[OCR] Gemini Vision rate limited (429).")
            raise Exception("Gemini Vision rate limited")
        else:
            logger.error(f"[OCR] Gemini Vision error: {resp.status_code} - {resp.text[:200]}")
            raise Exception(f"Gemini Vision HTTP {resp.status_code}")

    except json.JSONDecodeError as e:
        logger.error(f"[OCR] Gemini Vision returned non-JSON: {e}")
        raise e
    except requests.exceptions.RequestException as e:
        logger.error(f"[OCR] Gemini Vision network error: {e}")
        raise e

    return None


def analyze_document_with_aws_textract(file_bytes: bytes) -> Optional[str]:
    """
    Fallback OCR Worker: Amazon Textract
    Requires AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
    """
    import boto3

    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "ap-south-1")

    if not aws_access_key or not aws_secret_key:
        logger.warning("[OCR] AWS Textract credentials missing.")
        raise ValueError("AWS credentials not configured.")

    try:
        client = boto3.client(
            'textract',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )

        response = client.detect_document_text(Document={'Bytes': file_bytes})

        extracted_text = ""
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                extracted_text += item["Text"] + "\n"

        logger.info("[OCR] AWS Textract successfully extracted text.")
        return extracted_text

    except Exception as e:
        logger.error(f"[OCR] AWS Textract failed: {str(e)}")
        raise e


def extract_pan_and_name_from_text(raw_text: str) -> Dict[str, str]:
    """
    Parses raw OCR text to find a PAN number and a likely Name.
    Used for AWS Textract raw text output.
    """
    result = {"name": "Unknown User", "pan": ""}

    if not raw_text:
        return result

    # Extract PAN (Format: 5 Letters, 4 Digits, 1 Letter)
    pan_match = re.search(r'([A-Z]{5}\d{4}[A-Z])', raw_text.upper())
    if pan_match:
        result["pan"] = pan_match.group(1)

    # Basic Name extraction heuristic
    lines = raw_text.split('\n')
    for line in lines:
        if "name" in line.lower() and len(line) > 5:
            clean_name = re.sub(r'(?i)name[:\s-]*', '', line).strip()
            if clean_name:
                result["name"] = clean_name
                break

    return result


def process_kyc_document(file_bytes: bytes, filename: str, mime_type: str = "application/pdf") -> Dict[str, str]:
    """
    Orchestrates the intelligent OCR pipeline:
      1. Gemini Vision API (primary — uses dedicated OCR key)
      2. AWS Textract (fallback)
      3. Mock Filename Extraction (graceful demo degradation)
    """

    # 1. PRIMARY: Gemini Vision API
    try:
        result = analyze_document_with_gemini_vision(file_bytes, mime_type)
        if result and (result.get("pan") or result.get("name", "Unknown") != "Unknown"):
            logger.info(f"[OCR PIPELINE] Gemini Vision extracted: {result}")
            return result
    except Exception as e:
        logger.warning(f"Primary OCR (Gemini Vision) failed: {e}")

    # 2. FALLBACK: AWS Textract
    try:
        raw_text = analyze_document_with_aws_textract(file_bytes)
        if raw_text:
            extracted_data = extract_pan_and_name_from_text(raw_text)
            if extracted_data.get("pan"):
                logger.info(f"[OCR PIPELINE] AWS Textract extracted: {extracted_data}")
                return extracted_data
    except Exception as aws_e:
        logger.warning(f"Fallback OCR (AWS Textract) failed: {aws_e}")

    # 3. GRACEFUL DEMO DEGRADATION (MOCK OCR)
    logger.info("[OCR PIPELINE] Live APIs bypassed. Using Mock Filename Simulation.")

    lower_filename = filename.lower()
    for key, data in MOCK_USER_DATA.items():
        if key in lower_filename:
            return {"name": data["name"], "pan": data["pan"]}

    return {"name": "Unknown User", "pan": "ZZZZZ9999Z"}
