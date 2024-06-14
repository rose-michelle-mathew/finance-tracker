import streamlit as st
import sqlite3
from streamlit_option_menu import option_menu

st.set_page_config( page_title="Welcome")

# Connect to SQLite database
conn = sqlite3.connect('users.db', check_same_thread=False)
cur = conn.cursor()

# Create Users table
cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    name TEXT,
    username TEXT PRIMARY KEY,
    email TEXT,
    password TEXT
)
''')
conn.commit()

# Function to register a new user
def register_user(name, username, email, password):
    try:
        cur.execute('''
        INSERT INTO users (name, username, email, password)
        VALUES (?, ?, ?, ?)
        ''', (name, username, email, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# Function to verify user login
def login_user(username, password):
    cur.execute('''
    SELECT name,username FROM users WHERE username = ? AND password = ?
    ''', (username, password))
    user = cur.fetchone()
    return user

# Title
st.title("Welcome")

# Main section
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    container = st.container()
    with container:
        selected_login = option_menu(
            menu_title=None,
            options=["Sign Up", "Login"],
            orientation="horizontal",
            icons=["person-plus", "box-arrow-in-right"],  # Optional: Add icons for better UX
        )

        if selected_login == "Sign Up":
            with st.form("sign_up_form", clear_on_submit=True):
                name = st.text_input("Name")
                username = st.text_input("User Name")
                email = st.text_input("Email Id")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Sign Up"):
                    if register_user(name, username, email, password):
                        st.success("Successfully registered! Please log in.")
                    else:
                        st.error("Username already exists. Please use a different username.")

        elif selected_login == "Login":
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("User Name")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    user = login_user(username, password)
                    if user:
                        st.session_state["user"] = user[0]
                        st.session_state["username"] = user[1]
                        st.success(f"Logged in as {user[0]}")
                    else:
                        st.error("Invalid username or password")

else:
    st.sidebar.write(f"Welcome, {st.session_state['user']}!")
    if st.sidebar.button("Logout"):
        st.session_state["user"] = None
        st.experimental_rerun()

# Example main content for logged-in users
if st.session_state["user"]:
    st.write(f"Hello, {st.session_state['user']}!")
    st.write("This is your dashboard.")
else:
    st.write("Please log in to see your dashboard.")
