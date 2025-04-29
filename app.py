import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime
from fpdf import FPDF
from io import BytesIO

# ---- Page Setup ----
st.set_page_config(page_title="School Management System", page_icon="🧑‍🏫", layout="centered")

DB_PATH = "data/students.db"

# ---- Ensure Required Folders Exist ----
os.makedirs("assets", exist_ok=True)
os.makedirs("assets/photos", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ---- Database Setup ----
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        class TEXT,
        section TEXT,
        class_teacher TEXT,
        phone TEXT,
        year TEXT,
        fee_paid INTEGER,
        fee_balance INTEGER,
        photo TEXT,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ---- PDF Generator ----
def generate_student_pdf(student):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Student Record", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    for key, value in student.items():
        if key not in ["photo", "timestamp", "id"]:
            pdf.cell(50, 10, f"{key.capitalize()}:", 0)
            pdf.cell(100, 10, str(value), 0, ln=True)
    pdf.ln(10)
    if student["photo"]:
        photo_path = f"assets/photos/{student['name'].replace(' ', '_')}_{student['photo']}"
        if os.path.exists(photo_path):
            pdf.image(photo_path, x=10, y=pdf.get_y(), w=40)
    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

# ---- Header ----
col1, col2 = st.columns([1, 4])
with col1:
    st.image("assets/logo.png", width=100)
with col2:
    st.markdown("<h1 style='margin-top: 20px;'>ABC Public School</h1>", unsafe_allow_html=True)
st.markdown("---")

# ---- Login ----
USERNAME = "admin"
PASSWORD = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_failed" not in st.session_state:
    st.session_state.login_failed = False

if not st.session_state.logged_in:
    st.subheader("Admin Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")
        if login_btn:
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
                st.session_state.login_failed = False
            else:
                st.session_state.login_failed = True
    if st.session_state.login_failed:
        st.error("Invalid credentials. Please try again.")
else:
    st.sidebar.markdown("### Navigation")
    nav = st.sidebar.radio("Go to", ["Dashboard", "Add Student", "Student Dashboard", "Edit Student"])

    if nav == "Dashboard":
        st.subheader("📊 Dashboard")
        conn = get_conn()
        df = pd.read_sql("SELECT * FROM students", conn)
        conn.close()

        if df.empty:
            st.warning("No student data available.")
        else:
            total_students = len(df)
            total_classes = df["class"].nunique()
            total_fee_paid = df["fee_paid"].sum()
            total_fee_balance = df["fee_balance"].sum()

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Students", total_students)
            with col2:
                st.metric("Total Classes", total_classes)
            with col3:
                st.metric("Fee Received (₹)", total_fee_paid)
            with col4:
                st.metric("Fee Pending (₹)", total_fee_balance)

            st.markdown("### Filter Fee Report by Month")
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['month'] = df['timestamp'].dt.month
            month_filter = st.selectbox("Select Month", sorted(df['month'].unique()))
            filtered_df = df[df['month'] == month_filter]
            st.write(f"Showing data for month {month_filter}:")
            st.dataframe(filtered_df)

    elif nav == "Add Student":
        st.subheader("➕ Add New Student")
        with st.form("student_form"):
            name = st.text_input("Full Name")
            student_class = st.text_input("Class")
            section = st.text_input("Section")
            class_teacher = st.text_input("Class Teacher Name")
            phone = st.text_input("Phone Number")
            year = st.selectbox("Academic Year", [str(y) for y in range(2020, datetime.now().year + 2)])
            fee_paid = st.number_input("Fee Paid (in ₹)", min_value=0)
            fee_balance = st.number_input("Fee Balance (in ₹)", min_value=0)
            photo = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])
            submit = st.form_submit_button("Save")

            if submit:
                photo_name = photo.name if photo else ""
                if photo:
                    photo_path = f"assets/photos/{name.replace(' ', '_')}_{photo_name}"
                    with open(photo_path, "wb") as f:
                        f.write(photo.getbuffer())

                conn = get_conn()
                conn.execute("""
                    INSERT INTO students (name, class, section, class_teacher, phone, year, fee_paid, fee_balance, photo, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, student_class, section, class_teacher, phone, year, fee_paid, fee_balance, photo_name, datetime.now()))
                conn.commit()
                conn.close()

                st.success("Student data saved successfully!")

    elif nav == "Edit Student":
        st.subheader("✏️ Edit Student Record")
        conn = get_conn()
        df = pd.read_sql("SELECT * FROM students", conn)
        conn.close()

        if df.empty:
            st.warning("No student data available.")
        else:
            df["Student Label"] = df["name"] + " | " + df["phone"].astype(str)
            selected = st.selectbox("Select Student", df["Student Label"])
            if selected:
                student = df[df["Student Label"] == selected].iloc[0]
                with st.form("edit_form"):
                    name = st.text_input("Full Name", value=student["name"])
                    student_class = st.text_input("Class", value=student["class"])
                    section = st.text_input("Section", value=student["section"])
                    class_teacher = st.text_input("Class Teacher", value=student["class_teacher"])
                    phone = st.text_input("Phone", value=student["phone"])
                    year = st.selectbox("Academic Year", [str(y) for y in range(2020, datetime.now().year + 2)], index=int(student["year"]) - 2020)
                    fee_paid = st.number_input("Fee Paid", min_value=0, value=int(student["fee_paid"]))
                    fee_balance = st.number_input("Fee Balance", min_value=0, value=int(student["fee_balance"]))
                    photo = st.file_uploader("Upload New Photo (optional)")

                    submit = st.form_submit_button("Update")

                    if submit:
                        photo_name = student["photo"]
                        if photo:
                            photo_name = photo.name
                            photo_path = f"assets/photos/{name.replace(' ', '_')}_{photo_name}"
                            with open(photo_path, "wb") as f:
                                f.write(photo.getbuffer())

                        conn = get_conn()
                        conn.execute("""
                            UPDATE students
                            SET name=?, class=?, section=?, class_teacher=?, phone=?, year=?, fee_paid=?, fee_balance=?, photo=?, timestamp=?
                            WHERE id=?
                        """, (name, student_class, section, class_teacher, phone, year, fee_paid, fee_balance, photo_name, datetime.now(), student["id"]))
                        conn.commit()
                        conn.close()

                        st.success("Student record updated!")

    elif nav == "Student Dashboard":
        st.subheader("👨‍🎓 Student Dashboard")
        conn = get_conn()
        df = pd.read_sql("SELECT * FROM students", conn)
        conn.close()

        with st.sidebar:
            class_filter = st.text_input("Class")
            section_filter = st.text_input("Section")
            year_filter = st.selectbox("Year", ["All"] + sorted(df["year"].unique()))
            name_search = st.text_input("Search by Name")

        if class_filter:
            df = df[df["class"].str.contains(class_filter, case=False)]
        if section_filter:
            df = df[df["section"].str.contains(section_filter, case=False)]
        if year_filter != "All":
            df = df[df["year"] == year_filter]
        if name_search:
            df = df[df["name"].str.contains(name_search, case=False)]

        total_students = len(df)
        st.markdown(f"### Total Students: **{total_students}**")

        page_size = 50

        if total_students == 0:
            st.warning("No students found.")
        else:
            total_pages = (total_students // page_size) + int(total_students % page_size > 0)
            page_number = st.number_input("Page Number", min_value=1, max_value=total_pages, step=1)

            start_idx = (page_number - 1) * page_size
            end_idx = start_idx + page_size
            st.dataframe(df[start_idx:end_idx])

            st.download_button(
                "Download Current Page as CSV",
                data=df[start_idx:end_idx].to_csv(index=False),
                file_name=f"students_page_{page_number}.csv",
                mime="text/csv"
            )
