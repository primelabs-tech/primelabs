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


def format_date_time(date_value) -> str:
    """Format date to dd/mm/yyyy and time to 12hr format.
    
    Args:
        date_value: Date as string or datetime object
        
    Returns:
        Formatted date and time string
    """
    try:
        if isinstance(date_value, str):
            # Try parsing common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_value, fmt)
                    break
                except ValueError:
                    continue
            else:
                return str(date_value)  # Return as-is if parsing fails
        else:
            dt = date_value
        
        # Format: dd/mm/yyyy hh:mm AM/PM
        return dt.strftime("%d/%m/%Y %I:%M %p")
    except Exception:
        return str(date_value)


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
            self.line(15, self.get_y(), 195, self.get_y())
            self.ln(15)  # Space after line
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 7)
            self.cell(0, 8, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    # Create PDF object
    pdf = PDF()
    # Set margins
    pdf.set_margins(left=15, top=25, right=15)
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Page width for calculations
    page_width = 210 - 30  # A4 width minus margins (15 each side)
    half_width = page_width / 2
    
    # ===== PATIENT AND DOCTOR INFORMATION SIDE BY SIDE =====
    start_y = pdf.get_y()
    
    # Patient Information (Left side)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(half_width, 6, 'Patient Information', 0, 0)
    
    # Doctor Information (Right side) - only show header if doctor exists
    if record.doctor:
        pdf.cell(half_width, 6, 'Doctor Information', 0, 1)
    else:
        pdf.ln(6)
    
    # Patient details
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(half_width, 5, f'Name: {record.patient.name}', 0, 0)
    if record.doctor:
        pdf.cell(half_width, 5, f'Name: Dr. {record.doctor.name}', 0, 1)
    else:
        pdf.ln(5)
    
    if record.patient.phone:
        pdf.cell(half_width, 5, f'Phone: {record.patient.phone}', 0, 0)
        if record.doctor:
            pdf.cell(half_width, 5, f'Location: {record.doctor.location}', 0, 1)
        else:
            pdf.ln(5)
    elif record.doctor:
        pdf.cell(half_width, 5, '', 0, 0)  # Empty cell for patient
        pdf.cell(half_width, 5, f'Location: {record.doctor.location}', 0, 1)
    
    if record.patient.address:
        pdf.cell(half_width, 5, f'Address: {record.patient.address}', 0, 1)
    
    pdf.ln(6)
    
    # ===== MEDICAL TESTS SECTION =====
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'Medical Tests', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    
    # Get test names
    test_names = [test.name for test in record.medical_tests]
    
    # Calculate cell width for 4 columns (invisible table)
    tests_per_row = 4
    cell_width = page_width / tests_per_row
    
    # Display tests in rows of 4
    for i, test_name in enumerate(test_names):
        pdf.cell(cell_width, 5, f'- {test_name}', 0, 0)
        # New line after every 4 tests or at the end
        if (i + 1) % tests_per_row == 0:
            pdf.ln(5)
    
    # If last row wasn't complete, add new line
    if len(test_names) % tests_per_row != 0:
        pdf.ln(5)
    
    pdf.ln(4)
    
    # ===== PAYMENT SECTION =====
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'Payment Details', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 5, f'Amount Paid: Rs. {record.payment.amount:,}', 0, 1)
    
    pdf.ln(4)
    
    # ===== COMMENTS SECTION =====
    if record.comments:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, 'Additional Comments', 0, 1)
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(0, 5, record.comments)
        pdf.ln(4)
    
    # ===== FOOTER INFORMATION =====
    pdf.ln(3)
    pdf.set_font('Helvetica', 'I', 8)
    formatted_date = format_date_time(record.date)
    # Use user name if available, otherwise use email
    updated_by_display = st.session_state.get('user_name') or record.updated_by_email
    # Date and Patient care incharge on same line
    pdf.cell(half_width, 5, f'Date: {formatted_date}', 0, 0)
    pdf.cell(half_width, 5, f'Patient care incharge: {updated_by_display}', 0, 1)
    
    # Return PDF as bytes
    return bytes(pdf.output())

