import streamlit as st
from orchestrator import process_eligibility

# ==========================================
# 1. הגדרות עמוד בסיסיות
# ==========================================
st.set_page_config(
    page_title="מנוע בדיקת זכאות",
    page_icon="🚌",
    layout="centered"
)

# ==========================================
# 2. עיצוב הממשק - יישור לימין (RTL)
# ==========================================
st.markdown("""
    <style>
    .stApp { text-align: right; direction: rtl; }
    .stTextInput input { text-align: right; }
    div[data-testid="stMarkdownContainer"] { text-align: right; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. תצוגת ממשק המשתמש (UI)
# ==========================================
st.title("🚌 מנוע בדיקת זכאות לפרופיל גיאוגרפי")

# שדה קלט טקסט
raw_address = st.text_input("הזן כתובת מלאה", placeholder="למשל: הפלמ\"ח 14 ירוחם", label_visibility="collapsed")

# כפתור שליחה מעוצב
if st.button("בדיקת זכאות", key="check_eligibility_btn", type="primary", use_container_width=True):
    address_clean = raw_address.strip()
    
    # --- ולידציות של קלט חסר או ארוך מדי ---
    if not address_clean:
        st.error("יש להזין כתובת.")
        st.stop() # עוצר את המשך הריצה
        
    if len(address_clean) > 300:
        st.error("הכתובת יכולה להכיל עד 300 תווים.")
        st.stop() # עוצר את המשך הריצה

    # --- הפעלת מנוע הבדיקה ---
    with st.spinner("בודק זכאות במערכת... (נא להמתין)"):
        # קריאה לאורקסטרטור - בלוגיקה שמתחת לפני השטח הוא גם מדפיס לך לוגים לטרמינל
        final_response = process_eligibility(address_clean)
        
        status = final_response.get("status")
        
        st.divider()
        
        # --- תצוגת התוצאה למשתמש ---
        if status == "ELIGIBLE":
            st.success("✅ **זכאי! הכתובת נמצאה זכאית להטבה.**")
        elif status == "NOT_ELIGIBLE":
            st.error("⛔ **לא זכאי. הכתובת אינה זכאית להטבה.**")
        else:
            # מקרים כמו: כתובת לא נמצאה, עמומה מידי, או שגיאת מערכת
            st.warning(f"⚠️ {final_response.get('message', 'שגיאה בתהליך')}")