from dotenv import load_dotenv

# ייבוא הסוכנים של המערכת
from agents.eligibility_agent import EligibilityAgent
from agents.parser_agent import AddressParserAgent
from agents.geocoder_agent import ArcGISGeocoderAgent

# טעינת משתני סביבה (אם יש)
load_dotenv()

# אתחול הסוכנים פעם אחת ברמת המודול (מחליף את ה-st.cache_resource)
eligibility_agent = EligibilityAgent()
parser = AddressParserAgent()
geocoder = ArcGISGeocoderAgent()

# ==========================================
# 1. פונקציית לוגים למפתח (מודפסת רק בטרמינל)
# ==========================================
def print_developer_log(log_data: dict):
    print("\n" + "="*55)
    print("📋 [Developer Log] - נתוני ביניים ובקרה (Backend Only)")
    print("="*55)
    print(f"1. טקסט מקורי:           {log_data.get('original_text')}")
    print(f"2. כתובת מחולצת (LLM):   {log_data.get('parsed_address')}")
    print(f"3. תוצאת Geocoding:      {log_data.get('geocoding_result')}")
    print(f"4. קואורדינטות (X,Y):    {log_data.get('coords')}")
    print(f"5. סמל יישוב:            {log_data.get('locality_code')}")
    print(f"6. קוד אזור סטטיסטי:     {log_data.get('stat_area')}")
    print(f"7. אשכול חברתי-כלכלי:    {log_data.get('socio_cluster')}")
    print(f"8. דירוג פריפריאלי:      {log_data.get('periphery_index')}")
    print(f"9. תוצאת זכאות:          {log_data.get('eligibility_result')}")
    print(f"10. שנת נתונים (למ\"ס):   {log_data.get('data_version')}")
    print("="*55 + "\n")

# ==========================================
# 2. אורקסטרטור (מנהל את התהליך ומחזיר JSON עסקי)
# ==========================================
def process_eligibility(address_input: str) -> dict:
    # אובייקט לאיסוף הנתונים ללוגים בלבד
    log_data = {
        "original_text": address_input,
        "parsed_address": None,
        "geocoding_result": None,
        "coords": None,
        "locality_code": None,
        "stat_area": None,
        "socio_cluster": None,
        "periphery_index": None,
        "eligibility_result": None,
        "data_version": "למ\"ס 2022"
    }

    try:
        # שלב 1: LLM Parse
        parsed = parser.parse(address_input)
        log_data["parsed_address"] = f"{getattr(parsed, 'street', '')} {getattr(parsed, 'house_number', '')}, {getattr(parsed, 'city', '')}"
        
        # 9.4 Response - כתובת עמומה / חסרה
        if parsed.is_ambiguous or not parsed.has_city or not parsed.has_street:
            log_data["eligibility_result"] = "AMBIGUOUS"
            print_developer_log(log_data)
            return {
                "status": "AMBIGUOUS_ADDRESS",
                "message": "נמצאו מספר כתובות אפשריות. נא לבחור את הכתובת המתאימה."
            }

        # שלב 2: Geocode (ArcGIS)
        geocoded = geocoder.geocode(parsed)

        # 9.5 Response - כתובת לא נמצאה
        if not geocoded.is_valid:
            log_data["eligibility_result"] = "NOT_FOUND"
            print_developer_log(log_data)
            return {
                "status": "ADDRESS_NOT_FOUND",
                "message": "לא ניתן למצוא את הכתובת שהוזנה."
            }
            
        # עדכון נתוני לוג מהגאוקודר
        log_data["geocoding_result"] = getattr(geocoded, 'formatted_address', None)
        log_data["coords"] = f"({getattr(geocoded, 'x', 0)}, {getattr(geocoded, 'y', 0)})"
        log_data["locality_code"] = getattr(geocoded, 'locality_code', 0)
        log_data["stat_area"] = getattr(geocoded, 'statistical_area', 0)

        # שלב 3: חישוב זכאות מול הלמ"ס
        stat_area = geocoded.statistical_area if geocoded.statistical_area is not None else 0
        res = eligibility_agent.evaluate(geocoded.locality_code, stat_area)
        
        # חילוץ נתונים מתוך הפלט הישן של agent הזכאות לטובת הלוג של המפתחת
        metadata = res.get("metadata", {})
        log_data["socio_cluster"] = metadata.get("אשכול_חברתי_כלכלי", "לא ידוע")
        log_data["periphery_index"] = metadata.get("מדד_פריפריאליות", "לא ידוע")
        
        # הכרעה סופית
        if res.get("is_eligible", False):
            log_data["eligibility_result"] = "ELIGIBLE"
            print_developer_log(log_data)
            return {"eligible": True, "status": "ELIGIBLE"}
        else:
            log_data["eligibility_result"] = "NOT_ELIGIBLE"
            print_developer_log(log_data)
            return {"eligible": False, "status": "NOT_ELIGIBLE"}

    except Exception as e:
        # 9.8 Response - נתונים חסרים או שגיאת מערכת חמורה
        log_data["eligibility_result"] = f"SYSTEM_ERROR: {str(e)}"
        print_developer_log(log_data)
        return {
            "status": "DATA_UNAVAILABLE",
            "message": "לא ניתן להשלים את בדיקת הזכאות."
        }