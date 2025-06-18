import streamlit as st
import pyrebase
import firebase_admin
from firebase_admin import auth, credentials
from google.oauth2 import service_account

from data_models import User


# Initialize Firebase Admin SDK
def initialize_firebase_admin():
    """Initialize Firebase Admin SDK if not already initialized"""
    if not firebase_admin._apps:
        try:
            # Create credentials from Streamlit secrets
            credentials_dict = {
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
            
            cred = credentials.Certificate(credentials_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")

# Initialize Firebase Admin SDK
initialize_firebase_admin()

firebase_config = {
    "apiKey": st.secrets["web_api_key"],
    "authDomain": f"{st.secrets['project_id']}.firebaseapp.com",
    "databaseURL": f"https://{st.secrets['project_id']}-default-rtdb.firebaseio.com/",
    "projectId": st.secrets["project_id"],
    "storageBucket": f"{st.secrets['project_id']}.firebasestorage.app",
    "messagingSenderId": st.secrets.get("messaging_sender_id", ""),
    "appId": st.secrets.get("app_id", "")
}

firebase = pyrebase.initialize_app(firebase_config)
firebase_auth = firebase.auth()


def verify_token_validity():
    """Verify if the current token is still valid"""
    if not hasattr(st.session_state, 'user_token') or not st.session_state.user_token:
        return False
    
    try:
        decoded_token = auth.verify_id_token(st.session_state.user_token)
        return True
    except Exception as e:
        # Token is invalid or expired
        return False


def check_authentication():
    """Check if user is authenticated and token is valid"""
    # Check basic authentication state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    
    # If user claims to be authenticated, verify token validity
    if st.session_state.authenticated:
        if not verify_token_validity():
            # Token expired or invalid, logout user
            logout_silently()
            return False
    
    return st.session_state.authenticated


def test_firebase_config():
    """Test Firebase configuration and connectivity"""
    try:
        # Test Firebase Admin SDK connection
        from firebase_admin import auth as admin_auth
        
        # Test pyrebase connection
        test_config = {
            "apiKey": st.secrets["web_api_key"],
            "authDomain": f"{st.secrets['project_id']}.firebaseapp.com",
            "databaseURL": f"https://{st.secrets['project_id']}-default-rtdb.firebaseio.com/",
            "projectId": st.secrets["project_id"],
            "storageBucket": f"{st.secrets['project_id']}.firebasestorage.app",
            "messagingSenderId": st.secrets.get("messagingSenderId", ""),
            "appId": st.secrets.get("appId", "")
        }
        
        test_firebase = pyrebase.initialize_app(test_config)
        test_auth = test_firebase.auth()
        
        st.success("✅ Firebase configuration appears to be correct")
        st.info(f"Project ID: {st.secrets['project_id']}")
        st.info(f"Auth Domain: {st.secrets['project_id']}.firebaseapp.com")
        
        return True
    except Exception as e:
        st.error(f"❌ Firebase configuration error: {str(e)}")
        return False


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
                    
                    # Check approval status before proceeding
                    if not check_user_approval_status(user_email):
                        # Set minimal session state for pending users
                        st.session_state.authenticated = True
                        st.session_state.user_email = user_email
                        st.session_state.user_role = User.DOCTOR  # Temporary role
                        st.session_state.user_token = user['idToken']
                        st.session_state.user_id = decoded_token['uid']
                        st.rerun()
                        return
                    
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
                    error_message = str(e)
                    st.error(f"Full error details: {error_message}")
                    
                    # Log the error for debugging
                    import logging
                    logging.error(f"Authentication error: {error_message}")
                    
                    if "INVALID_EMAIL" in error_message:
                        st.error("Invalid email format")
                    elif "EMAIL_NOT_FOUND" in error_message:
                        st.error("No account found with this email")
                    elif "INVALID_PASSWORD" in error_message or "INVALID_LOGIN_CREDENTIALS" in error_message:
                        st.error("Incorrect password or invalid login credentials")
                    elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_message:
                        st.error("Too many failed attempts. Please try again later")
                    elif "USER_DISABLED" in error_message:
                        st.error("This user account has been disabled")
                    elif "WEAK_PASSWORD" in error_message:
                        st.error("Password is too weak. Please choose a stronger password")
                    else:
                        st.error(f"Authentication failed: {error_message}")
                        
                    # Additional debugging information
                    st.info("Debugging tips:")
                    st.info("1. Make sure you're using the correct email and password")
                    st.info("2. Try registering a new account if you haven't already")
                    st.info("3. Check if your email requires verification")
                    st.info("4. Ensure you have a stable internet connection")
            else:
                st.error("Please enter both email and password")
    
    else:  # Register mode
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("Register"):
            if email and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match")
                    return
                    
                try:
                    # Create user with Firebase
                    user = firebase_auth.create_user_with_email_and_password(email, password)
                    
                    # Store user with default role (Doctor) - only owner can change roles
                    from firestore_crud import FirestoreCRUD
                    db = FirestoreCRUD(use_admin_sdk=True)
                    
                    user_data = {
                        "email": email,
                        "role": User.DOCTOR,  # Default role for all new users
                        "created_at": st.session_state.get('timestamp', 'unknown'),
                        "status": "pending_approval"  # Require owner approval
                    }
                    
                    db.create_doc("users", user_data, doc_id=user['localId'])
                    
                    st.success("Registration successful! Your account has been created with Doctor role. Contact the system administrator to request role changes.")
                    
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
            user_data = user_docs[0]
            return user_data.get("role", User.DOCTOR)  # Default to DOCTOR if role not found
        else:
            # Fallback to hardcoded mapping for existing users (project owner or legacy users)
            if is_project_owner(email):
                return User.MANAGER  # Project owner gets manager role
            
            role_mapping = {
                "manager@primelabs.com": User.MANAGER,
                "supervisor@primelabs.com": User.SUPERVISOR,
                "doctor@primelabs.com": User.DOCTOR
            }
            return role_mapping.get(email, User.DOCTOR)
            
    except Exception as e:
        st.error(f"Error getting user role: {str(e)}")
        return User.DOCTOR  # Default role


def logout_silently():
    """Logout the user without triggering rerun"""
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.user_email = None
    st.session_state.user_token = None
    st.session_state.user_id = None


def logout():
    """Logout the user"""
    logout_silently()
    st.rerun()


def check_user_approval_status(email):
    """Check if user account is approved"""
    # First verify token is still valid
    if not verify_token_validity():
        # Token expired, user will be logged out by check_authentication
        return False
    
    try:
        from firestore_crud import FirestoreCRUD
        db = FirestoreCRUD(use_admin_sdk=True)
        
        # Skip check for project owner
        if is_project_owner(email):
            return True
        
        # Get user status from Firestore
        user_docs = db.get_docs("users", filters=[("email", "==", email)])
        
        if user_docs:
            user_data = user_docs[0]
            status = user_data.get("status", "active")
            return status == "active"
        else:
            # For legacy users not in Firestore, allow access
            legacy_emails = ["manager@primelabs.com", "supervisor@primelabs.com", "doctor@primelabs.com"]
            return email in legacy_emails
            
    except Exception as e:
        st.error(f"Error checking user status: {str(e)}")
        return False


def require_auth(required_role: User = None):
    """Check if user is authenticated and has required role"""
    if not check_authentication():
        return False
    
    # Check if user account is approved (this also verifies token validity)
    if not check_user_approval_status(st.session_state.user_email):
        show_pending_approval_screen()
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


def is_project_owner(email):
    """Check if the user is the project owner"""
    # Define project owner email - this should be configured in secrets
    owner_email = st.secrets.get("project_owner_email", "owner@primelabs.com")
    return email == owner_email


def require_owner():
    """Check if current user is the project owner"""
    if not check_authentication():
        return False
    
    if not is_project_owner(st.session_state.user_email):
        st.error("Access denied. Only the project owner can access this feature.")
        return False
    
    return True


def admin_user_management():
    """Admin interface for managing user roles - only accessible by project owner"""
    if not require_owner():
        return
    
    st.header("User Management (Admin Only)")
    
    try:
        from firestore_crud import FirestoreCRUD
        db = FirestoreCRUD(use_admin_sdk=True)
        
        # Get all users from Firestore
        users = db.get_docs("users")
        
        if not users:
            st.info("No users found in the system.")
            return
        
        st.subheader("Manage User Roles")
        
        # Display users in a table format
        for i, user_doc in enumerate(users):
            user_data = user_doc
            email = user_data.get('email', 'Unknown')
            current_role = user_data.get('role', User.DOCTOR)
            status = user_data.get('status', 'active')
            
            # Skip the owner's own account
            if is_project_owner(email):
                continue
            
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    st.text(f"📧 {email}")
                
                with col2:
                    st.text(f"Status: {status}")
                
                with col3:
                    new_role = st.selectbox(
                        "Role",
                        [User.DOCTOR, User.SUPERVISOR, User.MANAGER],
                        index=[User.DOCTOR, User.SUPERVISOR, User.MANAGER].index(current_role),
                        key=f"role_{i}"
                    )
                
                with col4:
                    if st.button("Update", key=f"update_{i}"):
                        try:
                            # Find the document ID for this user
                            user_docs = db.get_docs("users", filters=[("email", "==", email)])
                            if user_docs:
                                doc_id = user_docs[0].get('id')  # Assuming the doc has an id field
                                # Update user role and status
                                update_data = {
                                    "role": new_role,
                                    "status": "active",
                                    "updated_by": st.session_state.user_email,
                                    "updated_at": st.session_state.get('timestamp', 'unknown')
                                }
                                
                                # Find all documents with this email and update them
                                all_user_docs = db.get_docs("users", filters=[("email", "==", email)])
                                for user_doc in all_user_docs:
                                    # Get the document reference and update
                                    db.update_doc("users", user_doc.get('id', ''), update_data)
                                
                                st.success(f"Updated {email} to {new_role}")
                                st.rerun()
                            else:
                                st.error("User document not found")
                        except Exception as e:
                            st.error(f"Error updating user: {str(e)}")
                
                st.divider()
        
        # Pending approvals section
        st.subheader("Pending Approvals")
        pending_users = [user for user in users if user.get('status') == 'pending_approval']
        
        if pending_users:
            for user_data in pending_users:
                email = user_data.get('email', 'Unknown')
                if not is_project_owner(email):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.text(f"📧 {email} - Pending approval")
                    with col2:
                        if st.button("Approve", key=f"approve_{email}"):
                            try:
                                # Update status to active
                                user_docs = db.get_docs("users", filters=[("email", "==", email)])
                                for user_doc in user_docs:
                                    update_data = {
                                        "status": "active",
                                        "approved_by": st.session_state.user_email,
                                        "approved_at": st.session_state.get('timestamp', 'unknown')
                                    }
                                    db.update_doc("users", user_doc.get('id', ''), update_data)
                                
                                st.success(f"Approved {email}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error approving user: {str(e)}")
        else:
            st.info("No pending approvals.")
            
    except Exception as e:
        st.error(f"Error loading user management: {str(e)}")


def show_token_expired_message():
    """Show token expiration message"""
    st.warning("⏰ Your session has expired. Please login again to continue.")


def show_pending_approval_screen():
    """Show pending approval screen for users waiting for approval"""
    # Check if token is still valid for pending users
    if not verify_token_validity():
        show_token_expired_message()
        # Show login form instead of pending screen
        login_form()
        return
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1>🕐 Account Pending Approval</h1>
        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 0.5rem; padding: 1.5rem; margin: 2rem 0;">
            <h3 style="color: #856404;">Your account is waiting for administrator approval</h3>
            <p style="color: #856404; font-size: 1.1rem;">
                Your registration was successful, but your account needs to be approved by the project administrator 
                before you can access the PrimeLabs system.
            </p>
        </div>
        
        <div style="margin: 2rem 0;">
            <h4>What happens next?</h4>
            <ul style="text-align: left; display: inline-block;">
                <li>The system administrator will review your registration</li>
                <li>You will receive access once your account is approved</li>
                <li>This process typically takes 1-2 business days</li>
            </ul>
        </div>
        
        <div style="background-color: #d1ecf1; border: 1px solid #bee5eb; border-radius: 0.5rem; padding: 1rem; margin: 2rem 0;">
            <p style="color: #0c5460; margin-bottom: 0.5rem;"><strong>Need immediate access?</strong></p>
            <p style="color: #0c5460;">Contact the system administrator at: <code>admin@primelabs.com</code></p>
        </div>
        
        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 0.5rem; padding: 1rem; margin: 2rem 0;">
            <p style="color: #6c757d; margin-bottom: 0.5rem;">💡 <strong>Tip:</strong></p>
            <p style="color: #6c757d;">You can refresh this page periodically to check if your account has been approved.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Add logout and refresh buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            logout()


def show_admin_menu():
    """Show admin menu in sidebar if user is project owner"""
    if check_authentication() and is_project_owner(st.session_state.user_email):
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔧 Admin Panel")
        
        if st.sidebar.button("Manage Users"):
            st.session_state.show_admin = True
        
        if st.sidebar.button("Hide Admin Panel"):
            st.session_state.show_admin = False
