import mysql.connector
import streamlit as st

def get_connection():
    try:
        # Streamlit Cloud par chalne par secrets use karega
        if "db" in st.secrets:
            conn = mysql.connector.connect(
                host=st.secrets["db"]["host"],
                port=int(st.secrets["db"]["port"]),
                user=st.secrets["db"]["user"],
                password=st.secrets["db"]["password"],
                database=st.secrets["db"]["database"]
            )
        else:
            # Local PC (XAMPP) par chalne par
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="smartbus_db"
            )
        return conn
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None