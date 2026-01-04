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
    EXPENSE_DESCRIPTIONS,
)
from user_authentication import UserAuthentication
from utils import (
    get_firestore, 
    get_user_authentication,
    get_pending_approval_html,
    is_project_owner,
    get_ist_now,
    get_ist_now_str,
    format_datetime_for_display,
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
                total_price = 0
                for test in medical_record.medical_tests:
                    st.write(f"• {test.name}: ₹{test.price:,}")
                    total_price += test.price or 0
                st.write(f"• **Total Price: ₹{total_price:,}**")
            
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
        filename = f"medical_record_{medical_record.patient.name}_{get_ist_now_str('%Y%m%d_%H%M%S')}.pdf"
        
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
            'doctor_name', 'doctor_location', 'test_type', 'test_types', 'payment_amount',
            'comments'
        ]
        for key in form_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Clear dynamic payment keys (payment_<test_name>)
        payment_keys = [key for key in st.session_state if key.startswith('payment_')]
        for key in payment_keys:
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
                    "X-RAY KNEE-AP/LAT": 450,
                    "X-RAY BOTH KNEE-AP/LAT": 800,
                    "X-RAY ANKLE-AP/LAT": 400,
                    "X-RAY BOTH ANKLE-AP/LAT": 800,
                    "X-RAY FOOT-AP/LAT": 450,
                    "X-RAY FOOT-AP/OBLIQUE": 450,
                    "X-RAY BOTH FOOT-AP/OBL": 800,
                    "X-RAY LEG-AP/LAT": 400,
                    "X-RAY BOTH LEG-AP/LAT": 800,
                    "X-RAY WRIST-AP/LAT": 450,
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
                    "USG Follicular Study": 1200,
                    "ECG": 300,

                    "HCV RNA": 3600,
                    "Hep-B DNA": 3500,
                    "Serum IPTH": 1700,
                    "TTG": 1500,
                    "Blood Culture (BDLS)": 1500,
                    "Urine Culture (VDLS)": 1200,
                    "Stool Occult Blood Test (SOBT)": 500,
                    "FSH, LH": 1000,
                    "Serum TPO": 1300,
                    "NTCCP": 1700,
                    "Alpha Fetoprotein (α-FP)": 1000,
                    "Serum Iron": 700,
                    "Serum Ferritin": 900,
                    "CSF": 2000,
                    "CBNAA SPOT": 500,
                    "CBNAA": 3000,
                    "OBS": 750,
                }
                
                # Multi-select for tests
                selected_tests = st.multiselect(
                    label='🔬 Medical Test Types *',
                    options=list(TEST_PRICES.keys()),
                    help='Select one or more medical tests to be performed',
                    key="test_types",
                    placeholder="Select tests..."
                )
                
                if selected_tests:
                    st.success(f"✅ {len(selected_tests)} test(s) selected")
                else:
                    st.info("💡 Please select at least one medical test")
            
            # PAYMENT INFORMATION SECTION
            with st.expander("💳 Payment Information", expanded=True):
                # Initialize free_test_reason before conditional blocks
                free_test_reason = None
                
                if not selected_tests:
                    st.info("💡 Please select medical tests first to enter payment details")
                    # Initialize empty values for when no tests are selected
                    test_payments = {}
                    total_payment = 0
                    total_test_price = 0
                    total_discount = 0
                else:
                    st.markdown("**Payment per Test** (Enter amount paid for each test)")
                    
                    # Calculate total price for selected tests
                    total_test_price = sum(TEST_PRICES[test] for test in selected_tests)
                    
                    # Create payment input for each selected test
                    test_payments = {}
                    for test in selected_tests:
                        test_price = TEST_PRICES[test]
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            st.markdown(f"**{test}**")
                            st.caption(f"Price: ₹{test_price:,}")
                        
                        with col2:
                            payment_key = f"payment_{test.replace(' ', '_').replace('/', '_').replace('-', '_')}"
                            test_payment = st.number_input(
                                label=f"Amount for {test}",
                                min_value=0,
                                max_value=test_price,
                                step=10,
                                value=test_price,  # Default to full price
                                help=f'Enter amount paid for {test} (max ₹{test_price:,})',
                                key=payment_key,
                                label_visibility="collapsed"
                            )
                            test_payments[test] = test_payment
                        
                        with col3:
                            discount = test_price - test_payment
                            if discount > 0:
                                st.markdown(f"<span style='color: #dc3545;'>-₹{discount:,}</span>", unsafe_allow_html=True)
                            else:
                                st.markdown("✅")
                    
                    # Calculate totals
                    total_payment = sum(test_payments.values())
                    total_discount = total_test_price - total_payment
                    
                    # Show summary
                    st.markdown("---")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown("**Total Price:**")
                    with col2:
                        st.markdown(f"₹{total_test_price:,}")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown("**Total Payment:**")
                    with col2:
                        st.markdown(f"<span style='color: #28a745; font-weight: 800;'>₹{total_payment:,}</span>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown("**Total Discount:**")
                    with col2:
                        if total_discount > 0:
                            st.markdown(f"<span style='color: #dc3545; font-weight: 600;'>₹{total_discount:,}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("₹0")
                    
                    # Free test reason - shown only when total payment is 0
                    if total_payment == 0:
                        st.markdown("---")
                        st.warning("⚠️ **Free Test** - Please select a reason for waiving payment:")
                        free_test_reason = st.selectbox(
                            label="Reason for free test",
                            options=["-- Select Reason --", "Zaruratmand", "Friend/Family/Staff"],
                            key="free_test_reason",
                            help="Select why this test is being provided for free"
                        )
                
                # Comments section
                st.markdown("---")
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
                # Check if free test reason is valid (when payment is 0)
                free_test_valid = (
                    total_payment > 0 or 
                    (free_test_reason and free_test_reason != "-- Select Reason --")
                )
                
                # Validate required fields before enabling submit
                can_submit = (
                    patient_name and 
                    len(patient_name.strip()) >= 2 and
                    selected_tests and  # At least one test selected
                    len(selected_tests) > 0 and
                    free_test_valid and  # Either payment > 0 or valid free test reason
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
                payment_requirement = "Payment > 0 (or select free test reason)" if total_payment == 0 else "Payment > 0"
                st.info("📋 **Required fields:** Patient Name, At least one Medical Test, " + payment_requirement + 
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
                    
                    # Create list of medical tests with actual paid prices
                    medical_tests_list = [
                        MedicalTest(name=test_name, price=test_payments.get(test_name, TEST_PRICES[test_name]))
                        for test_name in selected_tests
                    ]
                    
                    # Build comments - include free test reason if applicable
                    final_comments = comments.strip() if comments else ""
                    if total_payment == 0 and free_test_reason and free_test_reason != "-- Select Reason --":
                        free_test_note = f"[FREE TEST: {free_test_reason}]"
                        final_comments = f"{free_test_note} {final_comments}".strip()
                    
                    # Create medical record
                    medical_entry = MedicalRecord(
                        patient=patient,
                        doctor=referring_doctor,
                        medical_tests=medical_tests_list,
                        payment=Payment(amount=total_payment),
                        date=get_ist_now(),  # Use datetime object for proper Firestore timestamp
                        comments=final_comments,
                        updated_by=st.session_state.user_role,
                        updated_by_email=st.session_state.user_email
                    )
                    
                    # Save to database
                    # Use model_dump() without mode="json" to preserve datetime objects
                    # Firestore will automatically convert them to proper Timestamps
                    db.create_doc(
                        self.database_collection, 
                        medical_entry.model_dump()
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
        # Description is required for OTHER expense type
        if expense_type == ExpenseType.OTHER:
            if not description or len(description.strip()) < 3:
                return False, "Description is required for 'Other Expense' (at least 3 characters)"
        # For other expense types, description is optional but must be valid if provided
        elif description and len(description.strip()) > 0:
            if len(description.strip()) < 3:
                return False, "Description must be at least 3 characters if provided"
        if description and len(description.strip()) > 500:
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
            # Get recent expenses with proper ordering by date
            recent_expenses = db.get_docs(
                self.database_collection,
                filters=[],
                limit=limit,
                order_by="date",
                order_direction="DESCENDING"
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
                st.info(f"💡 {EXPENSE_DESCRIPTIONS.get(expense_type, 'General expense category')}")
            
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
                        ExpenseType.CHAI_NASHTA: ["Daily refreshments", "Staff lunch arrangement"],
                        ExpenseType.PETROL_DIESEL: ["Vehicle fuel", "Generator diesel"],
                        ExpenseType.RENT: ["Monthly office rent - [Month/Year]", "Clinic space rental"],
                        ExpenseType.ELECTRICITY: ["Monthly electricity bill", "Generator fuel cost"],
                        ExpenseType.INTERNET: ["Monthly internet bill", "WiFi router purchase"],
                        ExpenseType.STAFF_SALARY: ["[Name] salary for [Month]", "Overtime payment"],
                        ExpenseType.DOCTOR_CUT: ["Dr. [Name] referral cut", "Monthly doctor payments"],
                        ExpenseType.DOCTOR_FEES: ["Dr. [Name] consultation fee", "Specialist consultation"],
                        ExpenseType.MACHINE_REPAIR: ["[Machine name] repair", "Annual maintenance"],
                        ExpenseType.MACHINE_INSTALL: ["[Machine name] installation", "Setup charges"],
                        ExpenseType.MACHINE_COST: ["[Machine name] purchase", "New equipment cost"],
                        ExpenseType.PAPER_STATIONARY: ["Office supplies purchase", "Printer paper and ink"],
                        ExpenseType.THYROCARE: ["Thyrocare test kits", "Thyrocare supplies"],
                        ExpenseType.STAFF_EXPENSE: ["Staff uniform purchase", "Staff training cost"],
                        ExpenseType.SALARY: ["[Name] salary for [Month]", "Bonus payment"],
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
                # Description is only required for OTHER expense type
                description_valid = (
                    expense_type != ExpenseType.OTHER or 
                    (expense_description and len(expense_description.strip()) >= 3)
                )
                can_submit = (
                    expense_amount and 
                    expense_amount > 0 and
                    description_valid and
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
                st.info("📋 **Required fields:** Expense Type, Amount (>0). Description required for 'Other Expense'.")
        
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
                            date=get_ist_now(),  # Use datetime object for proper Firestore timestamp
                            updated_by=st.session_state.user_role,
                            updated_by_email=st.session_state.user_email
                        )
                    except ValueError as ve:
                        raise Exception(f"Data validation error: {str(ve)}")
                    
                    # Save to database with retry logic
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            # Use model_dump() without mode="json" to preserve datetime objects
                            # Firestore will automatically convert them to proper Timestamps
                            db.create_doc(
                                self.database_collection, 
                                expense_entry.model_dump()
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
    
    def show_rejected_screen(self):
        """Show rejected screen for users whose access has been revoked"""
        st.markdown("### 🚫 Access Denied")
        
        st.error("""
        **Your account access has been revoked**
        
        Your account has been rejected or your access has been revoked by an administrator.
        You cannot access the PrimeLabs system at this time.
        """)
        
        st.markdown("#### What can you do?")
        st.markdown("""
        - Contact the system administrator to understand why your access was revoked
        - Request reinstatement if you believe this was done in error
        - If you need immediate assistance, reach out to: `admin@primelabs.com`
        """)
        
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
                self.show_error_message("MISSING_FIELDS")
                return
            
            is_logged_in, error_message = self.user_auth.login(email, password)
            if is_logged_in:
                st.success("Login successful!")
                st.rerun()
            else:
                self.show_error_message(error_message, "Login")
 
    def register_screen(self):
        name = st.text_input("Full Name", placeholder="Enter your full name")
        email = st.text_input("Email", placeholder="Enter your email address")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Register"):
            if not all([name, email, password, confirm_password]):
                self.show_error_message("MISSING_FIELDS")
                return
            if len(name.strip()) < 2:
                st.error("Name must be at least 2 characters")
                return
            if password != confirm_password:
                self.show_error_message("PASSWORD_MISMATCH")
                return 
            is_registered, error_message = self.user_auth.register(email, password, name.strip())
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
        display_message = ""
        
        if "MISSING_FIELDS" in error_message:
            display_message = "Please fill in all fields"
        elif "PASSWORD_MISMATCH" in error_message:
            display_message = "Passwords do not match"
        elif "MISSING_EMAIL" in error_message:
            display_message = "Please enter your email address"
        elif "EMAIL_NOT_FOUND" in error_message:
            display_message = "No account found with this email address"
        elif "EMAIL_EXISTS" in error_message:
            display_message = "An account with this email already exists. Please use a different email or try logging in."
        elif "WEAK_PASSWORD" in error_message:
            display_message = "Password is too weak. Please use at least 6 characters with a mix of letters and numbers."
        elif "INVALID_EMAIL" in error_message:
            display_message = "Invalid email format. Please enter a valid email address (e.g., user@example.com)"
        elif "INVALID_PASSWORD" in error_message or "INVALID_LOGIN_CREDENTIALS" in error_message:
            display_message = "Incorrect password or invalid login credentials"
        elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_message:
            display_message = "Too many failed attempts. Please try again later."
        elif "USER_DISABLED" in error_message:
            display_message = "This user account has been disabled. Please contact the administrator."
        elif "OPERATION_NOT_ALLOWED" in error_message:
            display_message = "Registration is currently disabled. Please contact the administrator."
        elif "NETWORK" in error_message.upper() or "CONNECTION" in error_message.upper():
            display_message = "Network error. Please check your internet connection and try again."
        elif "TIMEOUT" in error_message.upper():
            display_message = "Request timed out. Please try again."
        else:
            # Show a user-friendly message with the actual error for debugging
            display_message = f"{operation} failed. Please try again or contact support if the issue persists."
        
        st.error(f"❌ {display_message}")

    def token_expired_screen(self):
        """Show token expired message"""
        st.warning("⏰ Your session has expired. Please login again to continue.")    
        self.opening_screen()
        return



    def show_admin_user_management(self):
        """Admin interface for managing user roles and status - accessible only by Admin role users"""
        # Check if user has Admin role or is project owner
        is_owner = self.user_auth.is_current_user_owner() == AuthorizationStatus.OWNER
        is_admin = st.session_state.user_role == UserRole.ADMIN.value
        
        if not (is_owner or is_admin):
            st.error("❌ Access denied. Only users with Admin role can manage user status.")
            return
        
        # Header with improved styling
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="color: #e74c3c; margin-bottom: 10px;">🔧 Admin Dashboard</h1>
            <p style="color: #666; font-size: 16px;">Manage user accounts and permissions</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Initialize pagination state
        if 'admin_page' not in st.session_state:
            st.session_state.admin_page = 0
        if 'admin_cursors' not in st.session_state:
            st.session_state.admin_cursors = {0: None}  # Store cursors for each page
        
        PAGE_SIZE = 20  # Users per page
        
        try:
            # Get user counts for summary
            # Fetch a batch of users to count (works without composite indexes)
            try:
                LIMIT = 500
                all_users_for_count = self.db.get_docs(USER_DB_COLLECTION, limit=LIMIT)
                total_users_count = len(all_users_for_count)
                approved_users_count = len([u for u in all_users_for_count if u.get('status') == 'approved'])
                pending_users_count = len([u for u in all_users_for_count if u.get('status') == 'pending_approval'])
                rejected_users_count = len([u for u in all_users_for_count if u.get('status') == 'rejected'])

                limit_reached = total_users_count >= LIMIT
                # Add "+" if limit reached, for all user types
                total_users = f"{total_users_count}+" if limit_reached else str(total_users_count)
                approved_users = f"{approved_users_count}+" if limit_reached else str(approved_users_count)
                pending_users = f"{pending_users_count}+" if limit_reached else str(pending_users_count)
                rejected_users = f"{rejected_users_count}+" if limit_reached else str(rejected_users_count)
            except Exception:
                # Fallback if count fails
                total_users = "?"
                approved_users = "?"
                pending_users = "?"
                rejected_users = "?"
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Users", total_users)
            with col2:
                st.metric("Approved", approved_users)
            with col3:
                st.metric("Pending", pending_users)
            with col4:
                st.metric("Rejected", rejected_users)
            
            st.markdown("---")
            
            # Tabs for different sections
            tab1, tab2, tab3 = st.tabs(["👥 Manage Users", "⏳ Pending Approvals", "🚫 Rejected Users"])
            
            with tab1:
                st.subheader("User Role & Status Management")
                st.info("💡 Users with 'approved' status can access the app. Change status to 'rejected' or 'pending_approval' to revoke access.")
                
                # Get current page cursor
                current_cursor = st.session_state.admin_cursors.get(st.session_state.admin_page)
                
                # Fetch paginated users
                result = self.db.get_docs_paginated(
                    collection=USER_DB_COLLECTION,
                    page_size=PAGE_SIZE,
                    cursor=current_cursor,
                    order_by="email",
                    order_direction="ASCENDING"
                )
                
                users = result.documents
                
                if not users:
                    st.info("No users found in the system.")
                else:
                    # Display users in a table format
                    for i, user_data in enumerate(users):
                        email = user_data.get('email', 'Unknown')
                        name = user_data.get('name', '')
                        current_role = user_data.get('role', UserRole.EMPLOYEE)
                        status = user_data.get('status', 'pending_approval')
                        
                        # Skip the owner's own account
                        if is_project_owner(email):
                            continue
                        
                        # Create unique key using page and index
                        unique_key = f"p{st.session_state.admin_page}_u{i}"
                        
                        with st.container():
                            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                            
                            with col1:
                                if name:
                                    st.text(f"👤 {name}")
                                    st.caption(f"📧 {email}")
                                else:
                                    st.text(f"📧 {email}")
                            
                            with col2:
                                if status == "approved":
                                    status_icon = "🟢"
                                elif status == "pending_approval":
                                    status_icon = "🟡"
                                else:
                                    status_icon = "🔴"
                                st.text(f"{status_icon} {status}")
                            
                            with col3:
                                # Only owners can change roles
                                if is_owner:
                                    new_role = st.selectbox(
                                        "Role",
                                        options=list(UserRole),
                                        index=list(UserRole).index(current_role) if current_role in list(UserRole) else 0,
                                        key=f"role_{unique_key}"
                                    )
                                else:
                                    st.text(f"Role: {current_role}")
                                    new_role = current_role
                            
                            with col4:
                                # Status options for changing user access
                                status_options = ["approved", "pending_approval", "rejected"]
                                current_status_index = status_options.index(status) if status in status_options else 1
                                new_status = st.selectbox(
                                    "Status",
                                    options=status_options,
                                    index=current_status_index,
                                    key=f"status_{unique_key}"
                                )
                            
                            with col5:
                                if st.button("💾", key=f"update_{unique_key}", help="Save changes"):
                                    try:
                                        doc_id = user_data.get('id')
                                        if doc_id:
                                            update_data = {
                                                "status": new_status,
                                                "updated_by": st.session_state.user_email,
                                                "updated_at": get_ist_now_str()
                                            }
                                            # Only update role if owner
                                            if is_owner:
                                                update_data["role"] = new_role
                                            
                                            self.db.update_doc(USER_DB_COLLECTION, doc_id, update_data)
                                            
                                            st.success(f"Updated {email}")
                                            st.rerun()
                                        else:
                                            st.error("User document ID not found")
                                    except Exception as e:
                                        st.error(f"Error updating user: {str(e)}")
                            
                            st.divider()
                    
                    # Pagination controls
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        if st.session_state.admin_page > 0:
                            if st.button("⬅️ Previous", key="prev_page"):
                                st.session_state.admin_page -= 1
                                st.rerun()
                    
                    with col2:
                        st.markdown(f"<p style='text-align: center;'>Page {st.session_state.admin_page + 1}</p>", unsafe_allow_html=True)
                    
                    with col3:
                        if result.has_more:
                            if st.button("Next ➡️", key="next_page"):
                                # Store cursor for next page
                                next_page = st.session_state.admin_page + 1
                                st.session_state.admin_cursors[next_page] = result.next_cursor
                                st.session_state.admin_page = next_page
                                st.rerun()
            
            with tab2:
                st.subheader("Pending User Approvals")
                
                # Fetch pending users (filter only, no order_by to avoid index requirement)
                try:
                    pending_users_list = self.db.get_docs(
                        collection=USER_DB_COLLECTION,
                        filters=[("status", "==", "pending_approval")],
                        limit=100
                    )
                except Exception as e:
                    st.error(f"Error loading pending users: {str(e)}")
                    pending_users_list = []
                
                if not pending_users_list:
                    st.info("✅ No pending approvals found.")
                else:
                    for idx, user_data in enumerate(pending_users_list):
                        email = user_data.get('email', 'Unknown')
                        name = user_data.get('name', '')
                        if is_project_owner(email):
                            continue
                        
                        with st.container():
                            col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
                            with col1:
                                if name:
                                    st.text(f"👤 {name}")
                                    st.caption(f"📧 {email}")
                                else:
                                    st.text(f"📧 {email}")
                                created_date = user_data.get('created_at', 'Unknown')
                                st.caption(f"Registered: {created_date}")
                            
                            with col2:
                                st.write("⏳ Awaiting approval")
                            
                            with col3:
                                if st.button("✅", key=f"approve_{idx}_{email}", help="Approve user"):
                                    try:
                                        doc_id = user_data.get('id')
                                        if not doc_id:
                                            st.error("User document ID not found")
                                            continue
                                        
                                        update_data = {
                                            "status": "approved",
                                            "approved_by": st.session_state.user_email,
                                            "approved_at": get_ist_now_str()
                                        }
                                        self.db.update_doc(USER_DB_COLLECTION, doc_id, update_data)
                                        
                                        st.success(f"✅ Approved {email}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error approving user: {str(e)}")
                            
                            with col4:
                                if st.button("❌", key=f"reject_{idx}_{email}", help="Reject user"):
                                    try:
                                        doc_id = user_data.get('id')
                                        if not doc_id:
                                            st.error("User document ID not found")
                                            continue
                                        
                                        update_data = {
                                            "status": "rejected",
                                            "rejected_by": st.session_state.user_email,
                                            "rejected_at": get_ist_now_str()
                                        }
                                        self.db.update_doc(USER_DB_COLLECTION, doc_id, update_data)
                                        
                                        st.warning(f"❌ Rejected {email}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error rejecting user: {str(e)}")
                            
                            st.divider()
            
            with tab3:
                st.subheader("Rejected Users")
                
                # Fetch rejected users (filter only, no order_by to avoid index requirement)
                try:
                    rejected_users_list = self.db.get_docs(
                        collection=USER_DB_COLLECTION,
                        filters=[("status", "==", "rejected")],
                        limit=100
                    )
                except Exception as e:
                    st.error(f"Error loading rejected users: {str(e)}")
                    rejected_users_list = []
                
                if not rejected_users_list:
                    st.info("✅ No rejected users found.")
                else:
                    for idx, user_data in enumerate(rejected_users_list):
                        email = user_data.get('email', 'Unknown')
                        name = user_data.get('name', '')
                        if is_project_owner(email):
                            continue
                        
                        with st.container():
                            col1, col2, col3 = st.columns([4, 2, 2])
                            with col1:
                                if name:
                                    st.text(f"👤 {name}")
                                    st.caption(f"📧 {email}")
                                else:
                                    st.text(f"📧 {email}")
                                rejected_date = user_data.get('rejected_at', 'Unknown')
                                st.caption(f"Rejected: {rejected_date}")
                            
                            with col2:
                                st.write("🔴 Rejected")
                            
                            with col3:
                                if st.button("🔄 Reinstate", key=f"reinstate_{idx}_{email}", help="Approve this user"):
                                    try:
                                        doc_id = user_data.get('id')
                                        if not doc_id:
                                            st.error("User document ID not found")
                                            continue
                                        
                                        update_data = {
                                            "status": "approved",
                                            "approved_by": st.session_state.user_email,
                                            "approved_at": get_ist_now_str()
                                        }
                                        self.db.update_doc(USER_DB_COLLECTION, doc_id, update_data)
                                        
                                        st.success(f"✅ Reinstated {email}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error reinstating user: {str(e)}")
                            
                            st.divider()
                            
                            st.divider()
                
        except Exception as e:
            st.error(f"Error loading user management: {str(e)}")

class DailyReportPage:
    """Daily Report page showing total collections and expenses for the day"""
    
    def __init__(self):
        self.medical_collection = DBCollectionNames(st.secrets["database_collection"]).value
        self.expense_collection = DBCollectionNames(st.secrets.get("expense_collection", "expenses_dev")).value
    
    def is_admin_user(self) -> bool:
        """Check if current user is an admin or project owner"""
        from utils import is_project_owner
        user_email = st.session_state.get('user_email', '')
        user_role = st.session_state.get('user_role', '')
        return is_project_owner(user_email) or user_role == UserRole.ADMIN.value
    
    def get_today_date_range(self):
        """Get the start and end datetime for today in IST"""
        today = get_ist_now()
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_of_day, end_of_day
    
    def fetch_daily_collections(self, target_date: datetime = None):
        """Fetch all medical records for a specific date using server-side date filtering
        
        Args:
            target_date: The date to fetch records for. If None, uses today's date.
        """
        try:
            if target_date is None:
                # Use today's records
                records = db.get_today_docs(
                    collection=self.medical_collection,
                    date_field="date",
                    limit=1000
                )
            else:
                # Use specific date
                records = db.get_docs_for_date(
                    collection=self.medical_collection,
                    target_date=target_date,
                    date_field="date",
                    limit=1000
                )
            
            # Calculate total collection
            total_collection = 0
            for record in records:
                payment = record.get('payment', {})
                if isinstance(payment, dict):
                    total_collection += payment.get('amount', 0)
                elif hasattr(payment, 'amount'):
                    total_collection += payment.amount
            
            return records, total_collection
            
        except Exception as e:
            logger.error(f"Error fetching daily collections: {str(e)}")
            return [], 0
    
    def fetch_daily_expenses(self, target_date: datetime = None):
        """Fetch all expenses for a specific date using server-side date filtering
        
        Args:
            target_date: The date to fetch expenses for. If None, uses today's date.
        """
        try:
            if target_date is None:
                # Use today's expenses
                expenses = db.get_today_docs(
                    collection=self.expense_collection,
                    date_field="date",
                    limit=1000
                )
            else:
                # Use specific date
                expenses = db.get_docs_for_date(
                    collection=self.expense_collection,
                    target_date=target_date,
                    date_field="date",
                    limit=1000
                )
            
            # Calculate total expenses
            total_expenses = 0
            for expense in expenses:
                total_expenses += expense.get('amount', 0)
            
            return expenses, total_expenses
            
        except Exception as e:
            logger.error(f"Error fetching daily expenses: {str(e)}")
            return [], 0
    
    def render(self, is_authorized: bool = False):
        if not is_authorized:
            st.warning("🔐 You need to be logged in and approved to access this page.")
            return
        
        # Header
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="color: #2ecc71; margin-bottom: 10px;">📊 Daily Report</h1>
            <p style="color: #666; font-size: 16px;">Overview of payments and expenses</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Get today's date
        today = get_ist_now()
        today_date = today.date()
        
        # Check if user is admin
        is_admin = self.is_admin_user()
        
        # Initialize selected_date to today for all users
        selected_date = today_date
        
        # Date selection for admins
        if is_admin:
            selected_date = st.date_input(
                label="Report Date",
                value=today_date,
                max_value=today_date,  # Cannot select future dates
                help="Select a date to view the daily report. You can view reports for any past date.",
                key="report_date_selector"
            )
            st.caption("💡 As an admin, you can view reports from any past date. Employees can only see today's report.")
            
            # Convert selected_date to datetime with IST timezone for querying
            from datetime import timezone, timedelta
            IST = timezone(timedelta(hours=5, minutes=30))
            target_date = datetime.combine(selected_date, datetime.min.time()).replace(tzinfo=IST)
            
            # Display the selected date
            st.markdown(f"### 📅 {selected_date.strftime('%A, %d %B %Y')}")
        else:
            # Non-admins can only see today's report
            target_date = None  # None means today
            st.markdown(f"### 📅 {today.strftime('%A, %d %B %Y')}")
        
        st.markdown("---")
        
        # Fetch data first for summary
        with st.spinner("Loading data..."):
            records, total_collection = self.fetch_daily_collections(target_date)
            expenses, total_expenses = self.fetch_daily_expenses(target_date)
        
        # Summary section at the top - Net Amount in a styled card
        net_amount = total_collection - total_expenses
        is_profit = net_amount >= 0
        
        # Styled summary card
        summary_color = "#2ecc71" if is_profit else "#e74c3c"
        summary_bg = "rgba(46, 204, 113, 0.1)" if is_profit else "rgba(231, 76, 60, 0.1)"
        status_text = "Money In" if is_profit else "Money Out"
        status_icon = "💰" if is_profit else "💸"
        
        st.markdown(f"""
        <div style="
            background: {summary_bg};
            border: 2px solid {summary_color};
            border-radius: 10px;
            padding: 18px 24px;
            text-align: center;
        ">
            <div style="color: #888; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Today's Balance</div>
            <div style="color: {summary_color}; font-size: 34px; font-weight: 700;">₹{net_amount:,} <span style="font-size: 15px; font-weight: 500;">{status_icon} {status_text}</span></div>
            <div style="color: #666; font-size: 12px; margin-top: 6px;">₹{total_collection:,} income · ₹{total_expenses:,} expenses</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Details in two columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 Income")
            
            # Display total income metric
            collection_label = "Total Payments Received Today" if (not is_admin or selected_date == today_date) else f"Total Payments Received ({selected_date.strftime('%d %b %Y')})"
            st.metric(
                label=collection_label,
                value=f"₹{total_collection:,}",
                help="Total payments received from medical records"
            )
            
            # Show number of records
            st.info(f"📋 {len(records)} patient(s) helped today")
            
            # Show breakdown if there are records
            if records:
                with st.expander("📄 View Payment Details", expanded=False):
                    for i, record in enumerate(records):
                        patient = record.get('patient', {})
                        payment = record.get('payment', {})
                        patient_name = patient.get('name', 'Unknown') if isinstance(patient, dict) else 'Unknown'
                        amount = payment.get('amount', 0) if isinstance(payment, dict) else 0
                        record_date = record.get('date', '')
                        
                        # Extract time using helper that handles both datetime and string formats
                        _, time_str = format_datetime_for_display(record_date)
                        
                        st.markdown(f"**{i+1}. {patient_name}** - ₹{amount:,} ({time_str})")
                        
                        # Show tests if available
                        tests = record.get('medical_tests', [])
                        if tests:
                            test_names = [t.get('name', '') for t in tests if isinstance(t, dict)]
                            if test_names:
                                st.caption(f"Tests: {', '.join(test_names)}")
                        
                        if i < len(records) - 1:
                            st.divider()
        
        with col2:
            st.markdown("### 💸 Expenses")
            
            # Display total expenses metric
            expense_label = "Total Expenses Today" if (not is_admin or selected_date == today_date) else f"Total Expenses ({selected_date.strftime('%d %b %Y')})"
            st.metric(
                label=expense_label,
                value=f"₹{total_expenses:,}",
                help="Total expenses recorded"
            )
            
            # Show number of expense records
            st.info(f"📋 {len(expenses)} expense record(s) today")
            
            # Show breakdown if there are expenses
            if expenses:
                with st.expander("📄 View Expense Details", expanded=False):
                    for i, expense in enumerate(expenses):
                        expense_type = expense.get('expense_type', 'Unknown')
                        amount = expense.get('amount', 0)
                        description = expense.get('description', '')
                        expense_date = expense.get('date', '')
                        
                        # Extract time using helper that handles both datetime and string formats
                        _, time_str = format_datetime_for_display(expense_date)
                        
                        st.markdown(f"**{i+1}. {expense_type}** - ₹{amount:,} ({time_str})")
                        if description:
                            st.caption(f"Description: {description}")
                        
                        if i < len(expenses) - 1:
                            st.divider()
        
        # Refresh button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Refresh Data", use_container_width=True, key="refresh_daily_report"):
                st.rerun()


class PrimeLabsUI:
    def __init__(self):
        self.user_auth = get_user_authentication()
        self.opening_screen = OpeningScreen(self.user_auth)

    def render(self):
        if st.session_state.get('user_email') and not self.user_auth.verify_token_validity():
            self.opening_screen.token_expired_screen()
            return
        
        is_authenticated = self.user_auth.check_authentication()
        
        # Check user status and show appropriate screen
        if is_authenticated:
            user_status = self.user_auth.get_user_status(st.session_state.user_email)
            
            if user_status == "rejected":
                self.opening_screen.show_rejected_screen()
                return
            elif user_status == "pending_approval":
                self.opening_screen.show_pending_approval_screen()
                return
        
        is_approved = self.user_auth.check_user_approval_status(st.session_state.user_email)


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
                
                # Page selection - include Admin only for project owners and Admin role users
                page_options = ["Medical Records", "Expenses", "Daily Report"]
                # Admin page accessible only to owners and Admin role users
                if (is_project_owner(st.session_state.user_email) or 
                    st.session_state.user_role == UserRole.ADMIN.value):
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
                        'doctor_name', 'doctor_location', 'test_type', 'test_types', 'payment_amount',
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
        try:
            if is_authenticated and is_authorized:
                if current_page == "Medical Records":
                    MedicalRecordForm().render(is_authorized)
                elif current_page == "Expenses":
                    ExpenseForm().render(is_authorized)
                elif current_page == "Daily Report":
                    DailyReportPage().render(is_authorized)
                elif current_page == "Admin":
                    # Show admin page only to project owners and Admin role users
                    if (is_project_owner(st.session_state.user_email) or 
                        st.session_state.user_role == UserRole.ADMIN.value):
                        self.opening_screen.show_admin_user_management()
                    else:
                        st.error("❌ Access denied. Admin page is only accessible to users with Admin role.")
            else:
                # Show medical records form by default for unauthorized users (they'll see the warning)
                MedicalRecordForm().render(is_authorized)
        except Exception as e:
            logger.error(f"Unexpected error rendering page '{current_page}': {str(e)}", exc_info=True)
            st.error("⚠️ **Something went wrong**")
            st.info("An unexpected error occurred. Please try refreshing the page. If the problem persists, contact the system administrator.")


if __name__ == '__main__':
    ui = PrimeLabsUI()
    ui.render()
