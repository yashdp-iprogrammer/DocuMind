import streamlit as st
import requests
import re

BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="DocuMind - AI Chat", layout="wide")

# ---------------- SESSION ----------------
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "form_errors" not in st.session_state:
    st.session_state.form_errors = {}
if "registered_success" not in st.session_state:
    st.session_state.registered_success = False
if "reg_version" not in st.session_state:
    st.session_state.reg_version = 0

def get_error_message(response):
    """Extracts error message from the standardized FastAPI JSON response."""
    try:
        data = response.json()
        return data.get("error", "An unexpected error occurred.")
    except Exception:
        return f"Server Error: {response.status_code}"

# VALIDATION
def is_valid_email(email):
    return re.match(r"^[^@]+@[^@]+\.[^@]+$", email)

def is_valid_phone(phone):
    return re.fullmatch(r"\d{10}", phone)

# API
def login(email, password):
    return requests.post(f"{BASE_URL}/login", json={"email": email, "password": password})

def register_user(name, email, phone, password):
    return requests.post(f"{BASE_URL}/users/create", json={
        "name": name, "email": email, "phone": phone, "password": password
    })

def embed_files(files, token):
    headers = {"Authorization": f"Bearer {token}"}
    files_payload = [("files", (file.name, file, file.type)) for file in files]
    return requests.post(f"{BASE_URL}/documents/embed", files=files_payload, headers=headers)

def chat(query, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return requests.post(f"{BASE_URL}/chat", headers=headers, json={"query": query})

def get_documents(token):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{BASE_URL}/documents?size=50", headers=headers)

def delete_document(doc_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.delete(f"{BASE_URL}/documents/{doc_id}", headers=headers)

# AUTH UI
def auth_ui():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<h3 style='text-align:center;'>DocuMind AI</h3>", unsafe_allow_html=True)

        if st.session_state.registered_success:
            st.success("Registered successfully! Please login below.")

        with st.container(border=True):
            tab_login, tab_register = st.tabs(["Login", "Register"])

            with tab_login:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_pwd")

                if st.button("Login", use_container_width=True):
                    if not email or not password:
                        st.error("All fields are required")
                    else:
                        res = login(email, password)
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.user = email
                            st.session_state.registered_success = False 
                            st.rerun()
                        else:
                            # Standardized Login Error
                            st.error(get_error_message(res))

            with tab_register:
                v = st.session_state.reg_version
                errors = st.session_state.form_errors

                name = st.text_input("Name", key=f"reg_name_{v}")
                if errors.get("name"): st.caption(f":red[{errors['name']}]")

                reg_email = st.text_input("Email", key=f"reg_email_{v}")
                if errors.get("email"): st.caption(f":red[{errors['email']}]")

                phone = st.text_input("Phone", key=f"reg_phone_{v}")
                if errors.get("phone"): st.caption(f":red[{errors['phone']}]")

                reg_password = st.text_input("Password", type="password", key=f"reg_pwd_{v}")
                if errors.get("password"): st.caption(f":red[{errors['password']}]")

                if st.button("Register", use_container_width=True):
                    errors = {}
                    if not name: errors["name"] = "Name is required"
                    if not reg_email: errors["email"] = "Email is required"
                    elif not is_valid_email(reg_email): errors["email"] = "Invalid email format"
                    if not phone: errors["phone"] = "Phone is required"
                    elif not is_valid_phone(phone): errors["phone"] = "Must be 10 digits"
                    if not reg_password: errors["password"] = "Password is required"
                    elif len(reg_password) < 6: errors["password"] = "Minimum 6 characters"

                    if errors:
                        st.session_state.form_errors = errors
                        st.rerun()
                    else:
                        res = register_user(name, reg_email, phone, reg_password)
                        if res.status_code in [200, 201]:
                            st.session_state.reg_version += 1 
                            st.session_state.registered_success = True 
                            st.session_state.form_errors = {}
                            st.rerun()
                        else:
                            # Standardized Registration Error
                            st.error(get_error_message(res))

# MAIN APP
def main_app():
    st.sidebar.title("DocuMind")
    st.sidebar.write(f"Welcome, {st.session_state.user}")

    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Upload Documents")
    files = st.sidebar.file_uploader("Upload PDFs", accept_multiple_files=True)

    if st.sidebar.button("Embed Documents"):
        if not files:
            st.sidebar.warning("Upload files first")
        else:
            with st.sidebar:
                with st.spinner("Embedding..."):
                    res = embed_files(files, st.session_state.token)
                    if res.status_code == 200:
                        st.success("Embedding complete")
                    else:
                        # Standardized Embedding Error
                        st.error(get_error_message(res))

    st.title("AI Document Chat")

    with st.expander("Manage Your Documents", expanded=True):
        res = get_documents(st.session_state.token)
        if res.status_code == 200:
            docs = res.json().get("data", [])
            if not docs:
                st.info("No documents uploaded")
            else:
                for doc in docs:
                    d_col1, d_col2 = st.columns([0.9, 0.1])
                    with d_col1: st.markdown(f"📄 {doc['file_name']}")
                    with d_col2:
                        if st.button("✕", key=f"del_{doc['id']}"):
                            del_res = delete_document(doc["id"], st.session_state.token)
                            if del_res.status_code == 200: st.rerun()
                            else: st.error(get_error_message(del_res))
        else:
            st.error(get_error_message(res))

    st.divider()

    for chat_item in st.session_state.chat_history:
        with st.chat_message("user"): st.write(chat_item["query"])
        with st.chat_message("assistant"): st.write(chat_item["answer"])

    query = st.chat_input("Ask something about your documents...")

    if query:
        with st.chat_message("user"): st.write(query)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                res = chat(query, st.session_state.token)
                if res.status_code == 200:
                    answer = res.json().get("answer", "No response")
                    st.write(answer)
                    st.session_state.chat_history.append({"query": query, "answer": answer})
                else:
                    st.error(get_error_message(res))

# ROUTER
if not st.session_state.token:
    auth_ui()
else:
    main_app()