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

class ArcGISGeocoderAgent:
    def __init__(self):
        self.feature_server_url = "https://services2.arcgis.com/xMRYm7cNgdR5RN6F/arcgis/rest/services/אזורים_סטטיסטיים_WFL1/FeatureServer/3/query"
        self.geocode_url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"

    def geocode(self, parsed_data: ParsedAddress) -> GeocodedAddress:
        if not parsed_data.has_city or not parsed_data.has_street:
            return GeocodedAddress(is_valid=False, error_message="חסרים פרטי חובה (עיר או רחוב).")

        if parsed_data.is_ambiguous:
            return GeocodedAddress(is_valid=False, error_message="הכתובת עמומה מידי.")

        house_num = parsed_data.house_number if parsed_data.house_number else ""
        search_query = f"{parsed_data.street} {house_num}, {parsed_data.city}".strip()
        print(f"🌍 [ArcGIS Agent] מחפש קואורדינטות עבור: '{search_query}'...")

        try:
            # שלב א': המרה לקואורדינטות
            geo_params = {
                "SingleLine": search_query,
                "maxSuggestions": 1,
                "outSR": '{"wkid":102100}', 
                "f": "json"
            }
            
            geo_response = httpx.get(self.geocode_url, params=geo_params, timeout=10.0)
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            candidates = geo_data.get("candidates", [])
            if not candidates:
                return GeocodedAddress(is_valid=False, error_message=f"הכתובת '{search_query}' לא נמצאה במרשם.")
                
            location = candidates[0].get("location", {})
            x, y = location.get("x"), location.get("y")
            
            print(f"✅ נמצאו קואורדינטות מדויקות (X: {x}, Y: {y}). שואל את שרת הלמ\"ס...")

            # שלב ב': שאילתה מרחבית נקודתית (Point במקום Envelope)
            spatial_params = {
                "where": "1=1",
                "geometry": f"{x},{y}",
                "geometryType": "esriGeometryPoint", # שינוי קריטי: חיפוש לפי נקודה מדויקת
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "SHEM_YISHUV,STAT_2022,SEMEL_YISHUV",
                "f": "json"
            }
            
            spatial_response = httpx.get(self.feature_server_url, params=spatial_params, timeout=10.0)
            spatial_response.raise_for_status()
            spatial_data = spatial_response.json()
            
            features = spatial_data.get("features", [])
            if not features:
                return GeocodedAddress(is_valid=False, error_message="הכתובת נמצאה, אך לא נמצאה בתוך שטח סטטיסטי מוגדר של הלמ\"ס.")
                
            attributes = features[0].get("attributes", {})
            stat_area = attributes.get("STAT_2022")
            locality_code = attributes.get("SEMEL_YISHUV", 0)
            
            if not stat_area:
                return GeocodedAddress(is_valid=False, error_message="לא נמצא מספר אזור סטטיסטי רשמי לרשומה זו.")

            return GeocodedAddress(
                is_valid=True,
                locality_code=int(locality_code) if locality_code else 0,
                statistical_area=int(stat_area),
                formatted_address=search_query
            )

        except Exception as e:
            return GeocodedAddress(is_valid=False, error_message=f"שגיאה בתקשורת מול שרתי ArcGIS: {str(e)}")