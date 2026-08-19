import os
import httpx
import pandas as pd

PERIPHERY_URL = "https://www.cbs.gov.il/he/publications/DocLib/2023/1917/table_02.xlsx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_excel_file(url: str, local_path: str) -> str:
    """שומר את הקובץ מקומית בתיקיית data כדי למנוע חסימות והורדות חוזרות."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(local_path):
        print(f"📥 מוריד טבלת פריפריאליות משרתי הלמ\"ס: {url}")
        with httpx.Client(headers=HEADERS, verify=False, follow_redirects=True, timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(resp.content)
    else:
        print(f"📂 טוען קובץ שמור: {local_path}")
    return local_path

def get_periphery_index(semel_yishuv: int) -> dict:
    local_file = load_excel_file(PERIPHERY_URL, "data/table_periphery.xlsx")
    
    # טעינת עמודה D (סמל יישוב) ועמודה P (מדד פריפריאלי)
    df = pd.read_excel(local_file, usecols="D,P", header=None)
    df.columns = ['semel_yishuv', 'periphery_index']
    
    # המרה למספרים וסינון שורות כותרת וטקסט חופשי
    df['semel_yishuv'] = pd.to_numeric(df['semel_yishuv'], errors='coerce')
    df['periphery_index'] = pd.to_numeric(df['periphery_index'], errors='coerce')
    df = df.dropna()

    match = df[df['semel_yishuv'] == semel_yishuv]
    
    if not match.empty:
        return {
            "found": True,
            "semel_yishuv": semel_yishuv,
            "periphery_index": int(match.iloc[0]['periphery_index'])
        }

    return {
        "found": False,
        "error": f"סמל היישוב {semel_yishuv} לא נמצא בטבלת המדד הפריפריאלי."
    }

if __name__ == "__main__":
    # מקרה בדיקה 1: תל אביב (5000)
    res1 = get_periphery_index(semel_yishuv=5000)
    print("\nתוצאה 1 (תל אביב):", res1)

    # מקרה בדיקה 2: ראשון לציון (8300)
    res2 = get_periphery_index(semel_yishuv=8300)
    print("\nתוצאה 2 (ראשון לציון):", res2)
    
    # מקרה בדיקה 3: תל מונד (154)
    res3 = get_periphery_index(semel_yishuv=154)
    print("\nתוצאה 3 (תל מונד):", res3)