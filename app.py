import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Masukkan URL Web App dari Apps Script Langkah 2
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby8F7dcFUCMy7Dk-49c-zqV1xxEudo_3zGA_AJvfze3pbrAgQPUleaQbSwEq8TrSlzC/exec"

st.set_page_config(page_title="Catatan Pengeluaran", page_icon="💰", layout="centered")

st.title("💰 Catatan Pengeluaran")

tab1, tab2 = st.tabs(["➕ Tambah Pengeluaran", "📊 Lihat Data & Total"])

# --- TAB 1: FORM INPUT ---
with tab1:
    st.subheader("Input Pengeluaran Baru")
    with st.form("form_pengeluaran", clear_on_submit=True):
        tanggal = st.date_input("Tanggal", datetime.now()).strftime("%Y-%m-%d")
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
            elif WEB_APP_URL == "https://script.google.com/macros/s/AKfycby8F7dcFUCMy7Dk-49c-zqV1xxEudo_3zGA_AJvfze3pbrAgQPUleaQbSwEq8TrSlzC/exec":
                st.error("Ganti WEB_APP_URL dengan URL dari Google Apps Script Anda!")
            else:
                payload = {
                    "tanggal": tanggal,
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

# --- TAB 2: RIWAYAT DATA ---
with tab2:
    st.subheader("Riwayat & Total")
    if WEB_APP_URL != "https://script.google.com/macros/s/AKfycby8F7dcFUCMy7Dk-49c-zqV1xxEudo_3zGA_AJvfze3pbrAgQPUleaQbSwEq8TrSlzC/exec":
        try:
            res = requests.get(WEB_APP_URL)
            data = res.json()
            
            if len(data) > 1:
                header = data[0]
                rows = data[1:]
                df = pd.DataFrame(rows, columns=header)
                
                # Konversi kolom Jumlah ke angka
                df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
                
                total = df["Jumlah"].sum()
                st.metric(label="Total Pengeluaran", value=f"Rp {total:,.0f}")
                
                st.divider()
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Belum ada data pengeluaran.")
        except Exception as e:
            st.error(f"Gagal mengambil data: {e}")
    else:
        st.error("Isi WEB_APP_URL terlebih dahulu di kode kode Python Anda.")