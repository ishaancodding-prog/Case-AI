import json
import os
import tempfile
from io import BytesIO
import PyPDF2
from gtts import gTTS
import streamlit as st
from google import genai
from google.genai import types

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="NyayaMitra - Citizen Legal Summarizer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-title { font-size: 2.3rem; font-weight: 800; color: #1e3a8a; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #475569; margin-bottom: 1.5rem; }
    .emergency-banner {
        background-color: #fef2f2; border: 1px solid #fecaca;
        padding: 12px 18px; border-radius: 8px; margin-bottom: 20px;
        color: #991b1b; font-size: 0.95rem; font-weight: 600;
    }
    .status-card {
        padding: 16px; border-radius: 10px; margin-bottom: 12px;
        background-color: #f8fafc; border-left: 5px solid #2563eb;
    }
    .win-badge { background-color: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 6px; font-weight: 700; }
    .action-step {
        background-color: #fff; border: 1px solid #e2e8f0;
        padding: 12px; border-radius: 8px; margin-bottom: 8px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Multi-Language Localization Dictionary (8 Indian Languages)
# ---------------------------------------------------------
LANG_CONFIG = {
    "English": {"code": "en", "native": "English", "voice_code": "en"},
    "हिन्दी (Hindi)": {"code": "hi", "native": "हिन्दी", "voice_code": "hi"},
    "বাংলা (Bengali)": {"code": "bn", "native": "বাংলা", "voice_code": "bn"},
    "தமிழ் (Tamil)": {"code": "ta", "native": "தமிழ்", "voice_code": "ta"},
    "తెలుగు (Telugu)": {"code": "te", "native": "తెలుగు", "voice_code": "te"},
    "मराठी (Marathi)": {"code": "mr", "native": "मराठी", "voice_code": "mr"},
    "ગુજરાતી (Gujarati)": {
        "code": "gu",
        "native": "ગુજરાતી",
        "voice_code": "gu",
    },
    "ಕನ್ನಡ (Kannada)": {"code": "kn", "native": "ಕನ್ನಡ", "voice_code": "kn"},
}

TRANSLATIONS = {
    "English": {
        "title": "NyayaMitra (न्यायमित्र)",
        "tagline": "AI Judicial Companion for Citizens — Court Orders Explained in Plain Language",
        "helpline": "🚨 Free Government Legal Aid: Dial NALSA 15100 | Tele-Law: Dial 14416",
        "upload_label": "Upload Court Order / Judgement (PDF or TXT)",
        "paste_label": "Or paste court order text here:",
        "analyze_btn": "Explain in My Language",
        "sample_btn": "Load Sample Order (Anticipatory Bail)",
        "audio_title": "🔊 Listen to Summary (Audio)",
        "q1": "1. Did I Win or Lose? (Case Status)",
        "q2": "2. Do I have to go to Jail or Court?",
        "q3": "3. Immediate Deadlines & Financial Liabilities",
        "q4": "4. Step-by-Step Next Actions",
        "chat_title": "💬 Ask Questions About This Order",
        "chat_placeholder": "E.g., What happens if I miss the court date?",
        "jargon_title": "📖 Legal Jargon Buster",
        "nalsa_title": "⚖️ Do You Qualify for Free Legal Aid (NALSA)?",
    },
    "हिन्दी (Hindi)": {
        "title": "न्यायमित्र (NyayaMitra)",
        "tagline": "नागरिकों के लिए AI कानूनी सहायक — अदालती आदेश अपनी सरल भाषा में समझें",
        "helpline": "🚨 मुफ्त सरकारी कानूनी सहायता: नालसा (NALSA) 15100 डायल करें | टेली-लॉ: 14416",
        "upload_label": "अदालती आदेश / फैसला अपलोड करें (PDF या TXT)",
        "paste_label": "या अदालत के आदेश का विवरण यहाँ पेस्ट करें:",
        "analyze_btn": "मेरी भाषा में सरल अर्थ समझाएं",
        "sample_btn": "नमूना आदेश लोड करें (अग्रिम जमानत)",
        "audio_title": "🔊 ऑडियो सारांश सुनें (आवाज़ में)",
        "q1": "1. क्या मैं जीता या हारा? (आदेश का नतीजा)",
        "q2": "2. क्या मुझे जेल जाना होगा या अदालत में पेश होना है?",
        "q3": "3. पैसों का भुगतान और समय-सीमा (Deadlines)",
        "q4": "4. अब मुझे आगे क्या करना होगा? (कदम-दर-कदम)",
        "chat_title": "💬 इस अदालती आदेश पर सवाल पूछें",
        "chat_placeholder": "जैसे: यदि मैं तारीख पर न पहुँच पाऊं तो क्या होगा?",
        "jargon_title": "📖 कानूनी शब्दों का आसान मतलब",
        "nalsa_title": "⚖️ क्या आप मुफ्त सरकारी वकील (NALSA) के हकदार हैं?",
    },
    "বাংলা (Bengali)": {
        "title": "ন্যায়মিত্র (NyayaMitra)",
        "tagline": "নাগরিকদের জন্য AI আইনি সহায়ক — আদালতের আদেশ সহজ ভাষায় বুঝুন",
        "helpline": "🚨 বিনামূল্যে সরকারি আইনি সহায়তা: NALSA 15100 | টেলি-ল: 14416",
        "upload_label": "আদালতের আদেশ আপলোড করুন (PDF বা TXT)",
        "paste_label": "অথবা আদালতের আদেশের পাঠ্য এখানে পেস্ট করুন:",
        "analyze_btn": "আমার ভাষায় সহজভাবে ব্যাখ্যা করুন",
        "sample_btn": "নমুনা কেস লোড করুন (অগ্রিম জামিন)",
        "audio_title": "🔊 অডিও সারাংশ শুনুন",
        "q1": "১. মামলার ফলাফল কী? (আমি কি জিতেছি?)",
        "q2": "২. আমাকে কি জেলে বা আদালতে যেতে হবে?",
        "q3": "৩. আর্থিক জরিমানা ও সময়সীমা",
        "q4": "৪. আপনার পরবর্তী পদক্ষেপের তালিকা",
        "chat_title": "💬 এই আদেশ সম্পর্কিত প্রশ্ন জিজ্ঞাসা করুন",
        "chat_placeholder": "যেমন: আমি কি এখনই ভ্রমণ করতে পারব?",
        "jargon_title": "📖 আইনি শব্দের সরল ব্যাখ্যা",
        "nalsa_title": "⚖️ আপনি কি বিনামূল্যে সরকারি আইনি সহায়তার যোগ্য?",
    },
    "தமிழ் (Tamil)": {
        "title": "நியாயமித்ரா (NyayaMitra)",
        "tagline": "மக்களுக்கான AI சட்டத் துணைவன் — நீதிமன்ற உத்தரவுகளை எளிய மொழியில் புரிந்து கொள்ளுங்கள்",
        "helpline": "🚨 இலவச அரசு சட்ட உதவி: NALSA 15100 | டெலி-லா: 14416",
        "upload_label": "நீதிமன்ற உத்தரவை பதிவேற்றவும் (PDF அல்லது TXT)",
        "paste_label": "அல்லது நீதிமன்ற உத்தரவை இங்கே ஒட்டவும்:",
        "analyze_btn": "என் மொழியில் விளக்குங்கள்",
        "sample_btn": "மாதிரி உத்தரவை ஏற்றவும் (முன்ஜாமீன்)",
        "audio_title": "🔊 ஆடியோ சுருக்கத்தைக் கேளுங்கள்",
        "q1": "1. தீர்ப்பு என்ன? (வெற்றியா அல்லது தோல்வியா?)",
        "q2": "2. நான் சிறை செல்ல வேண்டுமா அல்லது ஆஜராக வேண்டுமா?",
        "q3": "3. செலுத்த வேண்டிய பணம் மற்றும் காலக்கெடு",
        "q4": "4. அடுத்த கட்ட நடவடிக்கைகள்",
        "chat_title": "💬 இந்த உத்தரவு பற்றி கேள்வி கேளுங்கள்",
        "chat_placeholder": "உதாரணமாக: அடுத்த நீதிமன்ற தேதி என்ன?",
        "jargon_title": "📖 சட்டச் சொற்களின் எளிய விளக்கம்",
        "nalsa_title": "⚖️ இலவச அரசு சட்ட உதவிக்கு நீங்கள் தகுதியானவரா?",
    },
    "తెలుగు (Telugu)": {
        "title": "న్యాయమిత్ర (NyayaMitra)",
        "tagline": "ప్రజల కోసం AI న్యాయ సహచరుడు — కోర్టు తీర్పులను సరళమైన భాషలో తెలుసుకోండి",
        "helpline": "🚨 ఉచిత ప్రభుత్వ న్యాయ సహాయం: NALSA 15100 | టెలి-లా: 14416",
        "upload_label": "కోర్టు ఆర్డర్ అప్‌లోడ్ చేయండి (PDF లేదా TXT)",
        "paste_label": "లేదా కోర్టు ఆర్డర్ టెక్స్ట్‌ని ఇక్కడ పేస్ట్ చేయండి:",
        "analyze_btn": "నా భాషలో వివరించండి",
        "sample_btn": "నమూనా ఆర్డర్ లోడ్ చేయండి (ముందస్తు బెయిల్)",
        "audio_title": "🔊 ఆడియో సారాంశాన్ని వినండి",
        "q1": "1. కేసు ఫలితం ఏమిటి? (నేను గెలిచానా?)",
        "q2": "2. నేను జైలుకు వెళ్లాలా లేదా కోర్టుకు హాజరు కావాలా?",
        "q3": "3. గడువులు మరియు చెల్లించాల్సిన రుసుములు",
        "q4": "4. తదుపరి చర్యల జాబితా",
        "chat_title": "💬 ఈ ఆర్డర్ పై ప్రశ్నలు అడగండి",
        "chat_placeholder": "ఉదాహరణకు: నేను ఎప్పుడు హాజరు కావాలి?",
        "jargon_title": "📖 న్యాయ పదాల సరళ నిఘంటువు",
        "nalsa_title": "⚖️ మీరు ఉచిత న్యాయ సహాయానికి అర్హులా?",
    },
    "मराठी (Marathi)": {
        "title": "न्यायमित्र (NyayaMitra)",
        "tagline": "नागरिकांसाठी AI कायदेशीर सहाय्यक — न्यायालयाचा निकाल सोप्या भाषेत समजून घ्या",
        "helpline": "🚨 मोफत सरकारी कायदेशीर सल्ला: NALSA 15100 | टेलि-लॉ: 14416",
        "upload_label": "न्यायालयाचा आदेश अपलोड करा (PDF किंवा TXT)",
        "paste_label": "किंवा येथे न्यायालयाचा मजकूर पेस्ट करा:",
        "analyze_btn": "माझ्या भाषेत सोप्या शब्दात सांगा",
        "sample_btn": "नमुना आदेश लोड करा (अटकपूर्व जामीन)",
        "audio_title": "🔊 ऑडिओ सारांश ऐका",
        "q1": "१. निकालाचा अर्थ काय? (विजय की पराभव?)",
        "q2": "२. मला तुरुंगात जावे लागेल की कोर्टात हजर राहावे लागेल?",
        "q3": "३. पैशांची देणी आणि मुदत (Deadlines)",
        "q4": "४. पुढे काय करावे लागेल? (कृती योजना)",
        "chat_title": "💬 या निकालाविषयी प्रश्न विचारा",
        "chat_placeholder": "उदा. पासपोर्ट जमा करावा लागेल का?",
        "jargon_title": "📖 कठीण कायदेशीर शब्दांचे सोपे अर्थ",
        "nalsa_title": "⚖️ मोफत सरकारी वकिलासाठी तुम्ही पात्र आहात का?",
    },
    "ગુજરાતી (Gujarati)": {
        "title": "ન્યાયમિત્ર (NyayaMitra)",
        "tagline": "નાગરિકો માટે AI કાનૂની સહાયક — કોર્ટના આદેશો સરળ ભાષામાં સમજો",
        "helpline": "🚨 મફત સરકારી કાનૂની સહાય: NALSA 15100 | ટેલિ-લો: 14416",
        "upload_label": "કોર્ટ ઓર્ડર અપલોડ કરો (PDF અથવા TXT)",
        "paste_label": "અથવા કોર્ટ ઓર્ડર અહીં પેસ્ટ કરો:",
        "analyze_btn": "મારી ભાષામાં સરળ અર્થ સમજાવો",
        "sample_btn": "નમૂનાનો ઓર્ડર લોડ કરો (આગોતરા જામીન)",
        "audio_title": "🔊 ઓડિયો સારાંશ સાંભળો",
        "q1": "૧. ચુકાદો શું છે? (જીત કે હાર?)",
        "q2": "૨. શું જેલ જવું પડશે કે કોર્ટમાં હાજર રહેવું પડશે?",
        "q3": "૩. નાણાકીય જવાબદારી અને સમયમર્યાદા",
        "q4": "૪. હવે પછી શું પગલાં લેવા?",
        "chat_title": "💬 આ ઓર્ડર વિશે પ્રશ્ન પૂછો",
        "chat_placeholder": "ઉદાહરણ તરીકે: મારી આગામી તારીખ ક્યારે છે?",
        "jargon_title": "📖 કાનૂની શબ્દોનો સરળ અર્થ",
        "nalsa_title": "⚖️ શું તમે મફત કાનૂની સહાય મેળવવા હકદાર છો?",
    },
    "ಕನ್ನಡ (Kannada)": {
        "title": "ನ್ಯಾಯಮಿತ್ರ (NyayaMitra)",
        "tagline": "ಜನಸಾಮಾನ್ಯರಿಗಾಗಿ AI ಕಾನೂನು ಮಾರ್ಗದರ್ಶಿ — ನ್ಯಾಯಾಲಯದ ಆದೇಶಗಳನ್ನು ಸರಳವಾಗಿ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ",
        "helpline": "🚨 ಉಚಿತ ಸರ್ಕಾರಿ ಕಾನೂನು ನೆರವು: NALSA 15100 | ಟೆಲಿ-ಲಾ: 14416",
        "upload_label": "ನ್ಯಾಯಾಲಯದ ಆದೇಶವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ (PDF ಅಥವಾ TXT)",
        "paste_label": "ಅಥವಾ ಆದೇಶದ ಪಠ್ಯವನ್ನು ಇಲ್ಲಿ ನಮೂದಿಸಿ:",
        "analyze_btn": "ನನ್ನ ಭಾಷೆಯಲ್ಲಿ ಸರಳವಾಗಿ ವಿವರಿಸಿ",
        "sample_btn": "ಮಾದರಿ ಆದೇಶವನ್ನು ಲೋಡ್ ಮಾಡಿ (ನಿರೀಕ್ಷಣಾ ಜಾಮೀನು)",
        "audio_title": "🔊 ಆಡಿಯೋ ಸಾರಾಂಶವನ್ನು ಆಲಿಸಿ",
        "q1": "೧. ತೀರ್ಪಿನ ಸಾರಾಂಶ (ಗೆಲುವೋ ಅಥವಾ ಸೋಲೋ?)",
        "q2": "೨. ನಾನು ಜೈಲಿಗೆ ಹೋಗಬೇಕೆ ಅಥವಾ ನ್ಯಾಯಾಲಯಕ್ಕೆ ಹಾಜರಾಗಬೇಕೆ?",
        "q3": "೩. ಪಾವತಿಸಬೇಕಾದ ಹಣ ಮತ್ತು ಗಡುವುಗಳು",
        "q4": "೪. ಮುಂದಿನ ಹಂತಗಳ ಪಟ್ಟಿ",
        "chat_title": "💬 ಈ ಆದೇಶದ ಬಗ್ಗೆ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ",
        "chat_placeholder": "ಉದಾಹರಣೆಗೆ: ನಾನು ಯಾವಾಗ ಹಾಜರಾಗಬೇಕು?",
        "jargon_title": "📖 ಕಾನೂನು ಪದಗಳ ಸರಳ ಅರ್ಥಕೋಶ",
        "nalsa_title": "⚖️ ನೀವು ಉಚಿತ ಕಾನೂನು ನೆರವಿಗೆ ಅರ್ಹರೇ?",
    },
}

SAMPLE_CASE = """IN THE HIGH COURT OF DELHI AT NEW DELHI
BAIL APPLN. NO. 4021/2025
IN THE MATTER OF:
Ramesh Sharma ... Petitioner
Versus
State (NCT of Delhi) ... Respondent

ORDER
1. This is an application seeking anticipatory bail under Section 438 of the Code of Criminal Procedure, 1973 (now Section 482 of BNSS, 2023) in connection with FIR No. 204/2025 registered at P.S. Malviya Nagar for offenses punishable under Sections 498A, 406 and 34 of the Indian Penal Code (IPC).
2. The learned counsel for the petitioner submits that the petitioner has been falsely implicated due to matrimonial discord. The petitioner is a senior teacher with clean antecedents and undertakes to cooperate fully with the investigation.
3. Learned APP for the State opposes the application on grounds of pending recovery of stridhan.
4. Having considered the submissions and perused the records, custodial interrogation of the petitioner is not warranted at this stage. Accordingly, the petitioner is granted anticipatory bail subject to the following conditions:
(a) In the event of arrest, petitioner shall be released on bail on furnishing a personal bond of Rs. 30,000/- with one surety of like amount to the satisfaction of the Arresting Officer/IO.
(b) Petitioner shall join investigation as and when called by the Investigating Officer upon 48 hours prior written notice.
(c) Petitioner shall not leave the National Capital Territory of Delhi without prior permission of the Trial Court.
(d) Petitioner shall surrender his passport before the Investigating Officer within 7 days from today.
(e) Petitioner shall not tamper with evidence or make any inducement, threat or promise to the complainant or any witness.
Application stands disposed of."""

# ---------------------------------------------------------
# Sidebar: Language Selector & Legal Aid
# ---------------------------------------------------------
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg",
        width=70,
    )
    st.markdown("### 🌐 भाषा चुनें / Select Language")
    selected_lang = st.selectbox(
        "Choose Language", options=list(LANG_CONFIG.keys()), index=0
    )
    T = TRANSLATIONS[selected_lang]
    lang_info = LANG_CONFIG[selected_lang]

    st.markdown("---")
    st.markdown(f"#### {T['nalsa_title']}")
    st.info(
        """
    **Article 39A & Legal Services Authorities Act:**
    You are entitled to **100% FREE lawyer & court fees** if you are:
    - 👩 Women or Children
    - 🌾 Farmers / Low-income citizens (annual income < ₹3 Lakhs)
    - ♿ Persons with disabilities
    - ⛓️ Persons in custody / jail
    
    📞 **Toll-Free Helpline:** 15100
    """
    )

    st.markdown("---")
    st.markdown(f"#### {T['jargon_title']}")
    with st.expander("⚖️ Common Terms"):
        st.markdown(
            """
        - **Anticipatory Bail:** Protection from arrest before police can arrest you.
        - **Surety (जमानती):** A person who signs a financial guarantee for your court presence.
        - **Status Quo (यथास्थिति):** Keep everything exactly as it currently is.
        - **Ex-Parte (एकपक्षीय):** Decision taken when the other party did not show up.
        - **Quashed (रद्द):** Completely cancelled and nullified.
        """
        )

# ---------------------------------------------------------
# Main Page Header
# ---------------------------------------------------------
st.markdown(f"<div class='main-title'>⚖️ {T['title']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-title'>{T['tagline']}</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='emergency-banner'>{T['helpline']}</div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Helper Functions: Text Extraction, Gemini API & gTTS
# ---------------------------------------------------------
def extract_text_from_pdf(pdf_file) -> str:
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def analyze_court_order(order_text: str, target_language: str):
    client = get_gemini_client()
    if not client:
        return None, "GEMINI_API_KEY is not set in environment."

    prompt = f"""
    You are 'NyayaMitra', a compassionate and expert Indian public legal aid counselor.
    Analyze the following Indian court order/judgment and explain it so an ordinary citizen with NO legal background can fully understand it.
    
    IMPORTANT: You MUST write the ENTIRE response strictly in {target_language}.
    
    Output strictly valid JSON with this structure:
    {{
        "case_title": "Case Title and Court name",
        "verdict_status": "WIN / RELIEF GRANTED or LOST / RELIEF DENIED or INTERIM / PARTIAL RELIEF",
        "verdict_summary": "1-2 sentences summarizing who won what in everyday language.",
        "jail_or_arrest": "Clearly explain if the citizen has to go to jail, is protected from arrest, or has to surrender.",
        "money_and_deadlines": "List exact amounts to pay (bonds, fines, compensation) and exact timeframes/dates mentioned.",
        "action_steps": [
            "Step 1: Concrete action they or their lawyer must take immediately",
            "Step 2: Second action",
            "Step 3: Documents required"
        ],
        "speech_summary": "A warm, natural 3-sentence summary in {target_language} that will be read aloud over audio to the citizen."
    }}

    Court Order Text:
    {order_text}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        return json.loads(response.text), None
    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------
# Input Section: File Upload or Sample
# ---------------------------------------------------------
col_input, col_sample = st.columns([3, 1])

with col_sample:
    st.write("")
    st.write("")
    load_sample = st.button(f"📋 {T['sample_btn']}", use_container_width=True)

if "case_text" not in st.session_state or load_sample:
    st.session_state["case_text"] = SAMPLE_CASE if load_sample else ""

uploaded_file = st.file_uploader(
    T["upload_label"], type=["pdf", "txt"], help="Upload case order"
)
if uploaded_file is not None:
    if uploaded_file.name.endswith(".pdf"):
        st.session_state["case_text"] = extract_text_from_pdf(uploaded_file)
    else:
        st.session_state["case_text"] = uploaded_file.read().decode("utf-8")

case_text = st.text_area(
    T["paste_label"],
    value=st.session_state["case_text"],
    height=200,
    placeholder="Paste bail order, High Court judgment, or consumer dispute verdict...",
)

analyze_click = st.button(
    f"🚀 {T['analyze_btn']}", type="primary", use_container_width=True
)

# ---------------------------------------------------------
# Processing & Display Results
# ---------------------------------------------------------
if analyze_click:
    if not case_text.strip():
        st.error("Please provide or upload a court order text.")
    else:
        with st.spinner(
            f"Analyzing with Indian Legal NLP in {selected_lang}..."
        ):
            summary_data, err = analyze_court_order(case_text, selected_lang)
            if err:
                st.error(
                    f"Error: {err}. Please ensure `GEMINI_API_KEY` is set in your environment variables."
                )
            else:
                st.session_state["summary_data"] = summary_data

if "summary_data" in st.session_state:
    data = st.session_state["summary_data"]

    st.markdown("---")
    st.subheader(f"📌 {data.get('case_title', 'Court Summary')}")

    # Top Status Banner
    status = data.get("verdict_status", "DECISION")
    st.markdown(
        f"""
        <div class='status-card'>
            <span class='win-badge'>STATUS: {status}</span>
            <p style='font-size: 1.15rem; margin-top: 10px; font-weight: 500;'>{data.get('verdict_summary', '')}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Audio Read-Aloud (gTTS)
    speech_text = data.get(
        "speech_summary", data.get("verdict_summary", "Summary")
    )
    if speech_text:
        st.markdown(f"#### {T['audio_title']}")
        try:
            tts = gTTS(text=speech_text, lang=lang_info["voice_code"])
            fp = BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            st.audio(fp, format="audio/mp3")
        except Exception:
            st.caption(
                "Audio synthesis not available for this specific dialect."
            )

    # 4 Citizen Pillars
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown(f"### 🛡️ {T['q2']}")
            st.write(data.get("jail_or_arrest", "N/A"))

        with st.container(border=True):
            st.markdown(f"### 💰 {T['q3']}")
            st.write(data.get("money_and_deadlines", "N/A"))

    with col2:
        with st.container(border=True):
            st.markdown(f"### 📋 {T['q4']}")
            steps = data.get("action_steps", [])
            for idx, s in enumerate(steps, 1):
                st.markdown(
                    f"<div class='action-step'><strong>{idx}.</strong> {s}</div>",
                    unsafe_allow_html=True,
                )

    # Interactive Ask NyayaMitra Assistant
    st.markdown("---")
    st.markdown(f"### {T['chat_title']}")
    user_query = st.text_input("Ask a follow-up:", placeholder=T["chat_placeholder"])

    if st.button("Ask / पूछें") and user_query:
        client = get_gemini_client()
        if client:
            with st.spinner("Answering..."):
                chat_prompt = f"""
                You are NyayaMitra, a friendly Indian legal guide.
                The citizen has this court order:
                {case_text}
                
                Question asked by citizen: "{user_query}"
                Answer simply, accurately, and reassuringly strictly in {selected_lang}.
                Do not provide formal advocate advice; tell them clearly what the order states.
                """
                chat_resp = client.models.generate_content(
                    model="gemini-2.5-flash", contents=chat_prompt
                )
                st.info(chat_resp.text)
