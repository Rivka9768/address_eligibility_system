from test_socio_lookup import get_socio_economic_cluster
from test_periphery_lookup import get_periphery_index

# רשימת מקרי בדיקה מגוונים
TEST_CASES = [
    {
        "description": "תל אביב - יפו (אזור 533)",
        "semel_yishuv": 5000,
        "stat_area": 533
    },
    {
        "description": "ראשון לציון",
        "semel_yishuv": 8300,
        "stat_area": 511
    },
    {
        "description": "סביון (יישוב ללא חלוקה פנימית)",
        "semel_yishuv": 587,
        "stat_area": 1
    }
]

def run_combined_tests():
    print("🧪 מתחיל הרצת טסט משולב (חברתי-כלכלי + פריפריאלי)...")
    print("=" * 65)

    for test in TEST_CASES:
        semel = test["semel_yishuv"]
        stat = test["stat_area"]
        
        print(f"\n📍 מקרה בדיקה: {test['description']}")
        print(f"   קלט: סמל יישוב = {semel}, אזור סטטיסטי = {stat}")

        # שליפת נתונים מ-2 המנגנונים
        socio_data = get_socio_economic_cluster(semel_yishuv=semel, stat_area=stat)
        periphery_data = get_periphery_index(semel_yishuv=semel)

        # הצגת תוצאות שליפה חברתית-כלכלית
        if socio_data.get("found"):
            print(f"   🔹 מדד חברתי-כלכלי: {socio_data['rank']} (מקור: {socio_data['source']})")
        else:
            print(f"   ❌ מדד חברתי-כלכלי: לא נמצא")

        # הצגת תוצאות שליפה פריפריאלית
        if periphery_data.get("found"):
            print(f"   🔹 מדד פריפריאלי:     {periphery_data['periphery_index']}")
        else:
            print(f"   ❌ מדד פריפריאלי:     לא נמצא")

    print("\n" + "=" * 65)
    print("🏁 הרצת הטסט המשולב הושלמה.")

if __name__ == "__main__":
    run_combined_tests()