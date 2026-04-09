import streamlit as st
import requests
from datetime import datetime, timedelta
import streamlit.components.v1 as components

API_URL = "https://tom-travel-app.onrender.com"
TIME_OPTIONS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

st.set_page_config(page_title="旅遊小幫手 App", page_icon="✈️", layout="centered")

# --- 1. 取得設定與成員名單 ---
try:
    settings = requests.get(f"{API_URL}/settings/").json()
    members_res = requests.get(f"{API_URL}/members/").json()
    MEMBER_NAMES = [m['name'] for m in members_res]
except:
    st.error("🚨 無法連線到後端！請確認 FastAPI 伺服器 (main.py) 是否已啟動。")
    st.stop()

trip_title = settings.get("trip_title")
start_dt = datetime.strptime(settings.get("start_date"), "%Y-%m-%d")
end_dt = datetime.strptime(settings.get("end_date"), "%Y-%m-%d")

st.title(f"✈️ {trip_title}")

with st.expander("⚙️ 編輯旅程設定"):
    new_title = st.text_input("旅程名稱", value=trip_title)
    col_d1, col_d2 = st.columns(2)
    with col_d1: new_start = st.date_input("開始日期", start_dt)
    with col_d2: new_end = st.date_input("結束日期", end_dt)
    if st.button("💾 儲存設定"):
        requests.post(f"{API_URL}/settings/", params={"trip_title": new_title, "start_date": new_start.strftime("%Y-%m-%d"), "end_date": new_end.strftime("%Y-%m-%d")})
        st.rerun()

delta = new_end - new_start if 'new_start' in locals() else end_dt - start_dt
TRIP_DATES = [(start_dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(delta.days + 1)]

tab_itinerary, tab_overview, tab_expense = st.tabs(["📅 每日編輯", "🗺️ 行程總覽", "💰 記帳與結算"])

# --- 行程表分頁 (保持不變) ---
with tab_itinerary:
    selected_date = st.selectbox("📅 請選擇日期：", TRIP_DATES)
    all_itineraries = requests.get(f"{API_URL}/itinerary/").json().get("data", [])
    day_itineraries = [item for item in all_itineraries if item.get("date") == selected_date]
    if not day_itineraries:
        st.info("這天還沒有安排行程。")
    else:
        for item in day_itineraries:
            with st.container(border=True):
                col1, col2 = st.columns([0.75, 0.25])
                with col1:
                    st.markdown(f"### 📍 {item['location']}")
                    st.write(f"🕒 **{item['start_time']} - {item['end_time']}**")
                    if item.get('notes'): st.caption(f"📝 {item['notes']}")
                with col2:
                    c_edit, c_del = st.columns(2)
                    with c_del:
                        if st.button("🗑️", key=f"del_i_{item['id']}"):
                            requests.delete(f"{API_URL}/itinerary/{item['id']}"); st.rerun()
                    with c_edit:
                        with st.popover("✏️"):
                            with st.form(f"edit_{item['id']}", border=False):
                                n_loc = st.text_input("地點", value=item['location'])
                                n_map = st.text_input("Map 網址", value=item.get('map_url', ''))
                                tc1, tc2 = st.columns(2)
                                n_t1 = tc1.selectbox("開始", TIME_OPTIONS, index=TIME_OPTIONS.index(item['start_time']) if item['start_time'] in TIME_OPTIONS else 0)
                                n_t2 = tc2.selectbox("結束", TIME_OPTIONS, index=TIME_OPTIONS.index(item['end_time']) if item['end_time'] in TIME_OPTIONS else 0)
                                n_notes = st.text_area("備註", value=item.get('notes', ''))
                                if st.form_submit_button("儲存"):
                                    requests.put(f"{API_URL}/itinerary/{item['id']}", json={"date": item['date'], "start_time": n_t1, "end_time": n_t2, "location": n_loc, "notes": n_notes, "map_url": n_map})
                                    st.rerun()
                f_link = item.get('map_url') if item.get('map_url') else f"https://www.google.com/maps/search/?api=1&query={item['location']}"
                st.markdown(f"[🗺️ 導航]({f_link})")
                components.html(f"""<iframe width="100%" height="200" frameborder="0" src="https://maps.google.com/maps?q={item['location']}&hl=zh-TW&z=14&output=embed"></iframe>""", height=200)

    st.divider()
    with st.form("add_itinerary", clear_on_submit=True):
        loc = st.text_input("地點名稱")
        c_map = st.text_input("自訂 Map 網址 (選填)")
        c1, c2 = st.columns(2)
        t1 = c1.selectbox("開始", TIME_OPTIONS, index=18)
        t2 = c2.selectbox("結束", TIME_OPTIONS, index=20)
        notes = st.text_area("備註")
        if st.form_submit_button("送出"):
            if loc: requests.post(f"{API_URL}/itinerary/", json={"date": selected_date, "start_time": t1, "end_time": t2, "location": loc, "notes": notes, "map_url": c_map}); st.rerun()

# ------------------------------------------
# 分頁 2：行程總覽 ✨ (支援一鍵匯出 PDF)
# ------------------------------------------
with tab_overview:
    # --- 🖨️ 魔法列印樣式 (隱藏不需要列印的網頁元素) ---
    st.markdown("""
        <style>
        @media print {
            /* 隱藏網頁頂部選單、側邊欄、以及匯出按鈕本身 */
            header, .stApp > header, [data-testid="stSidebar"], iframe {
                display: none !important;
            }
            /* 讓內容頂天，移除多餘留白 */
            .main .block-container {
                max-width: 100%;
                padding-top: 0rem !important;
            }
            /* 把背景變成純白，確保印出來好看 */
            body { background-color: white !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    c_title, c_btn = st.columns([0.7, 0.3])
    with c_title:
        st.subheader(f"🗺️ {trip_title} - 全程總覽")
    
    with c_btn:
        # --- 🖨️ 匯出按鈕 (呼叫瀏覽器的列印/存檔功能) ---
        components.html("""
            <div style="text-align: right; padding-top: 10px;">
                <button onclick="window.parent.print()" 
                        style="background-color: #FF4B4B; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    🖨️ 匯出 PDF / 列印
                </button>
            </div>
        """, height=60)

    # 呼叫 API 取得「所有」行程
    all_itineraries = requests.get(f"{API_URL}/itinerary/").json().get("data", [])
    
    if not all_itineraries:
        st.info("目前還沒有任何行程喔！請到「每日編輯」新增。")
    else:
        grouped_itineraries = {}
        for item in all_itineraries:
            date_key = item['date']
            if date_key not in grouped_itineraries:
                grouped_itineraries[date_key] = []
            grouped_itineraries[date_key].append(item)
            
        for date_key in sorted(grouped_itineraries.keys()):
            with st.expander(f"📌 {date_key}", expanded=True):
                for item in grouped_itineraries[date_key]:
                    final_link = item.get('map_url') if item.get('map_url') else f"https://www.google.com/maps/search/?api=1&query={item['location']}"
                    
                    c_info, c_map = st.columns([0.85, 0.15])
                    with c_info:
                        st.markdown(f"**{item['start_time']} - {item['end_time']}** | 📍 **{item['location']}**")
                        if item.get('notes'):
                            st.caption(f"📝 {item['notes']}")
                    with c_map:
                        st.link_button("🗺️ 地圖", final_link)
                    
                    st.divider()
# --- 💰 記帳與結算分頁 (新增成員管理功能) ---
with tab_expense:
    # 1. 成員管理區塊 ✨
    with st.expander("👥 管理行程成員"):
        col_m1, col_m2 = st.columns([0.7, 0.3])
        new_m = col_m1.text_input("新增成員名稱", placeholder="例如：小明")
        if col_m2.button("➕ 新增成員"):
            if new_m:
                requests.post(f"{API_URL}/members/", json={"name": new_m})
                st.rerun()
        
        st.write("**目前名單：**")
        for m in members_res:
            mc1, mc2 = st.columns([0.8, 0.2])
            mc1.write(f"👤 {m['name']}")
            if mc2.button("🗑️", key=f"del_m_{m['id']}"):
                requests.delete(f"{API_URL}/members/{m['id']}")
                st.rerun()

    st.divider()

    if not MEMBER_NAMES:
        st.warning("請先在上方「管理行程成員」中新增參與者，才能開始記帳喔！")
    else:
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("➕ 新增花費")
            with st.form("add_expense", clear_on_submit=True):
                i_name = st.text_input("項目名稱")
                amt = st.number_input("總金額", min_value=0, step=100)
                payer = st.selectbox("付款人", MEMBER_NAMES)
                shared = st.multiselect("分攤者", MEMBER_NAMES, default=MEMBER_NAMES)
                if st.form_submit_button("新增帳單"):
                    if i_name and amt > 0 and shared:
                        requests.post(f"{API_URL}/expenses/", json={"item_name": i_name, "amount": amt, "payer": payer, "shared_by": shared})
                        st.rerun()

        with col_r:
            st.subheader("🧾 結算摘要")
            settlement = requests.get(f"{API_URL}/settlement/").json().get("data", [])
            for line in settlement: st.markdown(f"**{line}**")

    st.divider()
    st.subheader("📜 歷史花費")
    expenses = requests.get(f"{API_URL}/expenses/").json().get("data", [])
    for exp in expenses:
        with st.container(border=True):
            ec1, ec2 = st.columns([0.9, 0.1])
            ec1.write(f"🏷️ **{exp['item_name']}** - ${exp['amount']}")
            ec1.caption(f"付款人：{exp['payer']} | 分攤者：{', '.join(exp['shared_by'])}")
            if ec2.button("🗑️", key=f"del_e_{exp['id']}"):
                requests.delete(f"{API_URL}/expenses/{exp['id']}"); st.rerun()
