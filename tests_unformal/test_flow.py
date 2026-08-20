import json
from dotenv import load_dotenv
from agents.parser_agent import AddressParserAgent
from agents.geocoder_agent import ArcGISGeocoderAgent

# חובה לטעון את קובץ ה-.env כדי שמפתח ה-API של OpenAI יהיה זמין
load_dotenv()

def test_integration_flow(raw_text: str):
    print(f"\n" + "="*50)
    print(f"🚀 מתחיל בדיקת זרימה (Flow) מלאה")
    print(f"🗣️ קלט המשתמש (טקסט חופשי): '{raw_text}'")
    print("="*50)
    
    try:
        # ---------------------------------------------------------
        # שלב 1: סוכן החילוץ (OpenAI Parser)
        # ---------------------------------------------------------
        print("\n🤖 [שלב 1] מפעיל סוכן חילוץ מבוסס בינה מלאכותית...")
        parser = AddressParserAgent()
        parsed_data = parser.parse(raw_text)
        
        print("✅ תוצאת החילוץ מהטקסט (JSON):")
        # מדפיסים את האובייקט בצורה יפה וקריאה
        print(json.dumps(parsed_data.model_dump(), ensure_ascii=False, indent=2))
        
        # בדיקת תקינות לפני שממשיכים הלאה
        if parsed_data.is_ambiguous or not parsed_data.has_city or not parsed_data.has_street:
            print("\n⚠️ הכתובת שחולצה חסרה או עמומה. עוצר את התהליך (לא פונה לשרתי המפות).")
            return

        # ---------------------------------------------------------
        # שלב 2: סוכן גיאוגרפי (ArcGIS - הלמ"ס)
        # ---------------------------------------------------------
        print("\n🌍 [שלב 2] מעביר את הנתונים המובנים לשרתי המפות של הלמ\"ס...")
        geocoder = ArcGISGeocoderAgent()
        geocoded_data = geocoder.geocode(parsed_data)
        
        if geocoded_data.is_valid:
            print("\n🎉 בינגו! התקבל אזור סטטיסטי רשמי:")
            print(f"📍 כתובת שנבדקה: {geocoded_data.formatted_address}")
            print(f"🏢 סמל יישוב: {geocoded_data.locality_code}")
            print(f"📊 אזור סטטיסטי (STAT_2022): {geocoded_data.statistical_area}")
        else:
            print(f"\n❌ שגיאה בשלב 2 (לא נמצא במפה): {geocoded_data.error_message}")
            
    except Exception as e:
        print(f"\n❌ התרחשה שגיאה במהלך הריצה: {e}")

if __name__ == "__main__":
    # אפשר לשנות את המשפטים כאן כדי לבדוק איך המערכת מתמודדת עם ניסוחים שונים
    test_cases = [
        "אני גרה בהרצל 12 בתל אביב, דירה 4 קומה 2",
        "הכתובת שלי היא רחוב ז'בוטינסקי 45 בפתח תקווה",
        "רק רחוב אלנבי בלי מספר בית", # פה נראה אם המערכת מתמודדת יפה עם חוסר נתונים
        "קוראים לי רבקה סורשר ואני נערה חמודה ומתוקה נורא אוהבת מאוד לטייל בעולם שהשם יתברך ברא איזה עולם נפלא ונדיר במיוחד אוהבת לבקר את אחותי שעשכיו ילדה תינוק באצל 14 בירשלים דירה 1 קומה ראשונה",
        "שדרות בן גוריון 5", # חסרה עיר (יש בן גוריון בעשרות ערים)  
        "שלום שמי דני ואני רוצה לבדוק זכאות להנחה ברב קו", # אין כתובת כלל  
        "סבתא שלי גרה ברחוב מעבר המתלה 7 ירושלים ארץ הקודש תבל עולם", # כתובת מלאה   
        "רחוב רבקה  ירושלים  מספר  1 "
    ]
    
    for case in test_cases:
        test_integration_flow(case)