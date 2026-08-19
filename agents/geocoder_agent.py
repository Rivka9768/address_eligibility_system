import httpx
from typing import Optional
from pydantic import BaseModel
from agents.parser_agent import ParsedAddress

class GeocodedAddress(BaseModel):
    is_valid: bool
    locality_code: int = 0
    statistical_area: int = 0
    formatted_address: str = ""
    error_message: Optional[str] = None
    x: float = 0.0  # <--- התוספת למודל
    y: float = 0.0  # <--- התוספת למודל

class ArcGISGeocoderAgent:
    def __init__(self):
        self.feature_server_url = "https://services2.arcgis.com/xMRYm7cNgdR5RN6F/arcgis/rest/services/אזורים_סטטיסטיים_WFL1/FeatureServer/3/query"
        self.geocode_url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"

    def geocode(self, parsed_data: ParsedAddress) -> GeocodedAddress:
        # בדיקת חוקיות בסיסית של הקלט
        if not parsed_data.has_city or not parsed_data.has_street:
            return GeocodedAddress(is_valid=False, error_message="חסרים פרטי חובה (עיר או רחוב).")

        if parsed_data.is_ambiguous:
            return GeocodedAddress(is_valid=False, error_message="הכתובת עמומה מידי.")

        house_num = parsed_data.house_number if parsed_data.house_number else ""
        search_query = f"{parsed_data.street} {house_num}, {parsed_data.city}".strip()
        print(f"🌍 [ArcGIS Agent] מחפש קואורדינטות עבור: '{search_query}'...")

        try:
            # שלב א': המרה לקואורדינטות - בקשה הכוללת רזולוציה וציון אמינות
            geo_params = {
                "SingleLine": search_query,
                "maxSuggestions": 1,
                "outSR": '{"wkid":102100}', 
                "outFields": "Score,Addr_type,Match_addr",  # דורשים את רמת הדיוק וסוג ההתאמה
                "f": "json"
            }
            
            geo_response = httpx.get(self.geocode_url, params=geo_params, timeout=10.0)
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            candidates = geo_data.get("candidates", [])
            if not candidates:
                return GeocodedAddress(is_valid=False, error_message=f"הכתובת '{search_query}' לא נמצאה במרשם הכתובות.")
                
            # חילוץ נתוני האימות של המועמד הראשון
            candidate = candidates[0]
            score = candidate.get("score", 0)
            attributes = candidate.get("attributes", {})
            addr_type = attributes.get("Addr_type", "")
            match_addr = attributes.get("Match_addr", "לא ידוע")
            
            # --- חומת מגן מפני הזיות ו-Fallback של ArcGIS ---
            # מאשרים רק התאמות לרחוב, כתובת מדוייקת או צומת רחובות
            valid_addr_types = ["PointAddress", "StreetAddress", "StreetName", "Intersection"]
            
            if score < 85 or addr_type not in valid_addr_types:
                # לוג שקיפות מפורט לקונסול כדי שתוכלי לדבג
                print(f"❌ [ArcGIS Agent] התאמה נדחתה! \n   ביקשנו: '{search_query}'\n   השרת נסוג ל: '{match_addr}' (סוג: {addr_type}, ציון: {score})")
                
                return GeocodedAddress(
                    is_valid=False, 
                    error_message=f"רמת הדיוק נמוכה. המערכת זיהתה '{match_addr}' במקום מה שביקשת. אנא ודא ששם הרחוב תקין."
                )
            
            # אם עברנו את חומת המגן - הכתובת מדויקת באמת
            location = candidate.get("location", {})
            x, y = location.get("x"), location.get("y")
            print(f"✅ [ArcGIS Agent] הכתובת אומתה כ-'{match_addr}' (ציון {score}). שואל את הלמ\"ס לפי קואורדינטות (X: {x}, Y: {y})...")

            # שלב ב': שאילתה מרחבית נקודתית (Point) מול הלמ"ס למציאת האזור הסטטיסטי
            spatial_params = {
                "where": "1=1",
                "geometry": f"{x},{y}",
                "geometryType": "esriGeometryPoint",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "SHEM_YISHUV,STAT_2022,SEMEL_YISHUV",
                "f": "json"
            }
            
            spatial_response = httpx.get(self.feature_server_url, params=spatial_params, timeout=10.0)
            spatial_response.raise_for_status()
            spatial_data = spatial_response.json()
            
            features = spatial_data.get("features", [])
            if not features:
                return GeocodedAddress(is_valid=False, error_message="הכתובת נמצאה במרשם, אך הקואורדינטות אינן נופלות בשטח סטטיסטי מוגדר של הלמ\"ס.")
                
            attributes = features[0].get("attributes", {})
            stat_area = attributes.get("STAT_2022")
            locality_code = attributes.get("SEMEL_YISHUV", 0)
            
            if not stat_area:
                return GeocodedAddress(is_valid=False, error_message="לא נמצא אזור סטטיסטי רשמי לרשומה זו.")

            # החזרת הנתונים - כאן הוספנו את ההשמה של x ו-y!
            return GeocodedAddress(
                is_valid=True,
                locality_code=int(locality_code) if locality_code else 0,
                statistical_area=int(stat_area),
                formatted_address=match_addr,
                x=x,  # <--- התוספת החסרה!
                y=y   # <--- התוספת החסרה!
            )

        except Exception as e:
            return GeocodedAddress(is_valid=False, error_message=f"שגיאה בתקשורת מול שרתי ArcGIS: {str(e)}")