import os
import json
import pandas as pd
from dotenv import load_dotenv

# ייבוא הסוכנים מתוך המערכת
from agents.eligibility_agent import EligibilityAgent
from agents.parser_agent import AddressParserAgent
from agents.geocoder_agent import ArcGISGeocoderAgent

load_dotenv()

def generate_ground_truth_samples(agent: EligibilityAgent, sample_size_per_class=5):
    """דוגם רשומות מתוך לוח ג' של הלמ"ס להרכבת קבוצת הביקורת (Ground Truth)"""
    samples = []
    df_c = agent.df_socio_c.copy()
    
    # דגימה מתוך יישובים מזכים (1-5) ושאינם מזכים (6-10)
    eligible_df = df_c[df_c['rank'] <= 5].sample(min(sample_size_per_class, len(df_c[df_c['rank'] <= 5])))
    non_eligible_df = df_c[df_c['rank'] > 5].sample(min(sample_size_per_class, len(df_c[df_c['rank'] > 5])))
    
    sampled_df = pd.concat([eligible_df, non_eligible_df])
    
    for _, row in sampled_df.iterrows():
        semel = int(row['semel_yishuv'])
        stat = int(row['stat_area'])
        truth = agent.evaluate(semel, stat)
        
        samples.append({
            "semel_yishuv": semel,
            "stat_area": stat,
            "expected_eligible": truth["is_eligible"],
            "expected_rank": truth["metadata"]["socio_rank"]
        })
    return samples

def run_benchmark():
    """מריץ את בדיקת הביצועים מקצה לקצה ושומר את התוצאות"""
    print("=" * 60)
    print("⏳ מפעיל את המערכת וטוען נתוני למ\"ס לזיכרון...")
    agent = EligibilityAgent()
    parser = AddressParserAgent()
    geocoder = ArcGISGeocoderAgent()
    print("✅ המערכת אותחלה בהצלחה.")
    print("=" * 60)

    print("\n📊 מפיק מדגם אמת (Ground Truth) מתוך לוחות הלמ\"ס...")
    ground_truth_samples = generate_ground_truth_samples(agent, sample_size_per_class=5)
    
    # רשימת כתובות לבדיקה משולבת
    test_addresses = [
        {"raw": "הפלמ\"ח 14 ירוחם", "type": "Clean - Eligible"},
        {"raw": "הרצל 12 תל אביב", "type": "Clean - Non Eligible"},
        {"raw": "ז'בוטינסקי 45 פ\"ת קומה 2", "type": "Noisy Input"},
        {"raw": "רחוב אלנבי 10", "type": "Incomplete - Missing City"},
        {"raw": "השקמה 5 סביון", "type": "Edge Case - High Socio"}
    ]

    results = []
    print(f"\n🚀 מתחיל הרצת {len(test_addresses)} בדיקות עומס...")
    
    for idx, test_item in enumerate(test_addresses, 1):
        raw_address = test_item["raw"]
        addr_type = test_item["type"]
        print(f"[{idx}/{len(test_addresses)}] בודק: '{raw_address}' ({addr_type})")
        
        try:
            # 1. חילוץ
            parsed = parser.parse(raw_address)
            # 2. אימות
            geocoded = geocoder.geocode(parsed)
            
            if geocoded.is_valid:
                stat_area = geocoded.statistical_area if geocoded.statistical_area is not None else 0
                # 3. זכאות
                eval_res = agent.evaluate(geocoded.locality_code, stat_area)
                
                results.append({
                    "raw_address": raw_address,
                    "test_type": addr_type,
                    "is_valid_geocoding": True,
                    "locality_code": geocoded.locality_code,
                    "stat_area": geocoded.statistical_area,
                    "is_eligible": eval_res["is_eligible"],
                    "reasons": "; ".join(eval_res["reasons"])
                })
            else:
                results.append({
                    "raw_address": raw_address,
                    "test_type": addr_type,
                    "is_valid_geocoding": False,
                    "locality_code": None,
                    "stat_area": None,
                    "is_eligible": False,
                    "reasons": f"כשל במיפוי: {geocoded.error_message}"
                })
        except Exception as e:
            results.append({
                "raw_address": raw_address,
                "test_type": addr_type,
                "is_valid_geocoding": False,
                "locality_code": None,
                "stat_area": None,
                "is_eligible": False,
                "reasons": f"שגיאת מערכת: {str(e)}"
            })

    # שמירת התוצאות
    output_file = "benchmark_results.xlsx"
    df_results = pd.DataFrame(results)
    df_results.to_excel(output_file, index=False, engine='openpyxl')
    
    print("\n" + "=" * 60)
    print(f"✅ ההרצה הושלמה בהצלחה!")
    print(f"💾 התוצאות נשמרו בקובץ: {output_file}")
    print("=" * 60)

# בלוק ההפעלה הראשי
if __name__ == "__main__":
    run_benchmark()