import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

# URL Google Apps Script Anda
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby8F7dcFUCMy7Dk-49c-zqV1xxEudo_3zGA_AJvfze3pbrAgQPUleaQbSwEq8TrSlzC/exec"

st.set_page_config(page_title="Catatan Pengeluaran", page_icon="💰", layout="centered")

st.title("💰 Catatan Pengeluaran")

tab1, tab2 = st.tabs(["➕ Tambah Pengeluaran", "📊 Lihat Data & Total"])

# --- TAB 1: FORM INPUT ---
with tab1:
    st.subheader("Input Pengeluaran Baru")
    with st.form("form_pengeluaran", clear_on_submit=True):
        input_tanggal = st.date_input("Tanggal", datetime.now())
        kategori = st.selectbox(
            "Kategori", 
            ["Makanan & Minuman", "Transportasi", "Kebutuhan Rumah", "Hiburan", "Tagihan & Pulsa", "Lainnya"]
        )
        jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=1000, format="%d")
        keterangan = st.text_input("Keterangan (Opsional)")
        
        submitted = st.form_submit_button("Simpan Data")
        
        if submitted:
            if jumlah <= 0:
                st.warning("Jumlah pengeluaran harus lebih besar dari 0.")
            else:
                # Ambil waktu WIB
                wib = pytz.timezone('Asia/Jakarta')
                now_wib = datetime.now(wib)
                
                # Format: YYYY-MM-DD HH:MM
                tanggal_jam_str = f"{input_tanggal.strftime('%Y-%m-%d')} {now_wib.strftime('%H:%M')}"
                
                payload = {
                    "tanggal": tanggal_jam_str,
                    "kategori": kategori,
                    "jumlah": jumlah,
                    "keterangan": keterangan
                }
                try:
                    res = requests.post(WEB_APP_URL, json=payload)
                    if res.status_code == 200 and res.json().get("status") == "success":
                        st.success("✓ Catatan berhasil tersimpan ke Google Sheets!")
                    else:
                        st.error("Gagal menyimpan data ke Google Sheets.")
                except Exception as e:
                    st.error(f"Terjadi kesalahan koneksi: {e}")

# --- TAB 2: RIWAYAT DATA & FILTER ---
with tab2:
    st.subheader("Riwayat & Total Pengeluaran")
    try:
        res = requests.get(WEB_APP_URL)
        data = res.json()
        
        if len(data) > 1:
            header = data[0]
            rows = data[1:]
            df = pd.DataFrame(rows, columns=header)
            
            # Konversi kolom Jumlah ke angka
            df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
            
            # Kolom pembantu untuk filter tanggal
            df["_dt"] = pd.to_datetime(df["Tanggal"], errors="coerce")
            
            # --- PILIHAN FILTER PERIODE ---
            filter_periode = st.selectbox(
                "📅 Pilih Periode Tampilan:",
                ["Semua", "Bulan Ini", "Minggu Ini"]
            )
            
            # Waktu saat ini (WIB)
            wib = pytz.timezone('Asia/Jakarta')
            now = datetime.now(wib)
            
            if filter_periode == "Bulan Ini":
                df_filtered = df[(df["_dt"].dt.month == now.month) & (df["_dt"].dt.year == now.year)].copy()
            elif filter_periode == "Minggu Ini":
                current_week = now.isocalendar().week
                df_filtered = df[(df["_dt"].dt.isocalendar().week == current_week) & (df["_dt"].dt.year == now.year)].copy()
            else:
                df_filtered = df.copy()
            
            # Hapus kolom bantuan _dt
            df_filtered = df_filtered.drop(columns=["_dt"])
            
            # Atur penomoran indeks mulai dari 1
            if not df_filtered.empty:
                df_filtered.index = range(1, len(df_filtered) + 1)
            
            # Tampilkan total pengeluaran berdasarkan filter
            total = df_filtered["Jumlah"].sum()
            st.metric(label=f"Total Pengeluaran ({filter_periode})", value=f"Rp {total:,.0f}")
            
            st.divider()
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.info("Belum ada data pengeluaran.")
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")
