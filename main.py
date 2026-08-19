import json
from dotenv import load_dotenv
from agents.parser_agent import AddressParserAgent
from agents.geocoder_agent import ArcGISGeocoderAgent
from agents.eligibility_agent import EligibilityAgent

load_dotenv()

def init_system():
    """אתחול המערכת וטעינת נתוני הלמ"ס לזיכרון."""
    print("=" * 60)
    print("⏳ מפעיל את המערכת וטוען נתוני למ\"ס לזיכרון (חד-פעמי)...")
    agent = EligibilityAgent()
    print("✅ המערכת מוכנה לשימוש!")
    print("=" * 60)
    return agent

def run_pipeline(raw_text_address: str, eligibility_agent: EligibilityAgent):
    try:
        # --- שלב 1: חילוץ באמצעות LLM ---
        print("\n[שלב 1] מפעיל סוכן חילוץ (AI)...")
        parser = AddressParserAgent()
        parsed = parser.parse(raw_text_address)
        print("תוצאת חילוץ:")
        print(json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2))
        
        # --- שלב 2: אימות מרחבי (ArcGIS Engine) ---
        print("\n[שלב 2] מפעיל סוכן אימות מרחבי (ArcGIS Engine)...")
        geocoder = ArcGISGeocoderAgent()
        geocoded = geocoder.geocode(parsed)
        
        if not geocoded.is_valid:
            print(f"❌ שגיאת אימות: {geocoded.error_message}")
            return
            
        print("✅ הכתובת אומתה בהצלחה!")
        print(f"- כתובת רשמית: {geocoded.formatted_address}")
        print(f"- סמל יישוב: {geocoded.locality_code}")
        print(f"- אזור סטטיסטי: {geocoded.statistical_area}")
        
        # --- שלב 3: חישוב זכאות משולבת ---
        print("\n[שלב 3] מפעיל סוכן זכאות (למ\"ס)...")
        
        if not geocoded.locality_code:
            print("❌ שגיאה: לא ניתן לבדוק זכאות ללא סמל יישוב מוגדר.")
            return
            
        stat_area = geocoded.statistical_area if geocoded.statistical_area is not None else 0
        
        eligibility_result = eligibility_agent.evaluate(
            semel_yishuv=geocoded.locality_code,
            stat_area=stat_area
        )
        
        # הצגת תוצאות הזכאות
        print("\n" + "📊 תוצאת זכאות סופית:")
        if eligibility_result["is_eligible"]:
            print("🎉 הכתובת זכאית!")
        else:
            print("⛔ הכתובת אינה זכאית.")
            
        print("\nנימוקים:")
        for reason in eligibility_result["reasons"]:
            print(f"  * {reason}")
            
        # הדפסת נתוני מטא-דאטה לשקיפות מלאה
        print("\nמידע רקע (Metadata):")
        print(json.dumps(eligibility_result["metadata"], ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"❌ התרחשה שגיאה במהלך העיבוד: {e}")

def main():
    eligibility_agent = init_system()
    
    print("\n🏠 מערכת בדיקת זכאות כתובות")
    print("הכניסי כתובת ולחצי Enter (הקלידי 'exit' או 'יציאה' לסיום)\n")
    
    while True:
        try:
            user_input = input("\n📍 הכניסי כתובת לבדיקה > ").strip()
            
            if user_input.lower() in ["exit", "quit", "יציאה", "q"]:
                print("\n👋 יציאה מהמערכת. יום טוב!")
                break
                
            if not user_input:
                continue
                
            run_pipeline(user_input, eligibility_agent)
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\n\n👋 הופסק על ידי המשתמש. יציאה...")
            break

if __name__ == "__main__":
    main()