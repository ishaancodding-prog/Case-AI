import os
import json
import io
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pypdf import PdfReader
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI App
app = FastAPI(
    title="NyayaMitra Citizen Judicial API",
    description="Backend service providing accessible, jargon-free court order explanations in Indian languages.",
    version="1.0.0"
)

# Enable CORS for frontend integration (React, HTML, Mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set specific domains in production (e.g., ["http://localhost:5173"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional Gemini Client Initialization
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_client = None

if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Google GenAI Client: {e}")

# ============================================================
# Pydantic Schemas
# ============================================================

class ActionStep(BaseModel):
    step_number: int
    action: str
    deadline: str
    caution: Optional[str] = None

class BigThreeTakeaways(BaseModel):
    jail_or_arrest_risk: str
    money_or_bond_required: str
    critical_deadline: str

class CaseSummaryResponse(BaseModel):
    case_headline: str
    court_and_parties: str
    verdict_status: str
    verdict_summary: str
    badge_color: str  # green, amber, red
    the_big_three: BigThreeTakeaways
    action_steps: List[ActionStep]
    common_pitfalls: List[str]
    voice_readout_summary: str

class ChatRequest(BaseModel):
    case_context: str = Field(..., description="The text of the court order or ruling")
    question: str = Field(..., description="The citizen's question")
    language: str = Field(default="Hindi", description="Target language (e.g., Hindi, English, Bengali, Tamil)")

class ChatResponse(BaseModel):
    answer: str
    language: str
    free_aid_helpline: str = "15100 (NALSA)"

class LegalAidCheckRequest(BaseModel):
    is_woman_or_child: bool = False
    is_sc_st: bool = False
    is_in_custody: bool = False
    annual_income_inr: float = 0.0

class LegalAidCheckResponse(BaseModel):
    is_eligible: bool
    reasons: List[str]
    how_to_apply: str
    helpline: str = "15100"

# ============================================================
# In-Memory Legal Glossary Data
# ============================================================

GLOSSARY_DATABASE = [
    {
        "term": "Anticipatory Bail (अग्रिम जमानत)",
        "simple_definition": "Protection against arrest before police can take you into custody (Sec 482 BNSS / 438 CrPC).",
        "example": "If granted, police must release you immediately on bond without detention."
    },
    {
        "term": "Ex-Parte (एकतरफा आदेश)",
        "simple_definition": "A ruling given by a court when one party fails to appear after notice.",
        "example": "If summons are ignored, the judge may deliver an ex-parte decree."
    },
    {
        "term": "Status Quo (यथास्थिति)",
        "simple_definition": "An order directing that property or ongoing conditions remain exactly as they are right now.",
        "example": "Neither party may construct, sell, or modify the property during this order."
    },
    {
        "term": "Surety / Zamin (जमानती)",
        "simple_definition": "A trusted person who signs guarantee papers taking responsibility for your appearance before court.",
        "example": "Requires submission of government identity and local property/residence proofs."
    },
    {
        "term": "Vakalatnama (वकालतनामा)",
        "simple_definition": "The formal written authorization letter empowering your advocate to plead on your behalf in court.",
        "example": "Signed before an advocate can formally file pleadings on your behalf."
    }
]

# ============================================================
# Helper Functions
# ============================================================

def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    """Extracts plain text from raw PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
        return "\n".join(extracted_text).strip()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process PDF document: {str(e)}"
        )

def generate_fallback_summary(raw_text: str, language: str) -> CaseSummaryResponse:
    """Rule-based fallback summary when AI API is unavailable or offline."""
    lower_text = raw_text.lower()
    
    is_bail = "bail" in lower_text or "438" in lower_text or "482" in lower_text
    is_rejected = "dismissed" in lower_text or "rejected" in lower_text
    
    if is_bail and not is_rejected:
        return CaseSummaryResponse(
            case_headline="अग्रिम जमानत स्वीकृत (Bail Granted) — गिरफ्तारी से सुरक्षा",
            court_and_parties="न्यायालय आदेश सारांश (Court Record Summary)",
            verdict_status="राहत मिली (RELIEF GRANTED)",
            verdict_summary="अदालत ने अग्रिम जमानत स्वीकार कर ली है। बांड जमा करने पर पुलिस हिरासत में नहीं ले सकती।",
            badge_color="green",
            the_big_three=BigThreeTakeaways(
                jail_or_arrest_risk="जेल का खतरा नहीं है। आपको अदालत से गिरफ्तारी पूर्व सुरक्षा मिली है।",
                money_or_bond_required="आदेश में निर्धारित निजी मुचलका (Personal Bond) एवं ज़मानती आवश्यक है।",
                critical_deadline="जांच अधिकारी (IO) के बुलाने पर जांच में शामिल होना अनिवार्य है।"
            ),
            action_steps=[
                ActionStep(
                    step_number=1,
                    action="अपने वकील के साथ जाकर निर्धारित राशि का बेल बांड और ज़मानती के कागजात जमा करें।",
                    deadline="अगले 2 से 3 दिनों के भीतर",
                    caution="बांड जमा करने में अनावश्यक देरी न करें।"
                ),
                ActionStep(
                    step_number=2,
                    action="जांच अधिकारी से मिलने पर अपनी उपस्थिति की लिखित पावती (receiving) अवश्य प्राप्त करें।",
                    deadline="पुलिस नोटिस प्राप्त होने पर",
                    caution="बिना अनुमति के शहर या देश से बाहर यात्रा न करें।"
                )
            ],
            common_pitfalls=[
                "शिकायतकर्ता पक्ष से प्रत्यक्ष या अप्रत्यक्ष संपर्क साधने का प्रयास न करें।",
                "अदालत की अनुमति के बिना यात्रा न करें और साक्ष्यों से छेड़छाड़ न करें।"
            ],
            voice_readout_summary="शुभ समाचार। अदालत ने आपकी अग्रिम जमानत मंजूर कर ली है। तय समय सीमा में बेल बांड जमा करें और जांच में पूरा सहयोग दें।"
        )

    # General default template
    return CaseSummaryResponse(
        case_headline="अदालती आदेश का सारांश (Court Order Parsed)",
        court_and_parties="विधिक प्रकरण विवरण (Legal Record)",
        verdict_status="आदेश पारित (DIRECTIONS ISSUED)",
        verdict_summary="अदालत ने मामले की सुनवाई कर दिशा-निर्देश जारी किए हैं। निर्धारित समय सीमा का अनुपालन करें।",
        badge_color="amber",
        the_big_three=BigThreeTakeaways(
            jail_or_arrest_risk="विस्तृत आदेशानुसार अपनी कानूनी स्थिति की समीक्षा अपने अधिवक्ता के साथ करें।",
            money_or_bond_required="आदेश में दर्शायी गई किसी भी राशि या हर्जाने की समय पर व्यवस्था करें।",
            critical_deadline="आदेश प्राप्ति से 30 से 60 दिनों के भीतर आवश्यक कानूनी कदम उठाएं।"
        ),
        action_steps=[
            ActionStep(
                step_number=1,
                action="न्यायालय की रजिस्ट्री से आदेश की प्रमाणित प्रति (Certified Copy) प्राप्त करें।",
                deadline="3 से 7 दिनों के भीतर",
                caution="अपील करने की मियाद सीमित होती है।"
            )
        ],
        common_pitfalls=["न्यायालय द्वारा नियत अगली पेशी या अनुपालन की अंतिम तिथि को न चूकें।"],
        voice_readout_summary="अदालत द्वारा दिशा-निर्देश जारी किए गए हैं। अपने वकील से संपर्क कर नियत समय सीमा में अनुपालन सुनिश्चित करें।"
    )

# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
def root():
    return {
        "app": "NyayaMitra API",
        "status": "online",
        "endpoints": [
            "/api/summarize (POST)",
            "/api/chat (POST)",
            "/api/glossary (GET)",
            "/api/legal-aid/eligibility (POST)"
        ]
    }

@app
