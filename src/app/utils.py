import streamlit as st
from firestore_crud import FirestoreCRUD


def get_firestore_admin_credential_dict()->dict:
    return {
                "type": st.secrets["type"],
                "project_id": st.secrets["project_id"],
                "private_key_id": st.secrets["private_key_id"],
                "private_key": st.secrets["private_key"].replace('\\n', '\n'),
                "client_email": st.secrets["client_email"],
                "client_id": st.secrets["client_id"],
                "auth_uri": st.secrets["auth_uri"],
                "token_uri": st.secrets["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["client_x509_cert_url"]
            }


def get_firebase_auth_config():
    return  {
    "apiKey": st.secrets["web_api_key"],
    "authDomain": f"{st.secrets['project_id']}.firebaseapp.com",
    "databaseURL": f"https://{st.secrets['project_id']}-default-rtdb.firebaseio.com/",
    "projectId": st.secrets["project_id"],
    "storageBucket": f"{st.secrets['project_id']}.firebasestorage.app",
    "messagingSenderId": st.secrets.get("messaging_sender_id", ""),
    "appId": st.secrets.get("app_id", "")
}

@st.cache_resource
def get_firestore():
    return FirestoreCRUD()
