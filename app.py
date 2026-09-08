import streamlit as st
import requests
import pandas as pd
from datetime import datetime
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
            header = data[0]
            rows = data[1:]
            df = pd.DataFrame(rows, columns=header)
            
            # Konversi kolom Jumlah ke angka
            if "Jumlah" in df.columns:
                df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
            
            # Pembacaan tanggal yang fleksibel & aman
            if "Tanggal" in df.columns:
                df["_dt"] = pd.to_datetime(df["Tanggal"], format="mixed", errors="coerce")
            
            filter_periode = st.selectbox(
                "📅 Pilih Periode Tampilan:",
                ["Semua", "Bulan Ini", "Minggu Ini", "Custom (Rentang Tanggal)"]
            )
            
            wib = pytz.timezone('Asia/Jakarta')
            now = datetime.now(wib)
            
            has_valid_dt = "_dt" in df.columns and df["_dt"].notnull().any()
            
            if filter_periode == "Bulan Ini" and has_valid_dt:
                df_filtered = df[(df["_dt"].dt.month == now.month) & (df["_dt"].dt.year == now.year)].copy()
            
            elif filter_periode == "Minggu Ini" and has_valid_dt:
                current_year, current_week, _ = now.isocalendar()
                iso_cal = df["_dt"].dt.isocalendar()
                df_filtered = df[(iso_cal.week == current_week) & (iso_cal.year == current_year)].copy()
            
            elif filter_periode == "Custom (Rentang Tanggal)" and has_valid_dt:
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
            
            # Hapus kolom bantuan _dt
            df_display = df_filtered.drop(columns=["_dt"], errors="ignore")
            
            # KUNCI URUTAN KOLOM
            col_kategori = "Katagori" if "Katagori" in df_display.columns else "Kategori"
            target_order = ["Tanggal", col_kategori, "Jumlah", "Keterangan"]
            existing_cols = [c for c in target_order if c in df_display.columns]
            other_cols = [c for c in df_display.columns if c not in existing_cols]
            df_display = df_display[existing_cols + other_cols]
            
            # 1. Total Keseluruhan
            total = df_display["Jumlah"].sum() if "Jumlah" in df_display.columns else 0
            st.metric(label=f"Total Pengeluaran ({filter_periode})", value=f"Rp {total:,.0f}")
            
            st.divider()

            # --- 2. LAPORAN PER KATEGORI ---
            if col_kategori in df_display.columns and not df_display.empty:
                st.write("### 🏷️ Total per Kategori (Terbesar - Terkecil)")
                
                df_kat = df_display.groupby(col_kategori)["Jumlah"].sum().reset_index()
                df_kat = df_kat.sort_values(by="Jumlah", ascending=False)
                
                df_kat_formatted = df_kat.copy()
                df_kat_formatted["Total Pengeluaran"] = df_kat_formatted["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
                df_kat_formatted = df_kat_formatted.drop(columns=["Jumlah"])
                
                st.data_editor(
                    df_kat_formatted,
                    use_container_width=True,
                    hide_index=True,
                    disabled=True
                )
                
                st.divider()

            # --- 3. RINCIAN PENGELUARAN DETAIL ---
            st.write("### 📝 Rincian Pengeluaran Detail")
            
            df_detail = df_display.copy()
            if "Jumlah" in df_detail.columns:
                df_detail["Jumlah"] = df_detail["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
            
            # Tampilkan tabel detail dengan lebar kolom yang ditentukan agar bisa di-scroll samping
            st.dataframe(
                df_detail, 
                hide_index=True,
                column_config={
                    "Tanggal": st.column_config.TextColumn("Tanggal", width="medium"),
                    col_kategori: st.column_config.TextColumn(col_kategori, width="medium"),
                    "Jumlah": st.column_config.TextColumn("Jumlah", width="small"),
                    "Keterangan": st.column_config.TextColumn("Keterangan", width="large"),
                }
            )
            
        elif isinstance(data, list) and len(data) <= 1:
            st.info("Belum ada data pengeluaran di Google Sheets.")
            
    except requests.exceptions.Timeout:
        st.error("Server Google Apps Script lambat merespons. Silakan klik '🔄 Refresh Data' di atas.")
    except Exception as e:
        st.error(f"Gagal mengambil data dari Google Sheets. Error: {e}")
