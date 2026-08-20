import os
import unittest
import pandas as pd
from dotenv import load_dotenv

# 1. טעינת משתני הסביבה כדי שה-OPENAI_API_KEY יהיה זמין לסוכן ה-Parser
load_dotenv()

from agents.parser_agent import AddressParserAgent
from agents.geocoder_agent import ArcGISGeocoderAgent
from agents.eligibility_agent import EligibilityAgent

# נגדיר מחלקה זמנית כדי לדמות פלט של Parser עבור ה-Geocoder
class MockParsedAddress:
    def __init__(self, street, house_number, city, has_street=True, has_city=True, is_ambiguous=False):
        self.street = street
        self.house_number = house_number
        self.city = city
        self.has_street = has_street
        self.has_city = has_city
        self.is_ambiguous = is_ambiguous

class TestAddressParserAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = AddressParserAgent()

    def test_valid_input(self):
        res = self.parser.parse("הפלמח 14 ירוחם")
        self.assertTrue(res.has_city)
        self.assertTrue(res.has_street)
        self.assertIn("ירוחם", res.city)

    def test_partial_input_missing_city(self):
        res = self.parser.parse("רחוב הרצל 12")
        self.assertFalse(res.has_city, "הסוכן אמור לזהות שחסרה עיר")

    def test_edge_case_gibberish(self):
        res = self.parser.parse("בלה בלה בלה 9999")
        self.assertTrue(res.is_ambiguous or not (res.has_city and res.has_street))

class TestArcGISGeocoderAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geocoder = ArcGISGeocoderAgent()

    def test_valid_address(self):
        parsed = MockParsedAddress("מחל", "20", "ירושלים")
        # 2. הוסר הפרמטר raw_text כדי להתאים לחתימת הפונקציה
        res = self.geocoder.geocode(parsed)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.locality_code, 3000, "סמל יישוב של ירושלים צריך להיות 3000")
        self.assertGreater(res.statistical_area, 0, "אמור לחזור אזור סטטיסטי תקין")

    def test_invalid_address(self):
        parsed = MockParsedAddress("רחובשלאקיים", "999", "עירדמיונית")
        res = self.geocoder.geocode(parsed)
        self.assertFalse(res.is_valid, "הכתובת לא אמורה להיות מאומתת")

    def test_ambiguous_address(self):
            parsed = MockParsedAddress("הרצל", "5", "", has_city=False)
            res = self.geocoder.geocode(parsed)
            
            # כתובת עמומה (בלי עיר) צריכה לחזור כלא חוקית עם הודעת שגיאה
            self.assertFalse(res.is_valid, "הכתובת עמומה ולכן לא צריכה להיות תקפה")
            self.assertIsNotNone(res.error_message, "אמורה לחזור הודעת שגיאה שמסבירה את העמימות")
            self.assertGreater(len(res.error_message), 0, "הודעת השגיאה לא יכולה להיות ריקה")

class TestEligibilityAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eligibility = EligibilityAgent()
        
        # 3. Mock Data: הזרקת נתוני דמה (DataFrames) עם סמלי היישוב המדויקים (587 - סביון, 666 - עומר)
        cls.eligibility.df_socio_c = pd.DataFrame({
            'semel_yishuv': [1161], # רהט
            'stat_area': [1],
            'ses_locality': [1],    # אשכול יישוב 1
            'ses_area': [2]         # אשכול אזור 2 (זכאי)
        })
        
        cls.eligibility.df_socio_b = pd.DataFrame({
            'semel_yishuv': [587, 666], # סביון, עומר
            'rank': [10, 9]             # אשכול יישוב 10 ו-9 בהתאמה
        })
        
        cls.eligibility.df_socio_a = pd.DataFrame(columns=['semel_yishuv', 'rank'])
        
        cls.eligibility.df_periphery = pd.DataFrame({
            'semel_yishuv': [1161, 587, 666],
            'rank': [2, 10, 4] # רהט (2), סביון (10 - לא זכאי), עומר (4 - זכאי פריפריה אך אמור להיפסל על אשכול 9)
        })

    def test_eligible_low_ses(self):
        res = self.eligibility.evaluate(1161, 1)
        self.assertTrue(res["is_eligible"], "רהט אמורה להיות זכאית")
        self.assertLessEqual(res["socio_cluster"], 5, "האשכול החברתי-כלכלי אמור להיות 1-5")

    def test_not_eligible_high_ses(self):
        res = self.eligibility.evaluate(587, 1) # סביון (587)
        self.assertFalse(res["is_eligible"], "סביון לא אמורה להיות זכאית")
        self.assertIn(res["metadata"]["ses_locality"], [9, 10], "האשכול היישובי צריך להיות 9-10")

    def test_periphery_but_high_ses_exclusion(self):
        res = self.eligibility.evaluate(666, 1) # עומר (666)
        self.assertFalse(res["is_eligible"], "יישוב פריפריאלי באשכול 9-10 אמור להיפסל")
        
        exclusion_reason_found = any("מוחרג" in reason or "נפסל" in reason for reason in res["reasons"])
        self.assertTrue(exclusion_reason_found, "אמור להופיע נימוק על החרגה בגלל אשכול יישובי")

if __name__ == '__main__':
    unittest.main()