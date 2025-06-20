import time
import logging
from datetime import datetime

import streamlit as st
from data_models import (
    MedicalRecord,
    Patient, 
    Doctor, 
    MedicalTest,  
    Payment, 
    UserRole,
    DBCollectionNames,
    AuthorizationStatus,
)
from user_authentication import UserAuthentication
from utils import (
    get_firestore, 
    get_user_authentication,
    get_pending_approval_html,
    is_project_owner,
)
from logger import logger


db = get_firestore()
USER_DB_COLLECTION = "users"


class MedicalRecordForm:
    def __init__(self):
        self.database_collection = DBCollectionNames(st.secrets["database_collection"]).value
    
    def validate_phone_number(self, phone):
        """Validate phone number format"""
        if not phone:
            return False, "Phone number is required"
        # Remove spaces, dashes, parentheses
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        if len(cleaned_phone) < 10:
            return False, "Phone number must be at least 10 digits"
        return True, ""
    
    def validate_patient_name(self, name):
        """Validate patient name"""
        if not name or len(name.strip()) < 2:
            return False, "Patient name must be at least 2 characters"
        return True, ""
    
    def validate_doctor_info(self, name, location):
        """Validate doctor information"""
        if not name or len(name.strip()) < 2:
            return False, "Doctor name must be at least 2 characters"
        if not location or len(location.strip()) < 2:
            return False, "Doctor location must be at least 2 characters"
        return True, ""
    
    def show_success_message(self, medical_record):
        """Show enhanced success message with record details"""
        st.success("✅ Medical record successfully saved!")
        
        with st.expander("📋 View Submitted Record", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Patient Information:**")
                st.write(f"• Name: {medical_record.patient.name}")
                if medical_record.patient.phone:
                    st.write(f"• Phone: {medical_record.patient.phone}")
                if medical_record.patient.address:
                    st.write(f"• Address: {medical_record.patient.address}")
                
                st.markdown("**Test Information:**")
                st.write(f"• Test: {medical_record.medical_test.name}")
                st.write(f"• Price: ₹{medical_record.medical_test.price}")
            
            with col2:
                if medical_record.doctor:
                    st.markdown("**Referring Doctor:**")
                    st.write(f"• Name: {medical_record.doctor.name}")
                    st.write(f"• Location: {medical_record.doctor.location}")
                
                st.markdown("**Payment & Other:**")
                st.write(f"• Payment: ₹{medical_record.payment.amount}")
                st.write(f"• Date: {medical_record.date}")
                if medical_record.comments:
                    st.write(f"• Comments: {medical_record.comments}")
        
        # Auto-hide after 5 seconds
        time.sleep(5)
        # Reset processing state before rerun
        st.session_state.processing_submission = False
        st.rerun()
    
    def render(self, is_authorized: bool = False):
        if not is_authorized:
            st.warning("🔐 You need to be logged in and approved to access this form.")
            return
        
        # Header with improved styling
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="color: #1f77b4; margin-bottom: 10px;">🏥 Medical Test Entry</h1>
            <p style="color: #666; font-size: 16px;">Complete the form below to register a new medical test</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize session state for form validation and submission tracking
        if 'form_errors' not in st.session_state:
            st.session_state.form_errors = {}
        if 'processing_submission' not in st.session_state:
            st.session_state.processing_submission = False
        
        # Form container with better styling
        with st.container():
            st.markdown("---")
            
            # PATIENT INFORMATION SECTION
            with st.expander("👤 Patient Information", expanded=True):
                st.markdown("**Required Information**")
                
                patient_name = st.text_input(
                    label="Patient's Full Name *",
                    placeholder="Enter patient's full name", 
                    help="📝 Enter the complete name of the patient",
                    key="patient_name"
                )
                
                # Real-time validation for patient name
                if patient_name:
                    is_valid, error_msg = self.validate_patient_name(patient_name)
                    if not is_valid:
                        st.error(f"❌ {error_msg}")
                    else:
                        st.success("✅ Valid name")
                
                st.markdown("**Optional Information**")
                col1, col2 = st.columns(2)
                
                with col1:
                    phone_available = st.checkbox("📞 Include Phone Number", key="phone_checkbox")
                    if phone_available:
                        patient_phone = st.text_input(
                            label="Patient's Phone Number",
                            placeholder="e.g., +91 98765 43210", 
                            help="📱 Enter 10+ digit phone number",
                            key="patient_phone"
                        )
                        
                        # Real-time phone validation
                        if patient_phone:
                            is_valid, error_msg = self.validate_phone_number(patient_phone)
                            if not is_valid:
                                st.error(f"❌ {error_msg}")
                            else:
                                st.success("✅ Valid phone number")
                
                with col2:
                    address_available = st.checkbox("🏠 Include Address", key="address_checkbox")
                    if address_available:
                        patient_address = st.text_area(
                            label="Patient's Address",
                            placeholder="Enter complete address...", 
                            help="🏠 Enter the patient's residential address",
                            height=100,
                            key="patient_address"
                        )
            
            # REFERRAL INFORMATION SECTION
            with st.expander("👨‍⚕️ Referral Information", expanded=False):
                through_referral = st.checkbox("📋 Patient referred by a doctor", key="referral_checkbox")
                
                if through_referral:
                    st.markdown("**Doctor Details**")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        doctor_name = st.text_input(
                            label="Referring Doctor's Name *",
                            placeholder="Dr. [Name]", 
                            help="👨‍⚕️ Enter the full name of the referring doctor",
                            key="doctor_name"
                        )
                    
                    with col2:
                        doctor_location = st.text_input(
                            label="Doctor's Clinic/Hospital *",
                            placeholder="Clinic/Hospital name and location", 
                            help="🏥 Enter the clinic or hospital details",
                            key="doctor_location"
                        )
                    
                    # Validate doctor info if provided
                    if through_referral and doctor_name and doctor_location:
                        is_valid, error_msg = self.validate_doctor_info(doctor_name, doctor_location)
                        if not is_valid:
                            st.error(f"❌ {error_msg}")
                        else:
                            st.success("✅ Doctor information valid")
            
            # TEST INFORMATION SECTION
            with st.expander("🔬 Test Information", expanded=True):
                TEST_PRICES = {
                    'Blood Test': 200,
                    'Urine Test': 150,
                    'X-Ray': 500,
                    'MRI': 1500,
                    'CT Scan': 1200,
                    'Ultrasound': 800,
                    'ECG': 300
                }
                
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    test_name = st.selectbox(
                        label='🔬 Medical Test Type *',
                        options=list(TEST_PRICES.keys()),
                        help='Select the type of medical test to be performed',
                        key="test_type"
                    )
                
                with col2:
                    test_price = st.text_input(
                        label='💰 Test Price',
                        disabled=True,
                        value=f"₹{TEST_PRICES[test_name]:,}",
                        help="Automatically calculated based on test type"
                    )
                
                with col3:
                    st.metric(
                        label="Price",
                        value=f"₹{TEST_PRICES[test_name]:,}",
                        help="Test price in Indian Rupees"
                    )
            
            # PAYMENT INFORMATION SECTION
            with st.expander("💳 Payment Information", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Payment Amount**")
                    payment_amount = st.number_input(
                        label='Payment Amount (₹) *',
                        min_value=0,
                        max_value=10000,
                        step=50,
                        value=0,
                        help='💰 Enter the payment amount received',
                        key="payment_amount"
                    )
                    
                    # Show payment status
                    if payment_amount > 0:
                        test_price_num = TEST_PRICES[test_name]
                        if payment_amount >= test_price_num:
                            st.success(f"✅ Full payment received (₹{payment_amount:,})")
                        else:
                            remaining = test_price_num - payment_amount
                            st.warning(f"⚠️ Partial payment. Discount: ₹{remaining:,}")
                    else:
                        st.info("💡 Please enter the payment amount")
                
                with col2:
                    st.markdown("**Additional Notes**")
                    comments = st.text_area(
                        label='Comments/Notes',
                        placeholder="Any additional notes or comments...",
                        help='📝 Enter any relevant comments about the test or patient',
                        height=100,
                        key="comments"
                    )
            
            st.markdown("---")
            
            # FORM SUBMISSION
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                # Validate required fields before enabling submit
                can_submit = (
                    patient_name and 
                    len(patient_name.strip()) >= 2 and
                    payment_amount > 0 and
                    not st.session_state.processing_submission  # Disable while processing
                )
                
                if through_referral:
                    can_submit = can_submit and doctor_name and doctor_location
                
                if phone_available:
                    can_submit = can_submit and patient_phone and self.validate_phone_number(patient_phone)[0]
                
                # Show processing status if submitting
                if st.session_state.processing_submission:
                    button_label = '⏳ Processing...'
                    help_text = "Please wait while your record is being saved"
                else:
                    button_label = '💾 Submit Medical Record'
                    help_text = "Complete all required fields to enable submission" if not can_submit else "Click to save the medical record"
                
                submit_button = st.button(
                    label=button_label,
                    disabled=not can_submit,
                    use_container_width=True,
                    help=help_text
                )
            
            # Show required fields reminder
            if not can_submit:
                st.info("📋 **Required fields:** Patient Name, Payment Amount" + 
                       (" + Doctor Details (if referral selected)" if through_referral else "") +
                       (" + Valid Phone Number (if phone selected)" if phone_available else ""))
        
        # FORM SUBMISSION LOGIC
        if submit_button:
            # Set processing state to disable the button
            st.session_state.processing_submission = True
            try:
                with st.spinner('💾 Saving medical record...'):
                    # Create patient object
                    patient = Patient(name=patient_name.strip())
                    if phone_available and patient_phone:
                        patient.phone = patient_phone
                    if address_available and patient_address:
                        patient.address = patient_address.strip()
                    
                    # Create doctor object if referral
                    referring_doctor = None
                    if through_referral:
                        referring_doctor = Doctor(
                            name=doctor_name.strip(), 
                            location=doctor_location.strip()
                        )
                    
                    # Create medical record
                    medical_entry = MedicalRecord(
                        patient=patient,
                        doctor=referring_doctor,
                        medical_test=MedicalTest(name=test_name, price=TEST_PRICES[test_name]),
                        payment=Payment(amount=payment_amount),
                        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        comments=comments.strip() if comments else "",
                        updated_by=st.session_state.user_role,
                        updated_by_email=st.session_state.user_email
                    )
                    
                    # Save to database
                    db.create_doc(
                        self.database_collection, 
                        medical_entry.model_dump(mode="json")
                    )
                
                # Show success message (outside spinner context)
                self.show_success_message(medical_entry)
                    
                    # Clear form by rerunning (optional)
                    # st.rerun()

            except Exception as e:
                # Reset processing state on error
                st.session_state.processing_submission = False
                st.error(f"❌ **Error saving record:** {str(e)}")
                st.error("Please try again or contact system administrator if the problem persists.")
                logger.error(f"Error saving medical record: {str(e)}")


class OpeningScreen:
    def __init__(self, user_auth: UserAuthentication):
        self.user_auth = user_auth
        self.db = get_firestore()
    
    def show_pending_approval_screen(self):
        """Show pending approval screen for users waiting for approval"""
        # html = get_pending_approval_html()
        # st.markdown(html, unsafe_allow_html=True)
        from utils import show_pending_approval_page
        show_pending_approval_page()
        
        # Add logout and refresh buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("🔄 Refresh Status", use_container_width=True):
                st.rerun()
        with col3:
            if st.button("🚪 Logout", use_container_width=True):
                self.user_auth.logout()
                st.rerun()
    
    def opening_screen(self):
        """Display login form and handle authentication"""
        st.title("Login")
        
        auth_mode = st.radio("Choose an option:", ["Login", "Register", "Reset Password"], horizontal=True)

        match auth_mode:
            case "Reset Password":
                self.reset_password_screen()
            case "Register":
                self.register_screen()
            case "Login":
                self.login_screen()
            case _:
                st.error("Invalid option")

    def login_screen(self):
        """Display login form and handle authentication"""
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        
        if st.button("Sign In"):
            if not email or not password:
                st.show_error_message("MISSING_FIELDS")
                return
            
            is_logged_in, error_message = self.user_auth.login(email, password)
            if is_logged_in:
                st.success("Login successful!")
                st.rerun()
            else:
                self.show_error_message(error_message, "Login")
 
    def register_screen(self):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Register"):
            if not all([email, password, confirm_password]):
                st.show_error_message("MISSING_FIELDS")
                return
            if password != confirm_password:
                st.show_error_message("PASSWORD_MISMATCH")
                return 
            is_registered, error_message = self.user_auth.register(email, password)
            if is_registered:
                st.success("Registration successful!")
            else:
                self.show_error_message(error_message, "Register User")

    def reset_password_screen(self):
        """Handle password reset"""
        st.subheader("Reset Password")
        reset_email = st.text_input("Enter your email address")
        
        if st.button("Send Reset Email"):
            if not reset_email:
                self.show_error_message("MISSING_EMAIL")
                return
            is_email_sent, error_message = self.user_auth.reset_password(reset_email)
            if is_email_sent:
                st.success("Password reset email sent! Check your inbox.")
            else:
                self.show_error_message(error_message, "Email Reset")

    def show_error_message(self, 
                           error_message: str,
                           operation: str = "Operation"):
        error_message = ""
        if "MISSING_FIELDS" in error_message:
            error_message = "Please fill in all fields"
        elif "PASSWORD_MISMATCH" in error_message:
            error_message = "Passwords do not match"
        elif "MISSING_EMAIL" in error_message:
            error_message = "Please enter your email address"
        elif "EMAIL_NOT_FOUND" in error_message:
            error_message = "No account found with this email address"
        elif "EMAIL_EXISTS" in error_message:
            error_message = "An account with this email already exists"
        elif "WEAK_PASSWORD" in error_message:
            error_message = "Password should be at least 6 characters"
        elif "INVALID_EMAIL" in error_message:
            error_message = "Invalid email format"
        elif "EMAIL_NOT_FOUND" in error_message:
            error_message = "No account found with this email"
        elif "INVALID_PASSWORD" in error_message or "INVALID_LOGIN_CREDENTIALS" in error_message:
            error_message = "Incorrect password or invalid login credentials"
        elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_message:
            error_message = "Too many failed attempts. Please try again later"
        elif "USER_DISABLED" in error_message:
            error_message = "This user account has been disabled"
        elif "WEAK_PASSWORD" in error_message:
            error_message = "Password is too weak. Please choose a stronger password"
        else:
            error_message = f"{operation} failed"            
        
        st.error(error_message)

    def token_expired_screen(self):
        """Show token expired message"""
        st.warning("⏰ Your session has expired. Please login again to continue.")    
        self.opening_screen()
        return

    def show_admin_menu(self):
        """Show admin menu in sidebar if user is project owner"""
        if self.user_auth.check_authentication() and is_project_owner(st.session_state.user_email):
            st.sidebar.markdown("---")
            st.sidebar.subheader("🔧 Admin Panel")
        
        if st.sidebar.button("Manage Users"):
            st.session_state.show_admin = True
        
        if st.sidebar.button("Hide Admin Panel"):
            st.session_state.show_admin = False

    def show_admin_user_management(self):
        """Admin interface for managing user roles - only accessible by project owner"""
        if self.user_auth.is_current_user_owner() != AuthorizationStatus.OWNER:
            return
        
        st.header("User Management (Admin Only)")
        
        try:
            users = self.db.get_docs(USER_DB_COLLECTION)
            
            if not users:
                st.info("No users found in the system.")
                return
            
            st.subheader("Manage User Roles")
            
            # Display users in a table format
            for i, user_doc in enumerate(users):
                user_data = user_doc
                email = user_data.get('email', 'Unknown')
                current_role = user_data.get('role', UserRole.EMPLOYEE)
                status = user_data.get('status', AuthorizationStatus.PENDING_APPROVAL)
                
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
                            options=list(UserRole),
                            index=list(UserRole).index(current_role),
                            key=f"role_{i}"
                        )
                    
                    with col4:
                        if st.button("Update", key=f"update_{i}"):
                            try:
                                # We already have the user document, no need to search again
                                doc_id = user_data.get('id') # Assuming the doc has an id field
                                if doc_id:
                                    # Update user role and status
                                    update_data = {
                                        "role": new_role,
                                        "status": "active",
                                        "updated_by": st.session_state.user_email,
                                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    
                                    # Update the document directly using the ID we already have
                                    self.db.update_doc(USER_DB_COLLECTION, doc_id, update_data)
                                    
                                    st.success(f"Updated {email} to {new_role}")
                                    st.rerun()
                                else:
                                    st.error("User document ID not found")
                            except Exception as e:
                                st.error(f"Error updating user: {str(e)}")
                    
                    st.divider()
            
            # Pending approvals section
            st.subheader("Pending Approvals")
            pending_users = [user for user in users if user.get('status') == 'pending_approval']
            
            if not pending_users:
                st.info("No pending approvals found.")
                return
            
            for user_data in pending_users:
                email = user_data.get('email', 'Unknown')
                if is_project_owner(email):
                    continue
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"📧 {email} - Pending approval")
                with col2:
                    if st.button("Approve", key=f"approve_{email}"):
                        try:
                            # Update status to active using the user data we already have
                            doc_id = user_data.get('id')
                            if not doc_id:
                                st.error("User document ID not found")
                                return
                            
                            update_data = {
                                "status": "active",
                                "approved_by": st.session_state.user_email,
                                "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            self.db.update_doc("users", doc_id, update_data)
                            
                            st.success(f"Approved {email}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error approving user: {str(e)}")
          
                
        except Exception as e:
            st.error(f"Error loading user management: {str(e)}")

class PrimeLabsUI:
    def __init__(self):
        self.user_auth = get_user_authentication()
        self.opening_screen = OpeningScreen(self.user_auth)

    def render(self):
        if st.session_state.get('user_email') and not self.user_auth.verify_token_validity():
            self.opening_screen.token_expired_screen()
            return
        
        is_authenticated = self.user_auth.check_authentication()
        is_approved = self.user_auth.check_user_approval_status(st.session_state.user_email)
        if is_authenticated and not is_approved:
            self.opening_screen.show_pending_approval_screen()
            return


        with st.sidebar:
            st.title('PrimeLabs')
            st.write('Primelabs management system')
            
            # Add login/logout buttons in sidebar
            if is_authenticated:
                st.write(f"Logged in as: {st.session_state.user_email}")
                st.write(f"Role: {st.session_state.user_role}")
                if st.button("Logout"):
                    self.user_auth.logout()
                    st.rerun()
                
                # Show admin menu if user is project owner
                self.opening_screen.show_admin_menu()
            else:
                self.opening_screen.opening_screen()
            
            st.session_state.times_loaded = st.session_state.get('times_loaded', 0)
            st.session_state.times_loaded += 1
            st.write(f"Times loaded: {st.session_state.times_loaded}")
            
        # Show admin panel if requested
        if st.session_state.get('show_admin', False):
            self.opening_screen.show_admin_user_management()
        else:
            authorization = self.user_auth.require_authorization()
            MedicalRecordForm().render(authorization==AuthorizationStatus.APPROVED)


if __name__ == '__main__':
    ui = PrimeLabsUI()
    ui.render()
