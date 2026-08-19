from test_socio_lookup import get_socio_economic_cluster

# מקרי קצה לבדיקה:
# 1. עיר גדולה עם חלוקה פנימית (תל אביב - לוח ג')
# 2. יישוב ללא חלוקה פנימית שדורש נפילה ללוח ב' (סביון)
# 3. יישוב פריפריאלי ללא חלוקה פנימית (ג'סר א-זרקא)
# 4. עיר עם חלוקה פנימית ואזור סטטיסטי 1 (מודיעין-מכבים-רעות)
# 5. סמל יישוב פיקטיבי/שגוי לבדיקת רובוסטיות

EDGE_TEST_CASES = [
    {
        "name": "עיר מטרופולינית עם חלוקה פנימית",
        "semel_yishuv": 5000,  # תל אביב - יפו
        "stat_area": 533
    },
    {
        "name": "יישוב ללא חלוקה פנימית (מעבר ללוח ב')",
        "semel_yishuv": 5800,  # סביון
        "stat_area": 0
    },
    {
        "name": "יישוב פריפריאלי ללא חלוקה פנימית",
        "semel_yishuv": 541,   # ג'סר א-זרקא
        "stat_area": 0
    },
    {
        "name": "עיר עם חלוקה פנימית (אזור 1)",
        "semel_yishuv": 1200,  # מודיעין-מכבים-רעות
        "stat_area": 1
    },
    {
        "name": "קלט שגוי - סמל יישוב מחוץ למאגר",
        "semel_yishuv": 99999,
        "stat_area": 99
    }
]

def run_edge_case_tests():
    print("🧪 מתחיל הרצת מקרי קצה (Edge Cases)...")
    print("=" * 60)
    
    passed_count = 0
    
    for case in EDGE_TEST_CASES:
        print(f"\n🔹 בדיקה: {case['name']}")
        print(f"   קלט: סמל יישוב = {case['semel_yishuv']}, אזור סטטיסטי = {case['stat_area']}")
        
        res = get_socio_economic_cluster(case['semel_yishuv'], case['stat_area'])
        
        if res.get("found"):
            print(f"   ✅ נמצא! מקור: {res['source']} | דירוג: {res['rank']}")
            passed_count += 1
        else:
            if case['semel_yishuv'] == 99999:
                print(f"   ✅ טיפול נכון בשגיאה: {res['error']}")
                passed_count += 1
            else:
                print(f"   ❌ נכשל! {res.get('error')}")
                
    print("\n" + "=" * 60)
    print(f"🏁 סיכום בדיקות: {passed_count}/{len(EDGE_TEST_CASES)} בדיקות עברו בהצלחה.")

if __name__ == "__main__":
    run_edge_case_tests()