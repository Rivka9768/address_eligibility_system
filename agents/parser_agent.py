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
        Your task is to extract Israeli address components from raw text provided in any language, and output the data STRICTLY in valid Hebrew, maintaining absolute fidelity to the source with zero hallucinations.

        STRICT EXTRACTION & NORMALIZATION RULES:

        1. Strict Phonetic Transliteration (No Over-Correction):
           - Transliterate street names into Hebrew exactly as they sound in the input (e.g., "Shamgar" -> "שמגר", "Mitle" -> "מיתלה").
           - CRITICAL WARNING: Do not attempt to "fix" typos by guessing. Never replace a given street name with a different existing street name (e.g., NEVER change "Shamgar" to "שמשון"). Return the exact phonetic transliteration.

        2. Base Term Translation Only:
           - City names: Translate to the official recognized Hebrew name (e.g., "Jerusalem" / "Jerusalm" -> "ירושלים", "Jaffa" -> "יפו").
           - Street types & semantic terms: Translate to Hebrew (e.g., "Pass" -> "מעבר", "Street" / "St" -> "רחוב", "Road" / "Rd" -> "דרך", "Blvd" -> "שדרות", "Square" -> "כיכר").
           - Semantic terms within street names: Translate the term (e.g., "King" -> "המלך", "Independence" -> "העצמאות").

        3. Ignore Neighborhoods (Streets Only):
           - Inputs often contain both a neighborhood and a street name (e.g., "Ramat Eshkol" alongside "Mitle Pass").
           - You must extract ONLY the specific street name into the `street` field and COMPLETELY IGNORE the neighborhood name. Do not let the neighborhood overwrite the street name.

        4. Remove Prepositions and Conjunctions:
           - Strip prepositions from city and street names in any language (e.g., "ברחוב דיזנגוף" -> "דיזנגוף", "In Tel Aviv" -> "תל אביב -יפו", "st. Herzl" -> "הרצל").

        5. Precise Parsing of Numbers:
           - Accurately separate the house number, entrance, and apartment number, even if written in a clumsy format (e.g., "Apt 4" -> apartment="4", "Entrance A" -> entrance="א'").

        6. Expand Acronyms:
           - Expand common Israeli city acronyms to their full Hebrew names (e.g., "ת\"א" -> "תל אביב -יפו", "ר\"ג" -> "רמת גן", "ראשל\"צ" -> "ראשון לציון").

        7. Absolute Fidelity & Ambiguity:
           - Do not invent missing details. If a component is missing from the input, return `null` and update the boolean fields accordingly.
           - Mark `is_ambiguous=true` if either the city or the street is missing, or if the input does not resemble an address at all.

        FEW-SHOT EXAMPLES:

        Input: "Jerusalem Shamgar 12"
        Output:
        - city: "ירושלים"
        - street: "שמגר"
        - house_number: "12"
        - has_city: true, has_street: true, has_house_number: true, is_ambiguous: false

        Input: "mitle pass ramat eshkol jerusalm 7"
        Output:
        - city: "ירושלים"
        - street: "מעבר המיתלה"
        - house_number: "7"
        - has_city: true, has_street: true, has_house_number: true, is_ambiguous: false

        Input: "Apt 4, 12 Ben Gurion st. Tel Aviv"
        Output:
        - city: "תל אביב -יפו"
        - street: "בן גוריון"
        - house_number: "12"
        - apartment: "4"
        - has_city: true, has_street: true, has_house_number: true, is_ambiguous: false
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