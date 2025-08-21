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
    ExpenseRecord,
    ExpenseType,
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
        
        # Add centered PDF download button
        from utils import generate_medical_record_pdf
        
        pdf_bytes = generate_medical_record_pdf(medical_record)
        filename = f"medical_record_{medical_record.patient.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        left_col, center_col, right_col = st.columns([1, 2, 1])
        with center_col:
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                help="Download the medical record as a PDF file",
                use_container_width=True
            )
        
        st.markdown("---")
    
    def clear_form_fields(self):
        """Clear all form fields from session state"""
        form_keys_to_clear = [
            'patient_name', 'patient_phone', 'patient_address',
            'phone_checkbox', 'address_checkbox', 'referral_checkbox',
            'doctor_name', 'doctor_location', 'test_type', 'payment_amount',
            'comments'
        ]
        for key in form_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
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
        if 'show_success' not in st.session_state:
            st.session_state.show_success = False
        if 'last_record' not in st.session_state:
            st.session_state.last_record = None
        
        # Show success message if we just completed a submission
        if st.session_state.show_success and st.session_state.last_record:
            self.show_success_message(st.session_state.last_record)
            
            # Add button to start new entry
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("➕ Add New Record", use_container_width=True):
                    # Clear success state and form
                    st.session_state.show_success = False
                    st.session_state.last_record = None
                    self.clear_form_fields()
                    st.rerun()
            return
        
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
                    "T3T4TSH": 500,
                    "T3T4TSH LAL PATH": 700,
                    "VITAMIN-B12": 1200,
                    "URINE C/S": 500,
                    "HBA1C": 600,
                    "AFB": 500,
                    "CSF R/M": 2000,
                    "G6PD": 1200,
                    "THROAT SWAB R/M": 300,
                    "BIOPSY AS SIZE": 1500,
                    "D2 HORMONES T3T4PRL LH FSH": 1500,
                    "BODY BLOOD": 3000,
                    "CA-125": 1250,
                    "CA-19.9": 1200,
                    "HLA": 2200,
                    "PUS CULTURE": 600,
                    "PROLACTIN-PRL": 600,
                    "TESTO-STERONE LEVEL": 700,
                    "OESTROGEN/PROGESTRONE/TESTROGEN E": 1100,
                    "GENE-EXPERT (CBNAAT)": 4000,
                    "CBC": 250,
                    "BLOOD GROUP": 50,
                    "WIDAL": 100,
                    "HB,TLC,DLC,ESR,": 200,
                    "CREATININE": 150,
                    "UREA": 150,
                    "SGOT": 150,
                    "SGPT": 150,
                    "LFT": 600,
                    "KFT/RFT": 700,
                    "CRP(QUANTITATIVE)": 500,
                    "BLOOD SUGAR FASTING,PP,RANDOM (RS 50)": 150,
                    "LIPID PROFILE": 500,
                    "URINE R/M": 300,
                    "SEMEN TEST": 300,
                    "NX TEST (MONTEX)": 80,
                    "HIV": 350,
                    "HBSAG": 250,
                    "HCV": 350,
                    "RA(QUANTITAVE)": 500,
                    "MP BY KIT": 200,
                    "MF": 500,
                    "ABO/RH": 50,
                    "VIDAL": 900,
                    "HB": 1700,
                    "ESR": 1700,
                    "URIC ACID": 150,
                    "CALCIUM": 150,
                    "TOTAL PROTEN,ALBUMIN,GLB": 150,
                    "TOTAL CHOLESTEROL": 150,
                    "TG": 150,
                    "DENGUE PROFILE": 1200,
                    "TROP-I": 700,
                    "TROP-T": 1200,
                    "MP BY SMEAR": 100,
                    "VDRL": 250,
                    "TYPHIDOT": 250,
                    "BT,CT": 100,
                    "PT,PC,INR": 500,
                    "ASO(QUALITATIVE)": 500,
                    "ALK PHOSPHATASE": 150,
                    "HBAEG": 500,
                    "ECTOLYTE": 400,
                    "CBC LAB(RET)": 70,
                    "UFMAC": 3000,
                    "IGE LEVEL": 900,
                    "ACID PHOSPHATASE": 600,
                    "AMYLASE LIPASE": 500,
                    "SPUTUM R/M": 500,
                    "VITAMIN -D3": 1500,
                    "VITAMIN-B9(FOLIC ACID)": 1500,
                    "PROLACTIN-PRL": 600,
                    "(LAL)CSF ANTOIMMUNA WAR KUP": 24000,
                    "ROGEN POLEN TUB MELANA SEMM N KA": 3000,
                    "HP HELICOBACTOR PYLORI": 5000,
                    "IGA": 3100,
                    "IGM": 3100,
                    "IGG": 3100,
                    "NT PRO BNP": 3100,
                    "BILI": 150,
                    "RA(QUANTITAVE)": 500,

                    "Iron profile": 1000,
                    "GBP": 500,
                    "Double marker": 3600,
                    "Anti-CGP": 1800,
                    "ANA": 850,
                    "Gonorrhea test": 4000,
                    "Pylori test": 4800,
                    "TB Gold": 2200,
                    "Routine body fluid": 440,
                    "ANA/ANF Combo panel": 5900,
                    "Androgen, plain tube modern": 3000,

                    "CT-SCAN CT-HEAD": 2000,
                    "CT-SCAN CECT-HEAD": 2300,
                    "CT-SCAN CT-3D SKULL": 4500,
                    "CT-SCAN NCCT-ORBIT": 4000,
                    "CT-SCAN NCCT-FACE": 4000,
                    "CT-SCAN CECT-FACE": 4500,
                    "CT-SCAN HRCT-TEMPORAL BONE (CT-Mastoid)": 4500,
                    "CT-SCAN CECT-PNS": 3800,
                    "CT-SCAN CECT-NECK": 4500,
                    "CT-SCAN CT-CERVICAL SPINE": 4000,
                    "CT-SCAN HRCT-THORAX/CHEST": 4000,
                    "CT-SCAN CECT-3D THORAX/3D CHEST": 4500,
                    "CT-SCAN CECT-THORAX/CHEST": 4500,
                    "CT-SCAN NCCT-ABDOMEN": 5000,
                    "CT-SCAN CECT-ABDOMEN": 6000,
                    "CT-SCAN NCCT-KUB": 5000,
                    "CT-SCAN CECT-KUB": 6000,
                    "CT-SCAN CECT-L.S SPINE + 3D": 4000,
                    "CT-SCAN CT-D.J SPINE": 4000,
                    "CT-SCAN NCCT-ANKLE": 3500,
                    "CT-SCAN NCCT-KNEE + 3D": 3500,
                    "CT-SCAN NCCT-BOTH HIP + 3D": 3500,
                    "CT-SCAN NCCT-ELBOW + 3D": 4000,
                    "CT-SCAN NCCT-SHOULDER + 3D": 4000,
                    "X-RAY CHEST-PA": 350,
                    "X-RAY CHEST-AP": 350,
                    "X-RAY CHEST-AP/PA": 600,
                    "X-RAY CHEST-PA/LAT": 600,
                    "X-RAY CHEST-AP/LAT": 600,
                    "X-RAY L.S SPINE-AP/LAT": 650,
                    "X-RAY L.S SPINE-AP": 350,
                    "X-RAY D.L SPINE-AP/LAT": 650,
                    "X-RAY CERVICAL SPINE-AP/LAT": 650,
                    "X-RAY NECK-AP/LAT": 500,
                    "X-RAY SHOULDER-AP/LAT": 400,
                    "X-RAY KUB/ABDOMEN-AP": 350,
                    "X-RAY PELVIS-AP": 350,
                    "X-RAY HIP-AP": 350,
                    "X-RAY HIP-AP/LAT": 650,
                    "X-RAY BOTH HIP-AP/LAT": 1200,
                    "X-RAY KNEE-AP/LAT": 400,
                    "X-RAY BOTH KNEE-AP/LAT": 800,
                    "X-RAY ANKLE-AP/LAT": 400,
                    "X-RAY BOTH ANKLE-AP/LAT": 800,
                    "X-RAY FOOT-AP/OBLIQUE": 400,
                    "X-RAY BOTH FOOT-AP/OBL": 800,
                    "X-RAY LEG-AP/LAT": 400,
                    "X-RAY BOTH LEG-AP/LAT": 800,
                    "X-RAY WRIST-AP/LAT": 400,
                    "X-RAY BOTH WRIST-AP/LAT": 800,
                    "X-RAY FINGER-AP/LAT": 400,
                    "X-RAY BOTH FINGER-AP/OBL": 800,
                    "X-RAY ELBOW-AP/LAT": 400,
                    "X-RAY BOTH ELBOW-AP/LAT": 800,
                    "X-RAY FOREARM-AP/LAT": 400,
                    "X-RAY BOTH FOREARM-AP/LAT": 800,
                    "X-RAY MASTOID-LAT": 350,
                    "X-RAY BOTH MASTOID-LAT": 600,
                    "X-RAY ORBIT-AP": 400,
                    "X-RAY PNS-WATER": 350,
                    "X-RAY FACE-PA/LAT": 500,
                    "X-RAY SKULL-PA/LAT": 500,
                    "X-RAY SKULL-PA": 350,
                    "X-RAY TMJ-LAT": 350,
                    "X-RAY BOTH TMJ-LAT": 600,
                    "X-RAY RGMU": 2000,
                    "X-RAY IVP": 2000,
                    "X-RAY FISTULOGRAM": 1200,
                    "X-RAY RGU": 1200,
                    "X-RAY MCU": 1000,
                    "X-RAY HSG": 2000,
                    "X-RAY BERIUM SALLOW": 1500,
                    "X-RAY BERIUM MEAL": 1500,
                    "X-RAY BERIUM MEAL FOLLOWTHROUGH": 1500,
                    "X-RAY BERIUM ENEMA": 1500,
                    "USG WHOLE ABDOMEN": 750,
                    "USG PREGNANCY USG": 780,
                    "USG PELVIC USG": 750,
                    "USG T.V.S. USG": 1200,
                    "USG SCROTUM/TESTIS USG": 1200,
                    "USG BREAST USG": 1200,
                    "USG NECK/THYROID USG": 1200,
                    "USG LOCAL REGION USG": 1200,
                    "USG Follicular Study": 1200
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
                
                # Set success state and record for display
                st.session_state.show_success = True
                st.session_state.last_record = medical_entry
                st.session_state.processing_submission = False
                
                # Clear form fields immediately after successful save
                self.clear_form_fields()
                
                # Rerun to show success screen
                st.rerun()

            except Exception as e:
                # Reset processing state on error
                st.session_state.processing_submission = False
                st.error(f"❌ **Error saving record:** {str(e)}")
                st.error("Please try again or contact system administrator if the problem persists.")
                logger.error(f"Error saving medical record: {str(e)}")


class ExpenseForm:
    def __init__(self):
        # Use expense collection name based on environment
        self.database_collection = DBCollectionNames(st.secrets.get("expense_collection", "expenses_dev")).value
    
    def validate_amount(self, amount):
        """Validate expense amount"""
        if amount <= 0:
            return False, "Amount must be greater than 0"
        if amount > 1000000:  # 10 Lakh limit
            return False, "Amount exceeds maximum limit (₹10,00,000)"
        return True, ""
    
    def validate_description(self, description, expense_type):
        """Validate description based on expense type"""
        if not description or len(description.strip()) < 3:
            return False, "Description must be at least 3 characters"
        if len(description.strip()) > 500:
            return False, "Description cannot exceed 500 characters"
        return True, ""
    
    def validate_form_data(self, expense_type, amount, description):
        """Comprehensive form validation"""
        errors = []
        
        # Validate expense type
        if not expense_type:
            errors.append("Please select an expense type")
        
        # Validate amount
        amount_valid, amount_error = self.validate_amount(amount)
        if not amount_valid:
            errors.append(amount_error)
        
        # Validate description
        desc_valid, desc_error = self.validate_description(description, expense_type)
        if not desc_valid:
            errors.append(desc_error)
        
        # Check for session state validity
        if not st.session_state.get('user_email'):
            errors.append("User session invalid. Please login again.")
        
        if not st.session_state.get('user_role'):
            errors.append("User role not found. Please contact administrator.")
        
        return len(errors) == 0, errors
    
    def show_success_message(self, expense_record):
        """Show enhanced success message with expense details"""
        st.success("✅ Expense record successfully saved!")
        
        with st.expander("📋 View Submitted Expense", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Expense Information:**")
                st.write(f"• Type: {expense_record.expense_type}")
                st.write(f"• Amount: ₹{expense_record.amount:,}")
                st.write(f"• Date: {expense_record.date}")
            
            with col2:
                st.markdown("**Additional Details:**")
                if expense_record.description:
                    st.write(f"• Description: {expense_record.description}")
                st.write(f"• Added by: {expense_record.updated_by_email}")
        
        st.markdown("---")
    
    def show_recent_expenses(self, limit=5):
        """Show recent expenses for context"""
        try:
            # Get recent expenses
            recent_expenses = db.query_collection(
                self.database_collection,
                filters=[],
                limit=limit
            )
            
            if recent_expenses:
                st.markdown("### 📊 Recent Expenses")
                
                for i, expense in enumerate(recent_expenses[:limit]):
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                        
                        with col1:
                            st.write(f"**{expense.get('expense_type', 'Unknown')}**")
                        with col2:
                            st.write(f"₹{expense.get('amount', 0):,}")
                        with col3:
                            expense_date = expense.get('date', '')
                            if expense_date:
                                try:
                                    # Handle different date formats
                                    if isinstance(expense_date, str):
                                        date_obj = datetime.strptime(expense_date, "%Y-%m-%d %H:%M:%S")
                                        formatted_date = date_obj.strftime("%d %b %Y")
                                    else:
                                        formatted_date = str(expense_date)[:10]
                                    st.write(formatted_date)
                                except:
                                    st.write(str(expense_date)[:10])
                        with col4:
                            if st.button("📝", key=f"view_expense_{i}", help="View details"):
                                with st.expander(f"Expense Details", expanded=True):
                                    st.write(f"**Description:** {expense.get('description', 'No description')}")
                                    st.write(f"**Added by:** {expense.get('updated_by_email', 'Unknown')}")
                        
                        if i < len(recent_expenses) - 1:
                            st.divider()
                            
            else:
                st.info("No recent expenses found.")
                
        except Exception as e:
            st.warning(f"Could not load recent expenses: {str(e)}")
    
    def clear_form_fields(self):
        """Clear all expense form fields from session state"""
        form_keys_to_clear = [
            'expense_type', 'expense_amount', 'expense_description'
        ]
        for key in form_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def reset_all_states(self):
        """Reset all expense-related states - comprehensive cleanup"""
        # Clear form fields
        self.clear_form_fields()
        
        # Clear processing states
        processing_keys = [
            'expense_form_errors', 'expense_processing_submission',
            'expense_show_success', 'expense_last_record', 'show_recent_expenses'
        ]
        for key in processing_keys:
            if key in st.session_state:
                del st.session_state[key]
    
    def handle_form_errors(self, error_msg: str):
        """Centralized error handling with user-friendly messages"""
        # Log the actual error
        logger.error(f"Expense form error: {error_msg}")
        
        # Show user-friendly error messages
        if "permission" in error_msg.lower() or "unauthorized" in error_msg.lower():
            st.error("❌ **Access denied.** You don't have permission to add expenses.")
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            st.error("❌ **Connection error.** Please check your internet connection and try again.")
        elif "validation" in error_msg.lower():
            st.error("❌ **Validation error.** Please check your input and try again.")
        else:
            st.error(f"❌ **Error saving expense:** {error_msg}")
            st.error("Please try again or contact system administrator if the problem persists.")
    
    def render(self, is_authorized: bool = False):
        if not is_authorized:
            st.warning("🔐 You need to be logged in and approved to access this form.")
            return
        
        # Header with improved styling
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="color: #ff6b6b; margin-bottom: 10px;">💰 Expense Entry</h1>
            <p style="color: #666; font-size: 16px;">Complete the form below to record a new expense</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize session state for form validation and submission tracking
        if 'expense_form_errors' not in st.session_state:
            st.session_state.expense_form_errors = {}
        if 'expense_processing_submission' not in st.session_state:
            st.session_state.expense_processing_submission = False
        if 'expense_show_success' not in st.session_state:
            st.session_state.expense_show_success = False
        if 'expense_last_record' not in st.session_state:
            st.session_state.expense_last_record = None
        
        # Show success message if we just completed a submission
        if st.session_state.expense_show_success and st.session_state.expense_last_record:
            self.show_success_message(st.session_state.expense_last_record)
            
            # Add button to start new entry
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("➕ Add New Expense", use_container_width=True, key="expense_new_entry"):
                    # Clear success state and form
                    st.session_state.expense_show_success = False
                    st.session_state.expense_last_record = None
                    self.clear_form_fields()
                    st.rerun()
            
            # Add option to view all expenses
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("📊 View All Expenses", use_container_width=True, key="view_all_expenses"):
                    # Set flag to show all expenses
                    st.session_state.show_all_expenses = True
                    st.rerun()
            
            # Show all expenses if requested
            if st.session_state.get('show_all_expenses', False):
                st.markdown("---")
                self.show_recent_expenses(limit=20)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🔙 Back to Form", use_container_width=True, key="back_to_form"):
                        st.session_state.show_all_expenses = False
                        st.rerun()
            
            return
        
        # Form container with better styling
        with st.container():
            st.markdown("---")
            
            # EXPENSE TYPE SECTION
            with st.expander("📂 Expense Type", expanded=True):
                expense_type = st.selectbox(
                    label='💼 Expense Category *',
                    options=list(ExpenseType),
                    help='Select the category of expense',
                    key="expense_type"
                )
                
                # Show expense type description
                expense_descriptions = {
                    ExpenseType.RENT: "Monthly office/clinic rent payments",
                    ExpenseType.ELECTRICITY: "Electricity and utility bills",
                    ExpenseType.INTERNET: "Internet and communication expenses",
                    ExpenseType.DOCTOR_FEES: "Doctor consultation and professional fees",
                    ExpenseType.STAFF_EXPENSE: "Staff-related expenses (excluding salary)",
                    ExpenseType.EQUIPMENT: "Medical equipment and machinery costs",
                    ExpenseType.SALARY: "Staff salary payments",
                    ExpenseType.STATIONARY: "Office supplies and stationery",
                    ExpenseType.CHAI_NASHTA: "Tea, snacks and refreshments",
                    ExpenseType.OTHER: "Other miscellaneous expenses"
                }
                
                st.info(f"💡 {expense_descriptions.get(expense_type, 'General expense category')}")
            
            # AMOUNT SECTION
            with st.expander("💵 Amount Details", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    expense_amount = st.number_input(
                        label='Expense Amount (₹) *',
                        min_value=1,
                        max_value=1000000,
                        step=10,
                        value=100,
                        help='💰 Enter the expense amount in Indian Rupees',
                        key="expense_amount"
                    )
                    
                    # Real-time amount validation
                    if expense_amount:
                        is_valid, error_msg = self.validate_amount(expense_amount)
                        if not is_valid:
                            st.error(f"❌ {error_msg}")
                        else:
                            st.success(f"✅ Amount: ₹{expense_amount:,}")
                
                with col2:
                    st.metric(
                        label="Amount",
                        value=f"₹{expense_amount:,}",
                        help="Expense amount in Indian Rupees"
                    )
            
            # DESCRIPTION SECTION
            with st.expander("📝 Description & Notes", expanded=True):
                expense_description = st.text_area(
                    label='Expense Description *',
                    placeholder="Enter detailed description of the expense...",
                    help='📝 Provide a clear description of what this expense is for',
                    height=120,
                    max_chars=500,
                    key="expense_description"
                )
                
                # Real-time description validation
                if expense_description:
                    is_valid, error_msg = self.validate_description(expense_description, expense_type)
                    if not is_valid:
                        st.error(f"❌ {error_msg}")
                    else:
                        char_count = len(expense_description.strip())
                        st.success(f"✅ Description valid ({char_count}/500 characters)")
                
                # Add predefined suggestions based on expense type
                if expense_type:
                    suggestions = {
                        ExpenseType.RENT: ["Monthly office rent - [Month/Year]", "Clinic space rental"],
                        ExpenseType.ELECTRICITY: ["Monthly electricity bill", "Generator fuel cost"],
                        ExpenseType.INTERNET: ["Monthly internet bill", "WiFi router purchase"],
                        ExpenseType.DOCTOR_FEES: ["Dr. [Name] consultation fee", "Specialist consultation"],
                        ExpenseType.STAFF_EXPENSE: ["Staff uniform purchase", "Staff training cost"],
                        ExpenseType.EQUIPMENT: ["[Equipment name] purchase", "Equipment maintenance"],
                        ExpenseType.SALARY: ["[Name] salary for [Month]", "Overtime payment"],
                        ExpenseType.STATIONARY: ["Office supplies purchase", "Printer paper and ink"],
                        ExpenseType.CHAI_NASHTA: ["Daily refreshments", "Staff lunch arrangement"],
                        ExpenseType.OTHER: ["Miscellaneous expense", "Unexpected cost"]
                    }
                    
                    if expense_type in suggestions:
                        st.markdown("**💡 Suggestion examples:**")
                        suggestion_text = " • ".join(suggestions[expense_type])
                        st.caption(f"• {suggestion_text}")
            
            st.markdown("---")
            
            # FORM SUBMISSION
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                # Validate required fields before enabling submit
                can_submit = (
                    expense_amount and 
                    expense_amount > 0 and
                    expense_description and
                    len(expense_description.strip()) >= 3 and
                    not st.session_state.expense_processing_submission  # Disable while processing
                )
                
                # Show processing status if submitting
                if st.session_state.expense_processing_submission:
                    button_label = '⏳ Processing...'
                    help_text = "Please wait while your expense is being saved"
                else:
                    button_label = '💾 Submit Expense'
                    help_text = "Complete all required fields to enable submission" if not can_submit else "Click to save the expense record"
                
                submit_button = st.button(
                    label=button_label,
                    disabled=not can_submit,
                    use_container_width=True,
                    help=help_text,
                    key="expense_submit"
                )
            
            # Show required fields reminder
            if not can_submit:
                st.info("📋 **Required fields:** Expense Type, Amount (>0), Description (min 3 characters)")
        
        # RECENT EXPENSES SECTION (before form submission logic)
        st.markdown("---")
        
        # Add toggle for recent expenses
        col1, col2 = st.columns([1, 3])
        with col1:
            show_recent = st.checkbox("📊 Show Recent Expenses", value=False, key="show_recent_expenses")
        
        if show_recent:
            with col2:
                st.caption("View recently added expenses for reference")
            self.show_recent_expenses(limit=5)
        
        # FORM SUBMISSION LOGIC
        if submit_button:
            # Set processing state to disable the button
            st.session_state.expense_processing_submission = True
            
            try:
                # Comprehensive validation before submission
                is_valid, validation_errors = self.validate_form_data(expense_type, expense_amount, expense_description)
                
                if not is_valid:
                    st.session_state.expense_processing_submission = False
                    st.error("❌ **Validation Errors:**")
                    for error in validation_errors:
                        st.error(f"• {error}")
                    return
                
                with st.spinner('💾 Saving expense record...'):
                    # Double-check database collection exists
                    if not self.database_collection:
                        raise Exception("Database collection not configured properly")
                    
                    # Create expense record with additional safety checks
                    try:
                        expense_entry = ExpenseRecord(
                            expense_type=expense_type,
                            amount=int(expense_amount),
                            description=expense_description.strip(),
                            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            updated_by=st.session_state.user_role,
                            updated_by_email=st.session_state.user_email
                        )
                    except ValueError as ve:
                        raise Exception(f"Data validation error: {str(ve)}")
                    
                    # Save to database with retry logic
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            db.create_doc(
                                self.database_collection, 
                                expense_entry.model_dump(mode="json")
                            )
                            break  # Success, exit retry loop
                        except Exception as db_error:
                            if attempt == max_retries - 1:  # Last attempt
                                raise Exception(f"Database save failed after {max_retries} attempts: {str(db_error)}")
                            time.sleep(1)  # Wait before retry
                
                # Set success state and record for display
                st.session_state.expense_show_success = True
                st.session_state.expense_last_record = expense_entry
                st.session_state.expense_processing_submission = False
                
                # Clear form fields immediately after successful save
                self.clear_form_fields()
                
                # Rerun to show success screen
                st.rerun()

            except Exception as e:
                # Reset processing state on error
                st.session_state.expense_processing_submission = False
                self.handle_form_errors(str(e))


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



    def show_admin_user_management(self):
        """Admin interface for managing user roles - only accessible by project owner"""
        if self.user_auth.is_current_user_owner() != AuthorizationStatus.OWNER:
            return
        
        # Header with improved styling
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="color: #e74c3c; margin-bottom: 10px;">🔧 Admin Dashboard</h1>
            <p style="color: #666; font-size: 16px;">Manage user accounts and permissions</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        try:
            users = self.db.get_docs(USER_DB_COLLECTION)
            
            if not users:
                st.info("No users found in the system.")
                return
            
            # Display summary stats
            total_users = len(users)
            active_users = len([u for u in users if u.get('status') == 'active'])
            pending_users = len([u for u in users if u.get('status') == 'pending_approval'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Users", total_users)
            with col2:
                st.metric("Active Users", active_users)
            with col3:
                st.metric("Pending Approval", pending_users)
            
            st.markdown("---")
            
            # Tabs for different sections
            tab1, tab2 = st.tabs(["👥 Manage User Roles", "⏳ Pending Approvals"])
            
            with tab1:
                st.subheader("User Role Management")
                
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
                            status_color = "🟢" if status == "active" else "🟡"
                            st.text(f"{status_color} {status}")
                        
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
            
            with tab2:
                st.subheader("Pending User Approvals")
                
                # Pending approvals section
                pending_users = [user for user in users if user.get('status') == 'pending_approval']
                
                if not pending_users:
                    st.info("✅ No pending approvals found.")
                    return
                
                for user_data in pending_users:
                    email = user_data.get('email', 'Unknown')
                    if is_project_owner(email):
                        continue
                    
                    with st.container():
                        col1, col2, col3 = st.columns([4, 2, 2])
                        with col1:
                            st.text(f"📧 {email}")
                            created_date = user_data.get('created_at', 'Unknown')
                            st.caption(f"Registered: {created_date}")
                        
                        with col2:
                            st.write("⏳ Awaiting approval")
                        
                        with col3:
                            if st.button("✅ Approve", key=f"approve_{email}"):
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
                                    
                                    st.success(f"✅ Approved {email}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error approving user: {str(e)}")
                        
                        st.divider()
                
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
                
                # Add page navigation
                st.markdown("---")
                st.subheader("📋 Navigation")
                
                # Initialize page selection in session state if not present
                if 'current_page' not in st.session_state:
                    st.session_state.current_page = "Medical Records"
                
                # Page selection - include Admin for project owners
                page_options = ["Medical Records", "Expenses"]
                if is_project_owner(st.session_state.user_email):
                    page_options.append("Admin")
                
                selected_page = st.radio(
                    "Select Page:",
                    page_options,
                    index=page_options.index(st.session_state.current_page) if st.session_state.current_page in page_options else 0,
                    key="page_selector"
                )
                
                # Update session state if page changed
                if selected_page != st.session_state.current_page:
                    st.session_state.current_page = selected_page
                    # Clear any form states when switching pages
                    form_keys_to_clear = [
                        # Medical form keys
                        'patient_name', 'patient_phone', 'patient_address',
                        'phone_checkbox', 'address_checkbox', 'referral_checkbox',
                        'doctor_name', 'doctor_location', 'test_type', 'payment_amount',
                        'comments', 'form_errors', 'processing_submission', 
                        'show_success', 'last_record',
                        # Expense form keys
                        'expense_type', 'expense_amount', 'expense_description',
                        'expense_form_errors', 'expense_processing_submission',
                        'expense_show_success', 'expense_last_record', 'show_recent_expenses',
                        'show_all_expenses',
                        # Admin form keys
                        'show_admin', 'admin_user_filter'
                    ]
                    for key in form_keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                
                st.markdown("---")
                
                if st.button("Logout"):
                    self.user_auth.logout()
                    st.rerun()
                
                # Remove the old admin menu call
                # self.opening_screen.show_admin_menu()
            else:
                self.opening_screen.opening_screen()
            
            st.session_state.times_loaded = st.session_state.get('times_loaded', 0)
            st.session_state.times_loaded += 1
            st.write(f"Times loaded: {st.session_state.times_loaded}")
            
        # Render pages based on navigation selection
        authorization = self.user_auth.require_authorization()
        is_authorized = authorization == AuthorizationStatus.APPROVED
        
        # Get current page selection
        current_page = st.session_state.get('current_page', 'Medical Records')
        
        # Render the appropriate page based on selection
        if is_authenticated and is_authorized:
            if current_page == "Medical Records":
                MedicalRecordForm().render(is_authorized)
            elif current_page == "Expenses":
                ExpenseForm().render(is_authorized)
            elif current_page == "Admin":
                # Only show admin page to project owners
                if is_project_owner(st.session_state.user_email):
                    self.opening_screen.show_admin_user_management()
                else:
                    st.error("❌ Access denied. Admin page is only accessible to project owners.")
        else:
            # Show medical records form by default for unauthorized users (they'll see the warning)
            MedicalRecordForm().render(is_authorized)


if __name__ == '__main__':
    ui = PrimeLabsUI()
    ui.render()
