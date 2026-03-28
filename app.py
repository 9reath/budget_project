import streamlit as st
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection

st.set_page_config(page_title="Sistem Budgeting Terpadu", layout="wide")
# conn = st.connection("supabase", type=SupabaseConnection)
conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url="https://bkgiroakvrcrzovhzmmy.supabase.co",
    key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJrZ2lyb2FrdnJjcnpvdmh6bW15Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ2MzY3NzAsImV4cCI6MjA5MDIxMjc3MH0.Mh9eWRrIJqc-NmFUkbtrJy-5AEEkzwDIMaeWMxj-ODs"
)

# --- FUNGSI LOGIN DINAMIS ---
def login_system():
    if "user_info" not in st.session_state:
        st.session_state.user_info = None

    if st.session_state.user_info is None:
        _, col, _ = st.columns([1, 1, 1])
        with col:
            with st.form("login_form"):
                st.subheader("🔑 Login Multi-User")
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Masuk"):
                    # Cek ke database Supabase
                    res = conn.table("users").select("*").eq("username", u).eq("password", p).execute()
                    if res.data:
                        st.session_state.user_info = res.data[0] # Simpan data user (id, username, role)
                        st.rerun()
                    else:
                        st.error("User atau Password salah!")
        return False
    return True

if login_system():
    user = st.session_state.user_info
    role = user['role']
    
    st.sidebar.title(f"Halo, {user['username']}")
    st.sidebar.info(f"Role: {role.replace('_', ' ').title()}")
    
    if st.sidebar.button("Logout"):
        st.session_state.user_info = None
        st.rerun()

    # --- LOGIKA HAK AKSES MENU ---
    
    # 1. Menu ADMIN (Bisa akses semua)
    if role == 'admin':
        menu = st.tabs(["Manajemen User", "Semua Data Budgeting", "Log Sistem"])
        with menu[0]:
            st.subheader("Daftar Pengguna")
            users_data = conn.table("users").select("*").execute()
            st.dataframe(pd.DataFrame(users_data.data))
        with menu[1]:
            st.subheader("Seluruh Transaksi")
            all_data = conn.table("transactions").select("*").execute()
            st.dataframe(pd.DataFrame(all_data.data))

    # 2. Menu KEPALA DAPUR (Upload & CRUD)
    elif role == 'kepala_dapur':
        # Mengambil username yang sedang login
        current_user = user['username'] 
        
        tab_upload, tab_data = st.tabs(["📤 Input & Upload", "📋 Data Saya"])
        
        with tab_upload:
            st.subheader(f"Upload Laporan: {current_user}")
            file = st.file_uploader("Pilih file .xlsx", type=["xlsx"])
            
            if file:
                df_upload = pd.read_excel(file)
                
                # --- TAMBAHAN KODE DI SINI ---
                from datetime import datetime
                
                # Menambahkan kolom uploaded_by (siapa) dan uploaded_date (kapan)
                df_upload['uploaded_by'] = current_user
                df_upload['uploaded_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                st.write("Preview Data yang akan di-upload:")
                st.dataframe(df_upload.head())
                
                if st.button("Konfirmasi Simpan ke Database"):
                    data_dict = df_upload.to_dict(orient="records")
                    conn.table("transactions").insert(data_dict).execute()
                    st.success(f"Berhasil! Data tersimpan atas nama {current_user}")

        with tab_data:
            st.subheader(f"Riwayat Input {current_user}")
            
            # Ambil data dari Supabase
            res = conn.table("transactions").select("*").eq("uploaded_by", current_user).execute()
            df_milik_saya = pd.DataFrame(res.data)

            if not df_milik_saya.empty:
                # Tampilkan editor dengan KEY yang tetap
                # Gunakan parameter on_change untuk mengunci data jika diperlukan, 
                # tapi cara paling simpel adalah mengecek session_state secara langsung.
                st.data_editor(
                    df_milik_saya, 
                    use_container_width=True,
                    num_rows="dynamic",
                    key="editor_dapur", 
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "uploaded_by": st.column_config.TextColumn("Pengunggah", disabled=True),
                        "uploaded_date": st.column_config.DatetimeColumn("Waktu Upload", disabled=True),
                        "updated_date": st.column_config.DatetimeColumn("Waktu Diperbarui", disabled=True),
                        "updated_by": st.column_config.TextColumn("Diperbarui Oleh", disabled=True),
                    }
                )
                
                # TOMBOL SIMPAN
                if st.button("💾 Simpan Semua Perubahan"):
                    # Ambil data perubahan dari session_state
                    state = st.session_state.get("editor_dapur")
                    
                    # DEBUG: Cek apakah state terbaca (akan muncul di pojok bawah)
                    # st.write(state) 

                    if state:
                        any_change = False
                        try:
                            # PROSES UPDATE
                            for row_idx_str, updates in state.get("edited_rows", {}).items():
                                actual_id = df_milik_saya.iloc[int(row_idx_str)]["id"]
                                updates["updated_by"] = current_user # Mengambil username login
                                updates["updated_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                conn.table("transactions").update(updates).eq("id", actual_id).execute()
                                any_change = True

                            # PROSES DELETE
                            for row_idx in state.get("deleted_rows", []):
                                actual_id = df_milik_saya.iloc[row_idx]["id"]
                                conn.table("transactions").delete().eq("id", actual_id).execute()
                                any_change = True

                            if any_change:
                                st.success("✅ Berhasil memperbarui database!")
                                # Beri jeda sebentar sebelum rerun agar pesan sukses terlihat
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("Tidak ada perubahan yang dilakukan pada tabel.")
                                
                        except Exception as e:
                            st.error(f"Terjadi kesalahan teknis: {e}")
                    else:
                        st.error("Gagal membaca data editor. Silakan edit ulang.")
            else:
                st.info("Belum ada data untuk ditampilkan.")

    # 3. Menu KEPALA PEMERINTAHAN (Hanya Lihat)
    elif role == 'kepala_pemerintahan':
        st.subheader("Monitoring Budgeting Dapur")
        # Filter: Hanya bisa melihat, tidak ada tombol edit/hapus
        res = conn.table("transactions").select("date, category, amount, type").execute()
        st.table(pd.DataFrame(res.data))