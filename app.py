import streamlit as st
import json
from dotenv import load_dotenv

# ייבוא הסוכנים של המערכת
from agents.eligibility_agent import EligibilityAgent
from agents.parser_agent import AddressParserAgent
from agents.geocoder_agent import ArcGISGeocoderAgent

load_dotenv()

# הגדרת תצורת העמוד
st.set_page_config(
    page_title="מנוע בדיקת זכאות",
    page_icon="🚌",
    layout="centered"
)

# טעינת המודלים לזיכרון (Cache) כדי שהמערכת תרוץ במהירות
@st.cache_resource
def init_agents():
    agent = EligibilityAgent()
    parser = AddressParserAgent()
    geocoder = ArcGISGeocoderAgent()
    return agent, parser, geocoder

eligibility_agent, parser, geocoder = init_agents()

# התאמת עיצוב לימין (RTL)
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    .stTextInput input { text-align: right; }
    div[data-testid="stMarkdownContainer"] { text-align: right; }
    </style>
""", unsafe_allow_html=True)

# כותרת והסבר
st.title("🚌 מנוע בדיקת זכאות לפרופיל גיאוגרפי ברב קו")
st.write("אנא הקלד/י את כתובת המגורים שלך")

# קלט מהמשתמש
raw_address = st.text_input( "",placeholder="למשל: הפלמ\"ח 14 ירוחם")

if st.button("בדיקת זכאות", type="primary", use_container_width=True):
    if not raw_address.strip():
        st.warning("נא להזין כתובת לבדיקה.")
    else:
        with st.spinner("מעבד כתובת ומצליב נתוני למ\"ס..."):
            try:
                # שלב 1: AI Parse
                parsed = parser.parse(raw_address)
                
                # שלב 2: Geocode (ArcGIS)
                geocoded = geocoder.geocode(parsed)
                
                if not geocoded.is_valid:
                    st.error(f"❌ שגיאת אימות כתובת: {geocoded.error_message}")
                else:
                    # שלב 3: חישוב זכאות
                    stat_area = geocoded.statistical_area if geocoded.statistical_area is not None else 0
                    res = eligibility_agent.evaluate(geocoded.locality_code, stat_area)
                    
                    st.divider()
                    
                    # תוצאה ראשית
                    if res["is_eligible"]:
                        st.success("🎉 **הכתובת זכאית להטבת פרופיל גיאוגרפי!**")
                    else:
                        st.error("⛔ **הכתובת אינה זכאית להטבה.**")
                    
                    # פירוט הכתובת שנמצאה
                    st.write("**📌 נתוני זיהוי מרחבי:**")
                    st.write(f"* **כתובת מאומתת:** {geocoded.formatted_address}")
                    st.write(f"* **סמל יישוב:** {geocoded.locality_code} | **אזור סטטיסטי:** {geocoded.statistical_area}")
                    
                    # נימוקים
                    st.write("**📋 נימוקי המערכת:**")
                    for reason in res["reasons"]:
                        st.write(f"* {reason}")
                        
                    # מטא-דאטה טכני
                    with st.expander("🔍 הצגת מטא-דאטה ודירוגי למ\"ס גולמיים"):
                        st.json(res["metadata"])
                        
            except Exception as e:
                st.error(f"התרחשה שגיאה בלתי צפויה: {e}")