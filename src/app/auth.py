import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
from data_models import User

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate({
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
    })
    firebase_admin.initialize_app(cred)

def check_authentication():
    """Check if user is authenticated"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    return st.session_state.authenticated

def login_form():
    """Display login form and handle authentication"""
    st.title("Login")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        try:
            # Sign in with Firebase
            # user = auth.get_user_by_email(email)
            # Note: In a real app, you would verify the password here
            # This requires additional Firebase Authentication setup
            
            # For demo purposes, we'll map emails to roles
            # In a real app, you would store user roles in Firestore
            role_mapping = {
                "manager@primelabs.com": User.MANAGER,
                "supervisor@primelabs.com": User.SUPERVISOR,
                "doctor@primelabs.com": User.DOCTOR
            }
            
            if email in role_mapping:
                st.session_state.authenticated = True
                st.session_state.user_role = role_mapping[email]
                st.session_state.user_email = email
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("User not authorized")
        except auth.UserNotFoundError:
            st.error("User not found")
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")


def logout():
    """Logout the user"""
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.user_email = None
    st.rerun()


def require_auth(required_role: User = None):
    """Check if user is authenticated and has required role"""
    if not check_authentication():
        return False
    
    if required_role and st.session_state.user_role != required_role:
        st.error("You don't have permission to access this page")
        return False    

    return True


def get_current_user():
    """Get the current user's information"""
    if check_authentication():
        return {
            'email': st.session_state.user_email,
            'role': st.session_state.user_role
        }
    return None
