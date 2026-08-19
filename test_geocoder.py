from agents.parser_agent import ParsedAddress
from agents.geocoder_agent import ArcGISGeocoderAgent

def test_arcgis_geocoder():
    # 1. הגדרת הקלט (הדמיה של מה שחוזר מ-OpenAI)
    mock_parsed_address = ParsedAddress(
        city="ירושלים",
        street="שמגר",
        house_number="12",
        entrance=None,
        apartment=None,
        has_city=True,
        has_street=True,
        has_house_number=True,
        is_ambiguous=False
    )

    print("--- מתחיל בדיקה של סוכן ArcGIS (למ\"ס) ---")
    
    # 2. אתחול הסוכן
    agent = ArcGISGeocoderAgent()
    
    # 3. שליחת הקלט לסוכן כדי לקבל פלט
    result = agent.geocode(mock_parsed_address)
    
    # 4. הדפסת הפלט
    print("\n--- פלט (Output) ---")
    print(f"האם הכתובת תקינה ונמצאה? {result.is_valid}")
    
    if result.is_valid:
        print(f"כתובת מעובדת: {result.formatted_address}")
        print(f"סמל יישוב: {result.locality_code}")
        print(f"אזור סטטיסטי (STAT_2022): {result.statistical_area}")
    else:
        print(f"שגיאה: {result.error_message}")

if __name__ == "__main__":
    test_arcgis_geocoder()