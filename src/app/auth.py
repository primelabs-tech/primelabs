import streamlit as st
import pyrebase
from firebase_admin import auth

from data_models import User


firebase_config = {
    "apiKey": st.secrets["web_api_key"],
    "authDomain": f"{st.secrets['project_id']}.firebaseapp.com",
    "projectId": st.secrets["project_id"],
    "storageBucket": f"{st.secrets['project_id']}.appspot.com",
    "messagingSenderId": st.secrets.get("messaging_sender_id", ""),
    "appId": st.secrets.get("app_id", ""),
    "databaseURL": ""  # Not needed for auth only
}

firebase = pyrebase.initialize_app(firebase_config)
firebase_auth = firebase.auth()

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
    
    # Add registration option
    auth_mode = st.radio("Choose an option:", ["Login", "Register", "Reset Password"], horizontal=True)
    
    if auth_mode == "Reset Password":
        reset_password()
        return
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if auth_mode == "Login":
        if st.button("Sign In"):
            if email and password:
                try:
                    # Authenticate with Firebase
                    user = firebase_auth.sign_in_with_email_and_password(email, password)
                    
                    # Verify the token with Firebase Admin SDK
                    decoded_token = auth.verify_id_token(user['idToken'])
                    user_email = decoded_token['email']
                    
                    # Get user role from Firestore or use default mapping
                    user_role = get_user_role(user_email)
                    
                    # Set session state
                    st.session_state.authenticated = True
                    st.session_state.user_role = user_role
                    st.session_state.user_email = user_email
                    st.session_state.user_token = user['idToken']
                    st.session_state.user_id = decoded_token['uid']
                    
                    st.success("Login successful!")
                    st.rerun()
                    
                except Exception as e:
                    if "INVALID_EMAIL" in str(e):
                        st.error("Invalid email format")
                    elif "EMAIL_NOT_FOUND" in str(e):
                        st.error("No account found with this email")
                    elif "INVALID_PASSWORD" in str(e):
                        st.error("Incorrect password")
                    elif "TOO_MANY_ATTEMPTS_TRY_LATER" in str(e):
                        st.error("Too many failed attempts. Please try again later")
                    else:
                        st.error(f"Authentication failed: {str(e)}")
            else:
                st.error("Please enter both email and password")
    
    else:  # Register mode
        confirm_password = st.text_input("Confirm Password", type="password")
        user_role_selection = st.selectbox("Select Role", [User.DOCTOR, User.SUPERVISOR, User.MANAGER])
        
        if st.button("Register"):
            if email and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match")
                    return
                    
                try:
                    # Create user with Firebase
                    user = firebase_auth.create_user_with_email_and_password(email, password)
                    
                    # Store user role in Firestore
                    from firestore_crud import FirestoreCRUD
                    db = FirestoreCRUD(use_admin_sdk=True)
                    
                    user_data = {
                        "email": email,
                        "role": user_role_selection,
                        "created_at": st.session_state.get('timestamp', 'unknown')
                    }
                    
                    db.create_doc("users", user_data, doc_id=user['localId'])
                    
                    st.success("Registration successful! Please login with your credentials.")
                    
                except Exception as e:
                    if "EMAIL_EXISTS" in str(e):
                        st.error("An account with this email already exists")
                    elif "WEAK_PASSWORD" in str(e):
                        st.error("Password should be at least 6 characters")
                    elif "INVALID_EMAIL" in str(e):
                        st.error("Invalid email format")
                    else:
                        st.error(f"Registration failed: {str(e)}")
            else:
                st.error("Please fill in all fields")


def get_user_role(email):
    """Get user role from Firestore or return default role"""
    try:
        from firestore_crud import FirestoreCRUD
        db = FirestoreCRUD(use_admin_sdk=True)
        
        # Try to get user role from Firestore
        user_docs = db.get_docs("users", filters=[("email", "==", email)])
        
        if user_docs:
            return user_docs[0].get("role", User.DOCTOR)  # Default to DOCTOR if role not found
        else:
            # Fallback to hardcoded mapping for existing users
            role_mapping = {
                "manager@primelabs.com": User.MANAGER,
                "supervisor@primelabs.com": User.SUPERVISOR,
                "doctor@primelabs.com": User.DOCTOR
            }
            return role_mapping.get(email, User.DOCTOR)
            
    except Exception as e:
        st.error(f"Error getting user role: {str(e)}")
        return User.DOCTOR  # Default role


def logout():
    """Logout the user"""
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.user_email = None
    st.session_state.user_token = None
    st.session_state.user_id = None
    st.rerun()


def require_auth(required_role: User = None):
    """Check if user is authenticated and has required role"""
    if not check_authentication():
        return False
    
    # Verify token is still valid if present
    if hasattr(st.session_state, 'user_token') and st.session_state.user_token:
        try:
            decoded_token = auth.verify_id_token(st.session_state.user_token)
            # Token is valid, user is authenticated
        except Exception as e:
            # Token is invalid or expired, logout user
            st.error("Session expired. Please login again.")
            logout()
            return False
    
    if required_role and st.session_state.user_role != required_role:
        st.error("You don't have permission to access this page")
        return False    

    return True


def reset_password():
    """Handle password reset"""
    st.subheader("Reset Password")
    reset_email = st.text_input("Enter your email address")
    
    if st.button("Send Reset Email"):
        if reset_email:
            try:
                firebase_auth.send_password_reset_email(reset_email)
                st.success("Password reset email sent! Check your inbox.")
            except Exception as e:
                if "EMAIL_NOT_FOUND" in str(e):
                    st.error("No account found with this email address")
                else:
                    st.error(f"Error sending reset email: {str(e)}")
        else:
            st.error("Please enter your email address")


def get_current_user():
    """Get the current user's information"""
    if check_authentication():
        return {
            'email': st.session_state.user_email,
            'role': st.session_state.user_role,
            'user_id': st.session_state.get('user_id', None)
        }
    return None
