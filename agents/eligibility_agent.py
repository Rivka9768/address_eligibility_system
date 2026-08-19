import os
import httpx
import pandas as pd

class EligibilityAgent:
    def __init__(self, data_dir="data"):
        """
        אתחול הסוכן: יצירת תיקיית נתונים וטעינת כל לוחות הלמ"ס לזיכרון (DataFrames).
        פעולה זו מתבצעת פעם אחת בעליית השרת כדי לחסוך זמן קריאה בדיסק או ברשת.
        """
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # כתובות הלוחות
        self.urls = {
            "socio_c": "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t4.xlsx",
            "socio_b": "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t3.xlsx",
            "socio_a": "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t1.xlsx",
            "periphery": "https://www.cbs.gov.il/he/publications/DocLib/2023/1917/table_02.xlsx"
        }
        
        # טעינת הנתונים למבני נתונים בזיכרון
        self._load_all_data()

    def _download_if_needed(self, url: str, filename: str) -> str:
        """מוריד את הקובץ רק אם הוא עדיין לא שמור מקומית."""
        local_path = os.path.join(self.data_dir, filename)
        if not os.path.exists(local_path):
            with httpx.Client(headers=self.headers, verify=False, follow_redirects=True, timeout=30.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(resp.content)
        return local_path

    def _load_all_data(self):
        """קורא את קובצי האקסל ומכין את ה-DataFrames לשאילתות מהירות."""
        # 1. מדד חברתי-כלכלי: לוח ג' (עם חלוקה לאזורים סטטיסטיים)
        path_c = self._download_if_needed(self.urls["socio_c"], "table_c_divisions.xlsx")
        self.df_socio_c = pd.read_excel(path_c, usecols="B,G,K", header=None, names=['semel_yishuv', 'stat_area', 'rank'])
        self.df_socio_c = self.df_socio_c.apply(pd.to_numeric, errors='coerce').dropna()

        # 2. מדד חברתי-כלכלי: לוח ב' (יישובים ללא חלוקה)
        path_b = self._download_if_needed(self.urls["socio_b"], "table_b_no_divisions.xlsx")
        self.df_socio_b = pd.read_excel(path_b, usecols="F,M", header=None, names=['semel_yishuv', 'rank'])
        self.df_socio_b = self.df_socio_b.apply(pd.to_numeric, errors='coerce').dropna()

        # 3. מדד חברתי-כלכלי: לוח א' (רשויות מקומיות)
        path_a = self._download_if_needed(self.urls["socio_a"], "table_a_authorities.xlsx")
        self.df_socio_a = pd.read_excel(path_a, usecols="B,H", header=None, names=['semel_yishuv', 'rank'])
        self.df_socio_a = self.df_socio_a.apply(pd.to_numeric, errors='coerce').dropna()

        # 4. מדד פריפריאלי
        path_periphery = self._download_if_needed(self.urls["periphery"], "table_periphery.xlsx")
        self.df_periphery = pd.read_excel(path_periphery, usecols="D,P", header=None, names=['semel_yishuv', 'rank'])
        self.df_periphery = self.df_periphery.apply(pd.to_numeric, errors='coerce').dropna()

    def _get_socio_rank(self, semel_yishuv: int, stat_area: int):
        """מבצע שליפה היררכית מהזיכרון: לוח ג' -> לוח ב' -> לוח א'."""
        match_c = self.df_socio_c[(self.df_socio_c['semel_yishuv'] == semel_yishuv) & (self.df_socio_c['stat_area'] == stat_area)]
        if not match_c.empty:
            return int(match_c.iloc[0]['rank']), "לוח ג' (יישובים עם חלוקה)"
        
        match_b = self.df_socio_b[self.df_socio_b['semel_yishuv'] == semel_yishuv]
        if not match_b.empty:
            return int(match_b.iloc[0]['rank']), "לוח ב' (יישובים ללא חלוקה)"
            
        match_a = self.df_socio_a[self.df_socio_a['semel_yishuv'] == semel_yishuv]
        if not match_a.empty:
            return int(match_a.iloc[0]['rank']), "לוח א' (רשויות מקומיות)"
            
        return None, None

    def _get_periphery_rank(self, semel_yishuv: int):
        """שולף את המדד הפריפריאלי מהזיכרון."""
        match_p = self.df_periphery[self.df_periphery['semel_yishuv'] == semel_yishuv]
        if not match_p.empty:
            return int(match_p.iloc[0]['rank'])
        return None

    def evaluate(self, semel_yishuv: int, stat_area: int) -> dict:
        """
        פונקציית הליבה: מקבלת סמל יישוב ואזור סטטיסטי ומחזירה תשובת זכאות סופית.
        """
        # שליפת נתונים
        socio_rank, socio_source = self._get_socio_rank(semel_yishuv, stat_area)
        periphery_rank = self._get_periphery_rank(semel_yishuv)

        # לוגיקת זכאות
        socio_eligible = socio_rank is not None and 1 <= socio_rank <= 5
        
        periphery_eligible = False
        if periphery_rank is not None and 1 <= periphery_rank <= 5:
            # החרגת אשכולות 9-10 במדד החברתי-כלכלי
            if socio_rank not in [9, 10]:
                periphery_eligible = True

        is_eligible = socio_eligible or periphery_eligible

        # הכנת נימוקים
        reasons = []
        if socio_eligible:
            reasons.append(f"זכאות חברתית-כלכלית: אשכול {socio_rank} מתוך 1-5")
        if periphery_eligible:
            reasons.append(f"זכאות פריפריאלית: מדד {periphery_rank} מתוך 1-5")
        
        if not is_eligible:
            if (periphery_rank is not None and 1 <= periphery_rank <= 5) and (socio_rank in [9, 10]):
                reasons.append(f"נפסל: מדד פריפריאלי מזכה ({periphery_rank}), אך מוחרג עקב אשכול חברתי-כלכלי גבוה ({socio_rank})")
            else:
                reasons.append("האזור אינו עומד בתנאי הסף של מדד חברתי-כלכלי (1-5) או מדד פריפריאלי (1-5)")

        return {
            "is_eligible": is_eligible,
            "reasons": reasons,
            "metadata": {
                "semel_yishuv": semel_yishuv,
                "stat_area": stat_area,
                "socio_rank": socio_rank,
                "periphery_rank": periphery_rank,
                "socio_source": socio_source
            }
        }