import unittest
from dotenv import load_dotenv

# טעינת משתני הסביבה כדי שכל הסוכנים יוכלו לתקשר עם העולם החיצון (OpenAI API וכו')
load_dotenv()

from agents.parser_agent import AddressParserAgent
from agents.geocoder_agent import ArcGISGeocoderAgent
from agents.eligibility_agent import EligibilityAgent

class TestSystemIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # אתחול כל הסוכנים האמיתיים
        cls.parser = AddressParserAgent()
        cls.geocoder = ArcGISGeocoderAgent()
        cls.eligibility = EligibilityAgent()

    def test_parser_to_geocoder_integration(self):
        """
        בדיקת אינטגרציה 1: Parser -> Geocoder
        מוודא שהפלט שה-LLM מייצר מתקבל כראוי ונבלע בהצלחה על ידי ArcGIS
        """
        raw_text = "אני גר ברחוב מחל 20 ירושלים"
        
        # שלב 1: חילוץ
        parsed = self.parser.parse(raw_text)
        self.assertTrue(parsed.has_city and parsed.has_street, "ה-Parser כשל בחילוץ הנתונים")
        
        # שלב 2: העברת האובייקט ל-Geocoder (זו בדיקת האינטגרציה האמיתית)
        geocoded = self.geocoder.geocode(parsed)
        
        self.assertTrue(geocoded.is_valid, f"ה-Geocoder דחה את הפלט של ה-Parser. שגיאה: {geocoded.error_message}")
        self.assertEqual(geocoded.locality_code, 3000, "סמל יישוב שגוי לירושלים, האינטגרציה הגיאוגרפית נכשלה")
        self.assertGreater(geocoded.statistical_area, 0, "לא זוהה אזור סטטיסטי")

    def test_geocoder_to_eligibility_integration(self):
        """
        בדיקת אינטגרציה 2: Geocoder -> Eligibility
        מוודא שסמלי היישוב והאזור הסטטיסטי שמחזיר ה-Geocoder מפעילים נכון את מנוע הזכאות
        """
        # אנו נדמה מצב שבו ה-Geocoder החזיר לנו את ירוחם (סמל 831, אזור סטטיסטי 2)
        simulated_locality_code = 831 
        simulated_stat_area = 2
        
        # העברת הנתונים למנוע הזכאות
        eligibility_res = self.eligibility.evaluate(simulated_locality_code, simulated_stat_area)
        
        self.assertIn("is_eligible", eligibility_res, "מבנה הנתונים שחזר ממנוע הזכאות שגוי")
        self.assertTrue(eligibility_res["is_eligible"], "ירוחם אמורה להיות זכאית. חוסר התאמה בנתוני הזכאות האמיתיים.")

    def test_full_end_to_end_integration(self):
        """
        בדיקת אינטגרציה מלאה (End-to-End): טקסט חופשי -> Parser -> Geocoder -> Eligibility
        בדיקת הצינור המלא מקצה לקצה בדיוק כמו שהמשתמש חווה אותו.
        """
        # נשתמש בכתובת אמיתית מעיר בעלת אשכול חברתי כלכלי נמוך ופריפריה
        raw_text = "הכתובת שלי היא הפלמח 14 ירוחם, האם אני זכאי?"
        
        # 1. חילוץ (Parser)
        parsed = self.parser.parse(raw_text)
        self.assertTrue(parsed.has_city, "החילוץ הראשוני נכשל")
        
        # 2. קידוד גיאוגרפי (Geocoder)
        geocoded = self.geocoder.geocode(parsed)
        self.assertTrue(geocoded.is_valid, f"Geocoding נכשל בשלב ה-E2E: {geocoded.error_message}")
        self.assertEqual(geocoded.locality_code, 831, "ה-Geocoder לא זיהה נכון את סמל ירוחם מהטקסט של ה-LLM")
        
        # 3. זכאות (Eligibility)
        eligibility_res = self.eligibility.evaluate(geocoded.locality_code, geocoded.statistical_area)
        
        # בדיקת התוצאה הסופית
        self.assertIn("is_eligible", eligibility_res)
        self.assertTrue(eligibility_res["is_eligible"], "בדיקת הקצה לקצה נכשלה, התוצאה הסופית אינה תואמת את הציפיות.")
        
        # בדיקה שהמטא-דאטה עבר כראוי כל הדרך אל התשובה הסופית
        self.assertIn("metadata", eligibility_res)
        # במקום לבדוק שזה 'area', נבדוק שהמערכת שאבה את הנתון בהצלחה מלוח א'
        self.assertEqual(eligibility_res["metadata"]["socio_source"], "לוח א' (רשויות מקומיות)", "מקור נתוני האשכול לירוחם מגיע מלוח הרשויות המקומיות")

if __name__ == '__main__':
    unittest.main()