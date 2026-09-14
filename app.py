import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import pytz

# URL Web App Google Apps Script Anda
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyxpOXOkt9jgMtr9q8S8zVbfUwyVLGTpxmCoBj9YieZMt1IBhQHrUM7JEa4EEqStTCj/exec"

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
                    res = requests.post(WEB_APP_URL, json=payload, timeout=10, allow_redirects=True)
                    if res.status_code == 200:
                        st.success("✓ Catatan berhasil tersimpan ke Google Sheets!")
                        st.cache_data.clear()
                    else:
                        st.error("Gagal menyimpan data ke Google Sheets.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan koneksi: {e}")

# --- TAB 2: RIWAYAT DATA & LAPORAN ---
with tab2:
    st.subheader("Riwayat & Laporan Pengeluaran")
    
    ICON_KATEGORI = {
        "Belanja bulanan": "🛒",
        "Transportasi": "🚗",
        "Kebutuhan Rumah": "🏠",
        "Hiburan / Jajanan": "🍿",
        "Tagihan & Pulsa": "💡",
        "Lainnya": "📦"
    }
    
    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_sheet_data():
        res = requests.get(WEB_APP_URL, timeout=10, allow_redirects=True)
        return res.json()

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
        
    try:
        with st.spinner("Mengambil data dari Google Sheets..."):
            data = fetch_sheet_data()

        if isinstance(data, list) and len(data) > 1:
            header = [str(col).strip() for col in data[0]]
            rows = data[1:]
            df = pd.DataFrame(rows, columns=header)
            
            # Normalisasi Kolom
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
            
            for req_col in ["Tanggal", "Kategori", "Jumlah", "Keterangan"]:
                if req_col not in df.columns:
                    df[req_col] = ""

            df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
            
            # Parsing Tanggal Multi-Format
            df["_dt"] = pd.to_datetime(df["Tanggal"], format="mixed", errors="coerce")
            if df["_dt"].isnull().any():
                df_str_date = df["Tanggal"].astype(str).str.extract(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})')[0]
                df["_dt"] = df["_dt"].fillna(pd.to_datetime(df_str_date, errors="coerce"))

            # --- MENU PENGATURAN TANGGAL GAJIAN ---
            with st.expander("⚙️ **Atur Tanggal Gajian / Cut-off Siklus Laporan**", expanded=False):
                st.write("Atur tanggal gajian/cut-off sesuai kondisi bulan ini:")
                
                col1, col2 = st.columns(2)
                with col1:
                    tgl_curr_start = st.date_input("Mulai Bulan Ini (Gajian)", value=date(2026, 8, 26))
                    tgl_curr_end = st.date_input("Sampai Tanggal", value=date(2026, 9, 25))
                with col2:
                    tgl_last_start = st.date_input("Mulai Bulan Lalu", value=date(2026, 7, 28))
                    tgl_last_end = st.date_input("Sampai Tanggal (Bulan Lalu)", value=date(2026, 8, 25))
                
                st.divider()
                use_tutup_buku = st.checkbox("🔒 Aktifkan Tutup Buku (Sembunyikan data lama saat klik 'Semua')")
                tgl_tutup_buku = date(2026, 8, 31)
                if use_tutup_buku:
                    tgl_tutup_buku = st.date_input("Sembunyikan Data Sebelum Tanggal Ini (Hanya untuk Opsi 'Semua'):", value=date(2026, 8, 31))

            str_curr = f"Bulan Ini ({tgl_curr_start.strftime('%d %b')} - {tgl_curr_end.strftime('%d %b %Y')})"
            str_last = f"Bulan Lalu ({tgl_last_start.strftime('%d %b')} - {tgl_last_end.strftime('%d %b %Y')})"

            filter_options = [
                "Semua", 
                str_curr, 
                str_last, 
                "Custom (Pilih Rentang Tanggal Bebas)"
            ]
            
            filter_periode = st.selectbox("📅 Pilih Periode Laporan:", filter_options)
            
            has_valid_dt = "_dt" in df.columns and df["_dt"].notnull().any()
            
            if has_valid_dt:
                df["_only_date"] = df["_dt"].dt.date
                
                if filter_periode == str_curr:
                    df_filtered = df[(df["_only_date"] >= tgl_curr_start) & (df["_only_date"] <= tgl_curr_end)].copy()
                elif filter_periode == str_last:
                    df_filtered = df[(df["_only_date"] >= tgl_last_start) & (df["_only_date"] <= tgl_last_end)].copy()
                elif filter_periode == "Custom (Pilih Rentang Tanggal Bebas)":
                    range_tgl = st.date_input(
                        "Pilih Rentang Tanggal (Mulai - Selesai):",
                        value=(datetime.now().date(), datetime.now().date()),
                        key="custom_range"
                    )
                    if isinstance(range_tgl, tuple) and len(range_tgl) == 2:
                        tgl_m, tgl_s = range_tgl
                        df_filtered = df[(df["_only_date"] >= tgl_m) & (df["_only_date"] <= tgl_s)].copy()
                    else:
                        df_filtered = df.copy()
                else: # Opsi "Semua"
                    if use_tutup_buku:
                        df_filtered = df[df["_only_date"] >= tgl_tutup_buku].copy()
                    else:
                        df_filtered = df.copy()
            else:
                df_filtered = df.copy()
            
            df_display = df_filtered.drop(columns=["_dt", "_only_date"], errors="ignore")
            
            # Total
            total = df_display["Jumlah"].sum() if not df_display.empty else 0
            st.metric(label=f"Total Pengeluaran ({filter_periode})", value=f"Rp {total:,.0f}")
            
            st.divider()

            # --- KONFIGURASI TAMPILAN LEBAR KOLOM ---
            config_terakhir = {
                "Tanggal": st.column_config.TextColumn("Tanggal", width="medium"),
                "Kategori": st.column_config.TextColumn("Kategori", width="medium"),
                "Jumlah": st.column_config.TextColumn("Jumlah", width="medium"),
                "Keterangan": st.column_config.TextColumn("Keterangan", width="large")
            }

            config_detail = {
                "Tanggal": st.column_config.TextColumn("Tanggal", width="medium"),
                "Jumlah": st.column_config.TextColumn("Jumlah", width="medium"),
                "Keterangan": st.column_config.TextColumn("Keterangan", width="large")
            }

            # --- TRANSAKSI TERAKHIR ---
            if not df_display.empty:
                st.write("### 🕒 Transaksi Terakhir (Terbaru)")
                
                df_recent = df_display.tail(5).iloc[::-1].copy()
                df_recent["Jumlah"] = df_recent["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
                df_recent["Kategori"] = df_recent["Kategori"].apply(lambda x: f"{ICON_KATEGORI.get(x, '📌')} {x}")
                
                # Urutan: Tanggal -> Kategori -> Jumlah -> Keterangan
                recent_cols = ["Tanggal", "Kategori", "Jumlah", "Keterangan"]
                df_recent_final = df_recent.reindex(columns=recent_cols).fillna("-")
                
                st.dataframe(
                    df_recent_final,
                    column_config=config_terakhir,
                    hide_index=True,
                    use_container_width=True
                )
                st.divider()

            # --- RINGKASAN PER KATEGORI ---
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
                
                st.dataframe(
                    df_kat_formatted,
                    hide_index=True,
                    use_container_width=True
                )
                st.divider()

            # --- DETAIL PER KATEGORI ---
            st.write("### 📂 Detail Rincian per Kategori")
            
            if not df_display.empty:
                kategori_list = df_display.groupby("Kategori")["Jumlah"].sum().sort_values(ascending=False).index
                
                for kat in kategori_list:
                    df_sub = df_display[df_display["Kategori"] == kat].copy()
                    sub_total = df_sub["Jumlah"].sum()
                    
                    icon = ICON_KATEGORI.get(kat, "📌")
                    
                    with st.expander(f"{icon} **{kat}** — Total: Rp {sub_total:,.0f} ({len(df_sub)} transaksi)"):
                        df_sub["Jumlah"] = df_sub["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
                        
                        # Urutan konsisten: Tanggal -> Jumlah -> Keterangan
                        target_columns = ["Tanggal", "Jumlah", "Keterangan"]
                        df_sub_final = df_sub.reindex(columns=target_columns).fillna("-")
                        
                        st.dataframe(
                            df_sub_final, 
                            column_config=config_detail,
                            hide_index=True,
                            use_container_width=True
                        )
            else:
                st.info("Belum ada rincian data untuk periode ini.")
            
        elif isinstance(data, list) and len(data) <= 1:
            st.info("Belum ada data pengeluaran di Google Sheets.")
            
    except requests.exceptions.Timeout:
        st.warning("⏱️ Waktu koneksi ke Google Sheets habis (Timeout). Silakan klik tombol '🔄 Refresh Data'.")
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengambil data: {e}")
