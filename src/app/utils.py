import streamlit as st
# from firestore_crud import FirestoreCRUD - removed to break circular import
# from user_authentication import UserAuthentication - removed to break circular import
import base64
from fpdf import FPDF
import io
from datetime import datetime
from data_models import MedicalRecord

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


def generate_medical_record_pdf(record: MedicalRecord) -> bytes:
    """Generate a PDF document from a medical record.
    
    Args:
        record (MedicalRecord): The medical record to convert to PDF
        
    Returns:
        bytes: The PDF document as bytes
    """
    class PDF(FPDF):
        def header(self):
            # Set up initial position
            initial_y = 8
            
            # Add horizontal line with some space below the header
            self.set_y(initial_y + 10)
            self.line(20, self.get_y(), 190, self.get_y())
            self.ln(20)  # Space after line
            
        def footer(self):
            self.set_y(-20)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    # Create PDF object
    pdf = PDF()
    # Set margins
    pdf.set_margins(left=20, top=30, right=20)
    pdf.set_auto_page_break(auto=True, margin=20)
    
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Content with improved spacing
    def add_section(title, content_list):
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, title, 0, 1)
        pdf.set_font('Helvetica', '', 12)
        for line in content_list:
            pdf.cell(0, 8, line, 0, 1)  # Reduced line height
        pdf.ln(5)  # Space between sections
    
    # Patient Information Section
    patient_info = [
        f'Name: {record.patient.name}'
    ]
    if record.patient.phone:
        patient_info.append(f'Phone: {record.patient.phone}')
    if record.patient.address:
        patient_info.append(f'Address: {record.patient.address}')
    add_section('Patient Information', patient_info)
    
    # Doctor Information Section
    if record.doctor:
        doctor_info = [
            f'Name: Dr. {record.doctor.name}',
            f'Location: {record.doctor.location}'
        ]
        add_section('Doctor Information', doctor_info)
    
    # Medical Test Section
    test_info = []
    total_test_price = 0
    for test in record.medical_tests:
        test_info.append(f'{test.name}: Rs. {test.price:,}')
        total_test_price += test.price or 0
    test_info.append(f'Total Test Price: Rs. {total_test_price:,}')
    test_info.append(f'Amount Paid: Rs. {record.payment.amount:,}')
    add_section('Medical Test Details', test_info)
    
    # Comments Section
    if record.comments:
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Additional Comments', 0, 1)
        pdf.set_font('Helvetica', '', 12)
        # Handle multi-line comments with proper wrapping
        pdf.multi_cell(0, 8, record.comments)
        pdf.ln(5)
    
    # Footer Information
    pdf.ln(5)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.cell(0, 8, f'Record Date: {record.date}', 0, 1)
    # Use user name if available, otherwise use email
    updated_by_display = st.session_state.get('user_name') or record.updated_by_email
    pdf.cell(0, 8, f'Updated by: {updated_by_display}', 0, 1)
    
    # Return PDF as bytes
    return bytes(pdf.output())

