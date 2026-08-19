import os
from typing import Optional
from pydantic import BaseModel, Field
from openai import OpenAI, APIConnectionError, APIError

# מבנה הנתונים המדויק (Schema) שה-API של OpenAI יחזיר אלינו
class ParsedAddress(BaseModel):
    city: Optional[str] = Field(default=None, description="שם העיר או היישוב כולל פתיחת ראשי תיבות (למשל 'תל אביב -יפו')")
    street: Optional[str] = Field(default=None, description="שם הרחוב ללא אותיות יחס (למשל 'ז'בוטינסקי' ולא 'ברחוב ז'בוטינסקי')")
    house_number: Optional[str] = Field(default=None, description="מספר הבית בלבד (ללא אותיות כניסה או מספר דירה)")
    entrance: Optional[str] = Field(default=None, description="כניסה לבניין במידה וקיימת (למשל 'א')")
    apartment: Optional[str] = Field(default=None, description="מספר דירה במידה וקיים")
    has_city: bool = Field(description="האם הוזכרה עיר בקלט")
    has_street: bool = Field(description="האם הוזכר רחוב בקלט")
    has_house_number: bool = Field(description="האם הוזכר מספר בית בקלט")
    is_ambiguous: bool = Field(description="האם הקלט עמום, מבלבל או חסר פרט קריטי (כמו עיר או רחוב)")

class AddressParserAgent:
    def __init__(self):
        # טעינת מפתח ה-API האמיתי מתוך מערכת ההפעלה / קובץ ה-.env
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("שגיאה קריטית: מפתח OPENAI_API_KEY לא נמצא בסביבת העבודה. נא להוסיף לקובץ .env")
            
        # אתחול הקליינט מול השרתים האמיתיים של OpenAI (עם הגבלת זמן למקרה של בעיות רשת)
        self.client = OpenAI(api_key=api_key, timeout=15.0)
        
        # חוקי הברזל שאנו מעבירים למודל השפה
        self.system_prompt = """
תפקידך לחלץ רכיבי כתובת בישראל מתוך טקסט חופשי בעברית.

כללים קשיחים:
1. אל תמציא פרטים שלא קיימים בטקסט. אם עיר לא צוינה, החזר null בשדה city וסמן has_city=false.
2. פתח ראשי תיבות וקיצורים מקובלים בישראל (לדוגמה: "ת"א" -> "תל אביב -יפו", "ר"ג" -> "רמת גן", "ראשל"צ" -> "ראשון לציון").
3. נקה אותיות יחס ומילות קישור בשם הרחוב והעיר (לדוגמה: "ברחוב דיזנגוף" -> "דיזנגוף", "בחיפה" -> "חיפה").
4. הפרד באופן מדויק בין מספר בית, כניסה ודירה.
5. תקן שגיאות כתיב פונטיות או תקלות הקלדה נפוצות בהקשר של שמות ערים ורחובות, אם יש מילה שרוב אותיותיה תואמות שם רחוב או עיר, תקן אותה.
6. סמן is_ambiguous=true אם חסרה עיר או רחוב, או אם הקלט לא נראה כמו כתובת כלל.
"""

    def parse(self, raw_text: str) -> ParsedAddress:
        """
        שולחת את הטקסט ל-OpenAI ומקבלת חזרה אובייקט Python מאומת.
        """
        try:
            # קריאה אמיתית ל-API של OpenAI, ל-Endpoint של Structured Outputs
            response = self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"חלץ את הכתובת הבאה:\n\"{raw_text}\""}
                ],
                response_format=ParsedAddress,
                temperature=0.0 # דורש מהמודל להיות מדויק ודטרמיניסטי, ללא "יצירתיות"
            )
            
            # החזרת המבנה המפוענח
            return response.choices[0].message.parsed
            
        except APIConnectionError:
            print("❌ שגיאת תקשורת: לא ניתן להתחבר לשרתי OpenAI. בדקי את חיבור האינטרנט.")
            raise
        except APIError as e:
            print(f"❌ שגיאת API מ-OpenAI: {e}")
            raise
        except Exception as e:
            print(f"❌ שגיאה לא צפויה במהלך חילוץ הכתובת: {e}")
            raise