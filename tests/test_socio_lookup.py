import os
import httpx
import pandas as pd

URL_TABLE_C = "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t4.xlsx" # לוח ג - יישובים עם חלוקה פנימית (B, G, K)
URL_TABLE_B = "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t3.xlsx" # לוח ב - יישובים ללא חלוקה פנימית (F, M)
URL_TABLE_A = "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t1.xlsx" # לוח א - רשויות מקומיות (B, H)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_excel_file(url: str, local_path: str) -> str:
    """שומר את הקובץ מקומית כדי למנוע הורדה חוזרת בכל הרצה."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(local_path):
        print(f"📥 מוריד קובץ משרתי הלמ\"ס: {url}")
        with httpx.Client(headers=HEADERS, verify=False, follow_redirects=True, timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(resp.content)
    else:
        print(f"📂 טוען קובץ שמור: {local_path}")
    return local_path

def get_socio_economic_cluster(semel_yishuv: int, stat_area: int) -> dict:
    # ---------------------------------------------------------
    # שלב 1: חיפוש בלוח ג' (עמודות B=סמל יישוב, G=אזור סטטיסטי, K=דירוג)
    # ---------------------------------------------------------
    file_c = load_excel_file(URL_TABLE_C, "data/table_c_divisions.xlsx")
    df_c = pd.read_excel(file_c, usecols="B,G,K", header=None)
    df_c.columns = ['semel_yishuv', 'stat_area', 'rank']
    df_c['semel_yishuv'] = pd.to_numeric(df_c['semel_yishuv'], errors='coerce')
    df_c['stat_area'] = pd.to_numeric(df_c['stat_area'], errors='coerce')
    df_c['rank'] = pd.to_numeric(df_c['rank'], errors='coerce')
    df_c = df_c.dropna()

    match_c = df_c[(df_c['semel_yishuv'] == semel_yishuv) & (df_c['stat_area'] == stat_area)]
    if not match_c.empty:
        return {
            "found": True,
            "source": "לוח ג' (יישובים עם חלוקה פנימית)",
            "semel_yishuv": semel_yishuv,
            "stat_area": stat_area,
            "rank": int(match_c.iloc[0]['rank'])
        }

    # ---------------------------------------------------------
    # שלב 2: חיפוש בלוח ב' (עמודות F=סמל יישוב, M=דירוג)
    # ---------------------------------------------------------
    print(f"⚠️ לא נמצא בלוח ג'. עובר לבדיקה בלוח ב' עבור יישוב {semel_yishuv}...")
    file_b = load_excel_file(URL_TABLE_B, "data/table_b_no_divisions.xlsx")
    df_b = pd.read_excel(file_b, usecols="F,M", header=None)
    df_b.columns = ['semel_yishuv', 'rank']
    df_b['semel_yishuv'] = pd.to_numeric(df_b['semel_yishuv'], errors='coerce')
    df_b['rank'] = pd.to_numeric(df_b['rank'], errors='coerce')
    df_b = df_b.dropna()

    match_b = df_b[df_b['semel_yishuv'] == semel_yishuv]
    if not match_b.empty:
        return {
            "found": True,
            "source": "לוח ב' (יישובים ללא חלוקה פנימית)",
            "semel_yishuv": semel_yishuv,
            "stat_area": stat_area,
            "rank": int(match_b.iloc[0]['rank'])
        }

    # ---------------------------------------------------------
    # שלב 3: חיפוש בלוח א' (עמודות B=סמל יישוב, H=דירוג)
    # ---------------------------------------------------------
    print(f"⚠️ לא נמצא בלוח ב'. עובר לבדיקה בלוח א' עבור יישוב {semel_yishuv}...")
    file_a = load_excel_file(URL_TABLE_A, "data/table_a_authorities.xlsx")
    df_a = pd.read_excel(file_a, usecols="B,H", header=None)
    df_a.columns = ['semel_yishuv', 'rank']
    df_a['semel_yishuv'] = pd.to_numeric(df_a['semel_yishuv'], errors='coerce')
    df_a['rank'] = pd.to_numeric(df_a['rank'], errors='coerce')
    df_a = df_a.dropna()

    match_a = df_a[df_a['semel_yishuv'] == semel_yishuv]
    if not match_a.empty:
        return {
            "found": True,
            "source": "לוח א' (רשויות מקומיות)",
            "semel_yishuv": semel_yishuv,
            "stat_area": stat_area,
            "rank": int(match_a.iloc[0]['rank'])
        }

    return {
        "found": False,
        "error": f"היישוב {semel_yishuv} או האזור {stat_area} לא נמצאו באף אחד משלושת לוחות הלמ\"ס (א', ב', ג')."
    }

if __name__ == "__main__":
    res = get_socio_economic_cluster(semel_yishuv=5000, stat_area=533)
    print("\nתוצאה:", res)