import os
import httpx
import pandas as pd

class EligibilityAgent:
    def __init__(self, data_dir="data"):
        """
        אתחול הסוכן: יצירת תיקיית נתונים וטעינת כל לוחות הלמ"ס לזיכרון (DataFrames).
        """
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        self.urls = {
            "socio_c": "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t4.xlsx",
            "socio_b": "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t3.xlsx",
            "socio_a": "https://www.cbs.gov.il/he/mediarelease/doclib/2024/230/24_24_230t1.xlsx",
            "periphery": "https://www.cbs.gov.il/he/publications/DocLib/2023/1917/table_02.xlsx"
        }
        
        self._load_all_data()

    def _download_if_needed(self, url: str, filename: str) -> str:
        local_path = os.path.join(self.data_dir, filename)
        if not os.path.exists(local_path):
            with httpx.Client(headers=self.headers, verify=False, follow_redirects=True, timeout=30.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(resp.content)
        return local_path

    def _load_all_data(self):
        """קורא את קובצי האקסל ומכין את ה-DataFrames."""
        # 1. מדד חברתי-כלכלי: לוח ג' (B: סמל יישוב, E: אשכול יישוב, G: אזור סטטיסטי, K: אשכול אזור)
        path_c = self._download_if_needed(self.urls["socio_c"], "table_c_divisions.xlsx")
        self.df_socio_c = pd.read_excel(
            path_c, 
            usecols="B,E,G,K", 
            header=None, 
            names=['semel_yishuv', 'ses_locality', 'stat_area', 'ses_area']
        )
        self.df_socio_c = self.df_socio_c.apply(pd.to_numeric, errors='coerce').dropna()

        # 2. מדד חברתי-כלכלי: לוח ב' (יישובים ללא חלוקה - היישוב הוא גם האזור)
        path_b = self._download_if_needed(self.urls["socio_b"], "table_b_no_divisions.xlsx")
        self.df_socio_b = pd.read_excel(
            path_b, 
            usecols="F,M", 
            header=None, 
            names=['semel_yishuv', 'rank']
        )
        self.df_socio_b = self.df_socio_b.apply(pd.to_numeric, errors='coerce').dropna()

        # 3. מדד חברתי-כלכלי: לוח א' (רשויות מקומיות - היישוב הוא גם האזור)
        path_a = self._download_if_needed(self.urls["socio_a"], "table_a_authorities.xlsx")
        self.df_socio_a = pd.read_excel(
            path_a, 
            usecols="B,H", 
            header=None, 
            names=['semel_yishuv', 'rank']
        )
        self.df_socio_a = self.df_socio_a.apply(pd.to_numeric, errors='coerce').dropna()

        # 4. מדד פריפריאלי
        path_periphery = self._download_if_needed(self.urls["periphery"], "table_periphery.xlsx")
        self.df_periphery = pd.read_excel(
            path_periphery, 
            usecols="D,P", 
            header=None, 
            names=['semel_yishuv', 'rank']
        )
        self.df_periphery = self.df_periphery.apply(pd.to_numeric, errors='coerce').dropna()

    def _get_socio_ranks(self, semel_yishuv: int, stat_area: int):
        """
        שולף את SES_AREA ו-SES_LOCALITY לפי ההיררכיה: לוח ג' -> לוח ב' -> לוח א'.
        מחזיר טאפל: (ses_area, ses_locality, source)
        """
        # חיפוש בלוח ג' (הבחנה בין אשכול האזור לאשכול היישוב)
        match_c = self.df_socio_c[
            (self.df_socio_c['semel_yishuv'] == semel_yishuv) & 
            (self.df_socio_c['stat_area'] == stat_area)
        ]
        if not match_c.empty:
            row = match_c.iloc[0]
            return int(row['ses_area']), int(row['ses_locality']), "לוח ג' (יישובים עם חלוקה)"
        
        # חיפוש בלוח ב' (אין חלוקה, האזור והיישוב זהים)
        match_b = self.df_socio_b[self.df_socio_b['semel_yishuv'] == semel_yishuv]
        if not match_b.empty:
            rank = int(match_b.iloc[0]['rank'])
            return rank, rank, "לוח ב' (יישובים ללא חלוקה)"
            
        # חיפוש בלוח א' (רשויות מקומיות)
        match_a = self.df_socio_a[self.df_socio_a['semel_yishuv'] == semel_yishuv]
        if not match_a.empty:
            rank = int(match_a.iloc[0]['rank'])
            return rank, rank, "לוח א' (רשויות מקומיות)"
            
        return None, None, None

    def _get_periphery_rank(self, semel_yishuv: int):
        """שולף את PERIPHERY_LOCALITY."""
        match_p = self.df_periphery[self.df_periphery['semel_yishuv'] == semel_yishuv]
        if not match_p.empty:
            return int(match_p.iloc[0]['rank'])
        return None

    def evaluate(self, semel_yishuv: int, stat_area: int) -> dict:
        """
        חישוב זכאות לפי הנוסחה החדשה:
        ELIGIBLE = (SES_AREA ∈ {1..5}) OR (PERIPHERY_LOCALITY ∈ {1..5} AND SES_LOCALITY ∉ {9,10})
        """
        ses_area, ses_locality, socio_source = self._get_socio_ranks(semel_yishuv, stat_area)
        periphery_locality = self._get_periphery_rank(semel_yishuv)

        # 1. זכאות חברתית-כלכלית באזור הסטטיסטי (1-5)
        ses_area_eligible = ses_area is not None and 1 <= ses_area <= 5
        
        # 2. זכאות פריפריאלית ביישוב (1-5) בתנאי שאשכול היישוב אינו 9 או 10
        periphery_eligible = False
        if periphery_locality is not None and 1 <= periphery_locality <= 5:
            if ses_locality is not None and ses_locality not in [9, 10]:
                periphery_eligible = True

        is_eligible = ses_area_eligible or periphery_eligible

        # נימוקים
        reasons = []
        if ses_area_eligible:
            reasons.append(f"זכאות אזורית: אשכול חברתי-כלכלי באזור {ses_area} (1-5)")
        if periphery_eligible:
            reasons.append(f"זכאות פריפריאלית: דירוג {periphery_locality} (1-5) ואשכול יישובי {ses_locality} (אינו 9-10)")
        
        if not is_eligible:
            if (periphery_locality is not None and 1 <= periphery_locality <= 5) and (ses_locality in [9, 10]):
                reasons.append(f"נפסל: פריפריאליות מזכה ({periphery_locality}), אך מוחרג עקב אשכול חברתי-כלכלי יישובי גבוה ({ses_locality})")
            else:
                reasons.append("האזור והיישוב אינם עומדים בתנאי הסף להטבה")

        # החזרת מפתח אחיד בעברית ובאנגלית למניעת תקלות חילוץ
        return {
            "is_eligible": is_eligible,
            "socio_cluster": ses_area if ses_area is not None else "לא ידוע",
            "periphery_index": periphery_locality if periphery_locality is not None else "לא ידוע",
            "reasons": reasons,
            "metadata": {
                "semel_yishuv": semel_yishuv,
                "stat_area": stat_area,
                "ses_area": ses_area,
                "ses_locality": ses_locality,
                "periphery_locality": periphery_locality,
                "socio_source": socio_source,
                "אשכול_חברתי_כלכלי": ses_area if ses_area is not None else "לא ידוע",
                "מדד_פריפריאליות": periphery_locality if periphery_locality is not None else "לא ידוע"
            }
        }