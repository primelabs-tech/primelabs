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
    owner_email1 = st.secrets.get("project_owner_email", None)
    owner_email2 = st.secrets.get("project_owner_email_2", None)
    return email in [owner_email1, owner_email2]


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
    <div style="text-align: center; padding: 1rem;">
        <h1>🕐 Account Pending Approval</h1>
    </div>
    """


def show_pending_approval_page():
    """Display the pending approval page using native Streamlit components"""
    st.markdown("### 🕐 Account Pending Approval")
    
    st.warning("""
    **Your account is waiting for administrator approval**
    
    Your registration was successful, but your account needs to be approved by the project administrator 
    before you can access the PrimeLabs system.
    """)
    
    st.markdown("#### What happens next?")
    st.markdown("""
    - The system administrator will review your registration
    - You will receive access once your account is approved  
    - This process typically takes 1-2 business days
    """)
    
    st.info("""
    **Need immediate access?**
    
    Contact the system administrator at: `admin@primelabs.com`
    """)
    
    st.markdown("""
    > 💡 **Tip:** You can refresh this page periodically to check if your account has been approved.
    """)

