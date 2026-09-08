import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import calendar
import pytz

# URL Web App Google Apps Script Anda
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby8F7dcFUCMy7Dk-49c-zqV1xxEudo_3zGA_AJvfze3pbrAgQPUleaQbSwEq8TrSlzC/exec"

st.set_page_config(page_title="Catatan Pengeluaran", page_icon="💰", layout="centered")

st.title("💰 Catatan Pengeluaran")

tab1, tab2 = st.tabs(["➕ Tambah Pengeluaran", "📊 Lihat Data & Laporan"])

# --- TAB 1: FORM INPUT ---
with tab1:
    st.subheader("Input Pengeluaran Baru")
    with st.form("form_pengeluaran", clear_on_submit=True):
        input_tanggal = st.date_input("Tanggal", datetime.now())
        kategori = st.selectbox(
            "Kategori", 
            ["Belanja bulanan", "Transportasi", "Kebutuhan Rumah", "Hiburan / Jajanan", "Tagihan & Pulsa", "Lainnya"]
        )
        jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=1000, format="%d")
        keterangan = st.text_input("Keterangan (Opsional)")
        
        submitted = st.form_submit_button("Simpan Data")
        
        if submitted:
            if jumlah <= 0:
                st.warning("Jumlah pengeluaran harus lebih besar dari 0.")
            else:
                wib = pytz.timezone('Asia/Jakarta')
                now_wib = datetime.now(wib)
                tanggal_jam_str = f"{input_tanggal.strftime('%Y-%m-%d')} {now_wib.strftime('%H:%M')}"
                
                payload = {
                    "tanggal": tanggal_jam_str,
                    "kategori": kategori,
                    "jumlah": jumlah,
                    "keterangan": keterangan
                }
                try:
                    res = requests.post(WEB_APP_URL, json=payload, timeout=30)
                    if res.status_code == 200:
                        st.success("✓ Catatan berhasil tersimpan ke Google Sheets!")
                        st.cache_data.clear() # Hapus cache agar data baru langsung terbaca
                    else:
                        st.error("Gagal menyimpan data ke Google Sheets.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan koneksi: {e}")

# --- TAB 2: RIWAYAT DATA & LAPORAN ---
with tab2:
    st.subheader("Riwayat & Laporan Pengeluaran")
    
    # Pemetaan Ikon Sesuai Kategori
    ICON_KATEGORI = {
        "Belanja bulanan": "🛒",
        "Transportasi": "🚗",
        "Kebutuhan Rumah": "🏠",
        "Hiburan / Jajanan": "🍿",
        "Tagihan & Pulsa": "💡",
        "Lainnya": "📦"
    }
    
    # Fungsi fetch data menggunakan CACHE
    @st.cache_data(ttl=120)
    def fetch_sheet_data():
        response = requests.get(WEB_APP_URL, timeout=30)
        return response.json()

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
        
    try:
        with st.spinner("Mengambil data dari Google Sheets..."):
            data = fetch_sheet_data()

        if isinstance(data, list) and len(data) > 1:
            header = [str(col).strip() for col in data[0]] # Hapus spasi tak terlihat pada header
            rows = data[1:]
            df = pd.DataFrame(rows, columns=header)
            
            # Normalisasi Nama Kolom (Huruf Kecil ke Standar Utama)
            col_map = {}
            for c in df.columns:
                c_clean = c.strip().lower()
                if c_clean in ["tanggal", "tgl"]:
                    col_map[c] = "Tanggal"
                elif c_clean in ["kategori", "katagori"]:
                    col_map[c] = "Kategori"
                elif c_clean in ["jumlah", "nominal", "total"]:
                    col_map[c] = "Jumlah"
                elif c_clean in ["keterangan", "ket", "notes"]:
                    col_map[c] = "Keterangan"
            
            df = df.rename(columns=col_map)
            
            # Pastikan Kolom Utama Selalu Ada
            for req_col in ["Tanggal", "Kategori", "Jumlah", "Keterangan"]:
                if req_col not in df.columns:
                    df[req_col] = ""

            # Konversi kolom Jumlah ke angka
            df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
            
            # Pembacaan tanggal yang fleksibel & aman
            df["_dt"] = pd.to_datetime(df["Tanggal"], format="mixed", errors="coerce")
            
            # --- BAGIAN 0: TAMPILKAN TRANSAKSI TERBARU (5 TERAKHIR) ---
            st.write("### 🕒 Transaksi Terbaru (5 Terakhir)")
            df_recent = df.copy()
            if "_dt" in df_recent.columns and df_recent["_dt"].notnull().any():
                df_recent = df_recent.sort_values(by="_dt", ascending=False)
            
            df_recent_top5 = df_recent.head(5).copy()
            if not df_recent_top5.empty:
                df_recent_top5["Jumlah"] = df_recent_top5["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
                df_recent_top5["Kategori"] = df_recent_top5["Kategori"].apply(
                    lambda x: f"{ICON_KATEGORI.get(x, '📌')} {x}"
                )
                df_recent_display = df_recent_top5.reindex(columns=["Tanggal", "Kategori", "Jumlah", "Keterangan"]).fillna("-")
                
                st.dataframe(
                    df_recent_display, 
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Tanggal": st.column_config.TextColumn("Tanggal", width="medium"),
                        "Kategori": st.column_config.TextColumn("Kategori", width="medium"),
                        "Jumlah": st.column_config.TextColumn("Jumlah", width="small"),
                        "Keterangan": st.column_config.TextColumn("Keterangan", width="large"),
                    }
                )
            st.divider()

            # --- PERHITUNGAN TANGGAL & HARI PERIODE ---
            wib = pytz.timezone('Asia/Jakarta')
            now = datetime.now(wib)
            
            current_month = now.month
            current_year = now.year
            
            if current_month == 1:
                last_month = 12
                last_month_year = current_year - 1
            else:
                last_month = current_month - 1
                last_month_year = current_year
                
            nama_bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]
            curr_month_str = nama_bulan[current_month - 1]
            last_month_str = nama_bulan[last_month - 1]
            
            days_in_curr_month = calendar.monthrange(current_year, current_month)[1]
            days_in_last_month = calendar.monthrange(last_month_year, last_month)[1]
            
            opt_m1_curr = f"Minggu ke-1 (1 - 7 {curr_month_str})"
            opt_m2_curr = f"Minggu ke-2 (8 - 14 {curr_month_str})"
            opt_m3_curr = f"Minggu ke-3 (15 - 21 {curr_month_str})"
            opt_m4_curr = f"Minggu ke-4 (22 - 28 {curr_month_str})"
            opt_m5_curr = f"Minggu ke-5 (29 - {days_in_curr_month} {curr_month_str})"
            
            opt_m1_last = f"Minggu ke-1 (1 - 7 {last_month_str})"
            opt_m2_last = f"Minggu ke-2 (8 - 14 {last_month_str})"
            opt_m3_last = f"Minggu ke-3 (15 - 21 {last_month_str})"
            opt_m4_last = f"Minggu ke-4 (22 - 28 {last_month_str})"
            opt_m5_last = f"Minggu ke-5 (29 - {days_in_last_month} {last_month_str})"
            
            filter_options = [
                "Semua", 
                "--- BULAN INI ---",
                f"Bulan Ini ({curr_month_str} {current_year})", 
                opt_m1_curr, 
                opt_m2_curr, 
                opt_m3_curr, 
                opt_m4_curr, 
                opt_m5_curr, 
                "--- BULAN LALU ---",
                f"Bulan Lalu ({last_month_str} {last_month_year})", 
                opt_m1_last, 
                opt_m2_last, 
                opt_m3_last, 
                opt_m4_last, 
                opt_m5_last, 
                "--- CUSTOM ---",
                "Custom (Rentang Tanggal)"
            ]
            
            filter_periode = st.selectbox("📅 Pilih Periode Laporan:", filter_options)
            
            has_valid_dt = "_dt" in df.columns and df["_dt"].notnull().any()
            
            # Logika Pemfilteran Laporan
            if has_valid_dt:
                is_bulan_ini = (df["_dt"].dt.month == current_month) & (df["_dt"].dt.year == current_year)
                is_bulan_lalu = (df["_dt"].dt.month == last_month) & (df["_dt"].dt.year == last_month_year)
                
                if filter_periode == f"Bulan Ini ({curr_month_str} {current_year})":
                    df_filtered = df[is_bulan_ini].copy()
                elif filter_periode == opt_m1_curr:
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 1) & (df["_dt"].dt.day <= 7)].copy()
                elif filter_periode == opt_m2_curr:
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 8) & (df["_dt"].dt.day <= 14)].copy()
                elif filter_periode == opt_m3_curr:
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 15) & (df["_dt"].dt.day <= 21)].copy()
                elif filter_periode == opt_m4_curr:
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 22) & (df["_dt"].dt.day <= 28)].copy()
                elif filter_periode == opt_m5_curr:
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 29)].copy()
                
                elif filter_periode == f"Bulan Lalu ({last_month_str} {last_month_year})":
                    df_filtered = df[is_bulan_lalu].copy()
                elif filter_periode == opt_m1_last:
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 1) & (df["_dt"].dt.day <= 7)].copy()
                elif filter_periode == opt_m2_last:
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 8) & (df["_dt"].dt.day <= 14)].copy()
                elif filter_periode == opt_m3_last:
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 15) & (df["_dt"].dt.day <= 21)].copy()
                elif filter_periode == opt_m4_last:
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 22) & (df["_dt"].dt.day <= 28)].copy()
                elif filter_periode == opt_m5_last:
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 29)].copy()
                
                elif filter_periode == "Custom (Rentang Tanggal)":
                    range_tgl = st.date_input(
                        "Pilih Rentang Tanggal (Mulai - Selesai):",
                        value=(datetime.now(), datetime.now()),
                        key="custom_range"
                    )
                    
                    if isinstance(range_tgl, tuple) and len(range_tgl) == 2:
                        tgl_mulai, tgl_selesai = range_tgl
                        start_dt = pd.to_datetime(tgl_mulai)
                        end_dt = pd.to_datetime(tgl_selesai).replace(hour=23, minute=59, second=59)
                        df_filtered = df[(df["_dt"] >= start_dt) & (df["_dt"] <= end_dt)].copy()
                    else:
                        df_filtered = df.copy()
                else:
                    df_filtered = df.copy()
            else:
                df_filtered = df.copy()
            
            df_display = df_filtered.drop(columns=["_dt"], errors="ignore")
            label_periode = filter_periode.replace("-", "").strip()
            
            # --- 1. TOTAL KESELURUHAN PERIODE ---
            total = df_display["Jumlah"].sum()
            st.metric(label=f"Total Pengeluaran ({label_periode})", value=f"Rp {total:,.0f}")
            
            st.divider()

            # --- 2. LAPORAN RINGKASAN PER KATEGORI ---
            if not df_display.empty:
                st.write("### 🏷️ Ringkasan Total per Kategori")
                
                df_kat = df_display.groupby("Kategori")["Jumlah"].sum().reset_index()
                df_kat = df_kat.sort_values(by="Jumlah", ascending=False)
                
                df_kat_formatted = df_kat.copy()
                df_kat_formatted["Kategori"] = df_kat_formatted["Kategori"].apply(
                    lambda x: f"{ICON_KATEGORI.get(x, '📌')} {x}"
                )
                df_kat_formatted["Total Pengeluaran"] = df_kat_formatted["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
                df_kat_formatted = df_kat_formatted.drop(columns=["Jumlah"])
                
                st.data_editor(
                    df_kat_formatted,
                    use_container_width=True,
                    hide_index=True,
                    disabled=True
                )
                
                st.divider()

            # --- 3. RINCIAN PENGELUARAN DETAIL PER KATEGORI ---
            st.write("### 📂 Detail Rincian per Kategori")
            
            if not df_display.empty:
                kategori_list = df_display.groupby("Kategori")["Jumlah"].sum().sort_values(ascending=False).index
                
                for kat in kategori_list:
                    df_sub = df_display[df_display["Kategori"] == kat].copy()
                    sub_total = df_sub["Jumlah"].sum()
                    
                    icon = ICON_KATEGORI.get(kat, "📌")
                    
                    with st.expander(f"{icon} **{kat}** — Total: Rp {sub_total:,.0f} ({len(df_sub)} transaksi)"):
                        df_sub["Jumlah"] = df_sub["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
                        
                        target_columns = ["Tanggal", "Jumlah", "Keterangan"]
                        df_sub_final = df_sub.reindex(columns=target_columns).fillna("-")
                        
                        st.dataframe(
                            df_sub_final, 
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Tanggal": st.column_config.TextColumn("Tanggal", width="medium"),
                                "Jumlah": st.column_config.TextColumn("Jumlah", width="small"),
                                "Keterangan": st.column_config.TextColumn("Keterangan", width="large"),
                            }
                        )
            else:
                st.info("Belum ada rincian data untuk periode ini.")
            
        elif isinstance(data, list) and len(data) <= 1:
            st.info("Belum ada data pengeluaran di Google Sheets.")
            
    except requests.exceptions.Timeout:
        st.error("Server Google Apps Script lambat merespons. Silakan klik '🔄 Refresh Data' di atas.")
    except Exception as e:
        st.error(f"Gagal mengambil data dari Google Sheets. Error: {e}")
