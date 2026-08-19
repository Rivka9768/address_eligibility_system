import os
import json
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI

# 1. טעינת מפתח ה-API מקובץ .env
load_dotenv()

# 2. הגדרת מבנה הפלט המבוקש (Structured Output)
class ParsedAddress(BaseModel):
    city: Optional[str] = Field(default=None, description="שם העיר או היישוב כולל פתיחת ראשי תיבות (למשל 'תל אביב -יפו')")
    street: Optional[str] = Field(default=None, description="שם הרחוב ללא אותיות יחס (למשל 'ז'בוטינסקי' ולא 'ברחוב ז'בוטינסקי')")
    house_number: Optional[str] = Field(default=None, description="מספר הבית בלבד")
    entrance: Optional[str] = Field(default=None, description="כניסה לבניין במידה וקיימת (למשל 'א')")
    apartment: Optional[str] = Field(default=None, description="מספר דירה במידה וקיים")
    has_city: bool = Field(description="האם הוזכרה עיר בקלט")
    has_street: bool = Field(description="האם הוזכר רחוב בקלט")
    has_house_number: bool = Field(description="האם הוזכר מספר בית בקלט")
    is_ambiguous: bool = Field(description="האם הקלט עמום, מבלבל או חסר פרט קריטי")

# 3. מחלקת הסוכן
class AddressParserAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("שגיאה: מפתח OPENAI_API_KEY לא נמצא בקובץ .env")
        self.client = OpenAI(api_key=api_key)
        self.system_prompt = """
תפקידך לחלץ רכיבי כתובת בישראל מתוך טקסט חופשי בעברית.

כללים קשיחים:
1. אל תמציא פרטים שלא קיימים בטקסט. אם עיר לא צוינה, החזר null בשדה city וסמן has_city=false.
2. פתח ראשי תיבות וקיצורים מקובלים בישראל (לדוגמה: "ת"א" -> "תל אביב -יפו", "ר"ג" -> "רמת גן", "ראשל"צ" -> "ראשון לציון", "פ"ת" -> "פתח תקווה", "שד'" -> "שדרות").
3. נקה אותיות יחס ומילות קישור בשם הרחוב והעיר (לדוגמה: "ברחוב דיזנגוף" -> "דיזנגוף", "בחיפה" -> "חיפה").
4. הפרד באופן מדויק בין מספר בית, כניסה ודירה (למשל "הרצל 12/4 ב'" -> בית 12, דירה 4, כניסה ב').
5. תקן שגיאות כתיב פונטיות או תקלות הקלדה נפוצות (למשל "ירשלים" -> "ירושלים").
6. סמן is_ambiguous=true אם חסרה עיר או רחוב, או אם המידע לא חד-משמעי.
"""

    def parse(self, raw_text: str) -> ParsedAddress:
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"חלץ את הכתובת הבאה:\n\"{raw_text}\""}
            ],
            response_format=ParsedAddress,
            temperature=0.0
        )
        return response.choices[0].message.parsed

# 4. הרצת סדרת בדיקות
if __name__ == "__main__":
    parser = AddressParserAgent()
    
    # test_cases = [
    #     "אני גרה בהרצל 12 א' דירה 4 תא",
    #     "רחוב ז'בוטינסקי 45/2 פתח תקווה",
    #     "ארלוזרוב 80 ירשלים",
    #     "שד ירושלים 15 ראשלצ",
    #     "רק רחוב אלנבי בלי עיר"
    # ]
    test_cases = [
    # 1. טקסט מבוסס שיחה ורועש במיוחד (Conversational Noise)
    "אני אצל דודה טובה ברחוב אלנבי 44 דירה 3 תל אביב תביאו פיצה",
    "אחי אני גורע בבן יהודה 12 בחיפה ליד המכולת של שמעון",
    
    # 2. מספרים שכתובים במילים + שגיאות פונטיות
    "זאבוטינסקיי חמישים במזכרת באתיה",
    "חיימ ויצמנ 108 רחובות",  # ללא אותיות סופיות
    
    # 3. עמימות וחוסר ודאות בקלט
    "אני לא בטוח אם זה 12 או 14 אבל ברחוב הרצל בבאר שבע",
    "שדרות בן גוריון 5",  # חסרה עיר (יש בן גוריון בעשרות ערים)
    
    # 4. חסר מידע בסיסי
    "רק עיר: אילת",
    
    # 5. טקסט שאין בו כתובת כלל (המודל אמור להחזיר null בכולם ו-is_ambiguous=true)
    "שלום שמי דני ואני רוצה לבדוק זכאות להנחה ברב קו",
    "סבתא שלי גרה ברחוב מעבר המתלה 7 ירושלים ארץ הקודש תבל עולם"
    ]
    
    print("=== מתחיל בדיקת סוכן חילוץ כתובות ===\n")
    for text in test_cases:
        print(f"קלט: \"{text}\"")
        try:
            result = parser.parse(text)
            print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"שגיאה: {e}")
        print("-" * 40)