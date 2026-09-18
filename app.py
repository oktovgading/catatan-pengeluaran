import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbw4g0MoSsrI3utH3xtlnmU0UDwAnGyMLMFPR6EnnqhwYx0tUUmm8zm-v9d2OVeqdWhS/exec"


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
                        st.success("✓ Catatan berhasil tersimpan!")
                        st.cache_data.clear()
                    else:
                        st.error("Gagal menyimpan data.")
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

    col_ref, col_tb = st.columns([1, 2])
    with col_ref:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    # --- MENU TUTUP BUKU (KLIK SENDIRI) ---
    with st.expander("⚙️ **Atur / Klik Tutup Buku (Gajian)**"):
        st.write("Klik tombol di bawah saat tanggal gajian untuk memindahkan data bulan ini ke arsip bulan lalu.")
        if st.button("🔒 Tutup Buku Sekarang", type="primary"):
            try:
                res = requests.post(WEB_APP_URL, json={"action": "tutup_buku"}, timeout=15)
                if res.status_code == 200:
                    st.success("✅ Tutup buku berhasil! Data Bulan Ini telah dipindah ke Arsip Bulan Lalu.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Gagal melakukan tutup buku.")
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

    st.divider()

    try:
        with st.spinner("Mengambil data..."):
            raw_data = fetch_sheet_data()

        def process_data(data_list):
            if isinstance(data_list, list) and len(data_list) > 1:
                header = [str(col).strip() for col in data_list[0]]
                rows = data_list[1:]
                df = pd.DataFrame(rows, columns=header)
                
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
                return df
            return pd.DataFrame(columns=["Tanggal", "Kategori", "Jumlah", "Keterangan"])

        df_sheet1 = process_data(raw_data.get("sheet1", []))
        df_sheet2 = process_data(raw_data.get("sheet2", []))

        filter_options = [
            "Bulan Ini / Aktif",
            "Bulan Lalu / Arsip",
            "Gabungan Semua Data"
        ]
        
        filter_periode = st.selectbox("📅 Pilih Laporan Periode:", filter_options)
        
        if filter_periode == "Bulan Ini / Aktif":
            df_display = df_sheet2.copy()
        elif filter_periode == "Bulan Lalu / Arsip":
            df_display = df_sheet1.copy()
        else:
            df_display = pd.concat([df_sheet1, df_sheet2], ignore_index=True)

        total = df_display["Jumlah"].sum() if not df_display.empty else 0
        st.metric(label=f"Total Pengeluaran ({filter_periode})", value=f"Rp {total:,.0f}")
        
        st.divider()

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

        if not df_display.empty:
            st.write("### 🕒 Transaksi Terakhir (Terbaru)")
            df_recent = df_display.tail(5).iloc[::-1].copy()
            df_recent["Jumlah"] = df_recent["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
            df_recent["Kategori"] = df_recent["Kategori"].apply(lambda x: f"{ICON_KATEGORI.get(x, '📌')} {x}")
            
            recent_cols = ["Tanggal", "Kategori", "Jumlah", "Keterangan"]
            df_recent_final = df_recent.reindex(columns=recent_cols).fillna("-")
            
            st.dataframe(df_recent_final, column_config=config_terakhir, hide_index=True, use_container_width=True)
            st.divider()

        if not df_display.empty:
            st.write("### 🏷️ Ringkasan Total per Kategori")
            df_kat = df_display.groupby("Kategori")["Jumlah"].sum().reset_index().sort_values(by="Jumlah", ascending=False)
            df_kat_formatted = df_kat.copy()
            df_kat_formatted["Kategori"] = df_kat_formatted["Kategori"].apply(lambda x: f"{ICON_KATEGORI.get(x, '📌')} {x}")
            df_kat_formatted["Total Pengeluaran"] = df_kat_formatted["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
            df_kat_formatted = df_kat_formatted.drop(columns=["Jumlah"])
            
            st.dataframe(df_kat_formatted, hide_index=True, use_container_width=True)
            st.divider()

        st.write("### 📂 Detail Rincian per Kategori")
        if not df_display.empty:
            kategori_list = df_display.groupby("Kategori")["Jumlah"].sum().sort_values(ascending=False).index
            for kat in kategori_list:
                df_sub = df_display[df_display["Kategori"] == kat].copy()
                sub_total = df_sub["Jumlah"].sum()
                icon = ICON_KATEGORI.get(kat, "📌")
                
                with st.expander(f"{icon} **{kat}** — Total: Rp {sub_total:,.0f} ({len(df_sub)} transaksi)"):
                    df_sub_formatted = df_sub.copy()
                    df_sub_formatted["Jumlah"] = df_sub_formatted["Jumlah"].apply(lambda x: f"Rp {x:,.0f}")
                    target_columns = ["Tanggal", "Jumlah", "Keterangan"]
                    df_sub_final = df_sub_formatted.reindex(columns=target_columns).fillna("-")
                    
                    st.dataframe(df_sub_final, column_config=config_detail, hide_index=True, use_container_width=True)
        else:
            st.info("Belum ada rincian data pada periode ini.")
            
    except requests.exceptions.Timeout:
        st.warning("⏱️ Timeout. Klik '🔄 Refresh Data'.")
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
