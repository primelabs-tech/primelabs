import streamlit as st
# from firestore_crud import FirestoreCRUD - removed to break circular import
# from user_authentication import UserAuthentication - removed to break circular import

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


def is_project_owner(email):
    """Check if the user is the project owner"""
    # Define project owner email - this should be configured in secrets
    owner_email = st.secrets.get("project_owner_email", "owner@primelabs.com")
    return email == owner_email


@st.cache_resource
def get_firestore():
    from firestore_crud import FirestoreCRUD
    return FirestoreCRUD()


@st.cache_resource
def get_user_authentication():
    from user_authentication import UserAuthentication
    return UserAuthentication()


def get_pending_approval_html():
    return """
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
    """
