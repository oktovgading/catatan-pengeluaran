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
            header = data[0]
            rows = data[1:]
            df = pd.DataFrame(rows, columns=header)
            
            # Konversi kolom Jumlah ke angka
            if "Jumlah" in df.columns:
                df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
            
            # Pembacaan tanggal yang fleksibel & aman
            if "Tanggal" in df.columns:
                df["_dt"] = pd.to_datetime(df["Tanggal"], format="mixed", errors="coerce")
            
            # Opsi pilihan periode tampilan (Lengkap: Bulan Ini & Bulan Lalu)
            filter_periode = st.selectbox(
                "📅 Pilih Periode Tampilan:",
                [
                    "Semua", 
                    "--- BULAN INI ---",
                    "Bulan Ini", 
                    "Minggu ke-1 (Bulan Ini)", 
                    "Minggu ke-2 (Bulan Ini)", 
                    "Minggu ke-3 (Bulan Ini)", 
                    "Minggu ke-4 (Bulan Ini)", 
                    "Minggu ke-5 (Bulan Ini)", 
                    "--- BULAN LALU ---",
                    "Bulan Lalu", 
                    "Minggu ke-1 (Bulan Lalu)", 
                    "Minggu ke-2 (Bulan Lalu)", 
                    "Minggu ke-3 (Bulan Lalu)", 
                    "Minggu ke-4 (Bulan Lalu)", 
                    "Minggu ke-5 (Bulan Lalu)", 
                    "--- CUSTOM ---",
                    "Custom (Rentang Tanggal)"
                ]
            )
            
            wib = pytz.timezone('Asia/Jakarta')
            now = datetime.now(wib)
            
            # Perhitungan Tahun & Bulan saat ini vs Bulan Lalu
            current_month = now.month
            current_year = now.year
            
            # Menentukan Bulan Lalu dan Tahunnya (jika bulan sekarang Januari, bulan lalu adalah Desember tahun sebelumnya)
            if current_month == 1:
                last_month = 12
                last_month_year = current_year - 1
            else:
                last_month = current_month - 1
                last_month_year = current_year
            
            has_valid_dt = "_dt" in df.columns and df["_dt"].notnull().any()
            
            # Logika Pemfilteran
            if has_valid_dt:
                is_bulan_ini = (df["_dt"].dt.month == current_month) & (df["_dt"].dt.year == current_year)
                is_bulan_lalu = (df["_dt"].dt.month == last_month) & (df["_dt"].dt.year == last_month_year)
                
                # --- BULAN INI ---
                if filter_periode == "Bulan Ini":
                    df_filtered = df[is_bulan_ini].copy()
                elif filter_periode == "Minggu ke-1 (Bulan Ini)":
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 1) & (df["_dt"].dt.day <= 7)].copy()
                elif filter_periode == "Minggu ke-2 (Bulan Ini)":
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 8) & (df["_dt"].dt.day <= 14)].copy()
                elif filter_periode == "Minggu ke-3 (Bulan Ini)":
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 15) & (df["_dt"].dt.day <= 21)].copy()
                elif filter_periode == "Minggu ke-4 (Bulan Ini)":
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 22) & (df["_dt"].dt.day <= 28)].copy()
                elif filter_periode == "Minggu ke-5 (Bulan Ini)":
                    df_filtered = df[is_bulan_ini & (df["_dt"].dt.day >= 29)].copy()
                
                # --- BULAN LALU ---
                elif filter_periode == "Bulan Lalu":
                    df_filtered = df[is_bulan_lalu].copy()
                elif filter_periode == "Minggu ke-1 (Bulan Lalu)":
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 1) & (df["_dt"].dt.day <= 7)].copy()
                elif filter_periode == "Minggu ke-2 (Bulan Lalu)":
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 8) & (df["_dt"].dt.day <= 14)].copy()
                elif filter_periode == "Minggu ke-3 (Bulan Lalu)":
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 15) & (df["_dt"].dt.day <= 21)].copy()
                elif filter_periode == "Minggu ke-4 (Bulan Lalu)":
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 22) & (df["_dt"].dt.day <= 28)].copy()
                elif filter_periode == "Minggu ke-5 (Bulan Lalu)":
                    df_filtered = df[is_bulan_lalu & (df["_dt"].dt.day >= 29)].copy()
                
                # --- CUSTOM ---
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
            
            # Hapus kolom bantuan _dt
            df_display = df_filtered.drop(columns=["_dt"], errors="ignore")
            
            # Deteksi nama kolom kategori
            col_kategori = "Katagori" if "Katagori" in df_display.columns else "Kategori"
            
            # Tampilkan Label Periode Bersih (menghapus garis pemisah jika dipilih)
            label_periode = filter_periode.replace("-", "").strip()
            
            # 1. Total Keseluruhan
            total = df_display["Jumlah"].sum() if "Jumlah" in df_display.columns else 0
            st.metric(label=f"Total Pengeluaran ({label_periode})", value=f"Rp {total:,.0f}")
            
            st.divider()

            # --- 2. LAPORAN RINGKASAN PER KATEGORI ---
            if col_kategori in df_display.columns and not df_display.empty:
                st.write("### 🏷️ Ringkasan Total per Kategori")
                
                df_kat = df_display.groupby(col_kategori)["Jumlah"].sum().reset_index()
                df_kat = df_kat.sort_values(by="Jumlah", ascending=False)
                
                df_kat_formatted = df_kat.copy()
                df_kat_formatted[col_kategori] = df_kat_formatted[col_kategori].apply(
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
            
            if col_kategori in df_display.columns and not df_display.empty:
                kategori_list = df_display.groupby(col_kategori)["Jumlah"].sum().sort_values(ascending=False).index
                
                for kat in kategori_list:
                    df_sub = df_display[df_display[col_kategori] == kat].copy()
                    sub_total = df_sub["Jumlah"].sum()
                    
                    icon = ICON_KATEGORI.get(kat, "📌")
                    
                    with st.expander(f"{icon} **{kat}** — Total: Rp {sub_total:,.0f} ({len(df_sub)} transaksi)"):
                        df_sub_display = df_sub.drop(columns=[col_kategori], errors="ignore")
                        if "Jumlah" in df_sub_display.columns:
                            df_sub_display["Jumlah"] = df_sub_display["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
                        
                        st.dataframe(
                            df_sub_display, 
                            hide_index=True,
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
