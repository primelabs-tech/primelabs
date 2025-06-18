import time
import logging
from datetime import datetime

import streamlit as st
from auth import (
    check_authentication, 
    login_form, 
    logout, 
    require_auth,
    show_admin_menu,
    admin_user_management,
    check_user_approval_status,
    show_pending_approval_screen,
    show_token_expired_message
)
from data_models import (
    MedicalRecord,
    Patient, 
    Doctor, 
    MedicalTest,  
    Payment, 
    User,
    DBCollectionNames,
)
from user_authentication import UserAuthentication
from utils import get_firestore, get_user_authentication
from logger import logger


db = get_firestore()


class MedicalRecordForm:
    def __init__(self):
        self.database_collection = DBCollectionNames(st.secrets["database_collection"]).value
    
    def show_temporary_messages(self, medical_record):
        # Create a placeholder for temporary messages
        message_placeholder = st.empty()
        message_placeholder.markdown(str(medical_record), unsafe_allow_html=True)
        time.sleep(3)
        message_placeholder.empty()
    
    def render(self):
        if not require_auth():
            return
            
        st.header('Medical Test Entry')

        ## Patient Information
        patient_name = st.text_input(
                            label="Patient's Name",
                            label_visibility="hidden",
                            placeholder="Patient's Name", 
                            help='Enter the name of the patient')
        patient = Patient(name=patient_name)
        
        phone_col1, phone_col2 = st.columns(2)
        phone_available = phone_col1.checkbox("Patient's Phone")
        if phone_available:
            patient_phone = phone_col2.text_input(
                            label="Patient's Phone",
                            label_visibility="hidden",
                            placeholder="Patient's Phone Number", 
                            help='Enter the phone number of the patient')
            patient.phone = patient_phone
        
        address_col1, address_col2 = st.columns(2)
        address_available = address_col1.checkbox("Patient's Address")
        if address_available:
            patient_address = address_col2.text_input(
                            label="Patient's Address",
                            label_visibility="hidden",
                            placeholder="Patient's Address", 
                            help='Enter the address of the patient')
            patient.address = patient_address
            
        
        ## Referral Information
        referring_doctor = None
        referral_col1, referral_col2 = st.columns(2)
        through_referral = referral_col1.checkbox("Referral")
        if through_referral:
            doctor_name = referral_col2.text_input(
                            label="Doctor's Name",
                            label_visibility="hidden",
                            placeholder="Doctor's Name", 
                            help='Enter the name of the doctor')
            doctor_location = referral_col2.text_input(
                            label="Doctor's Location",
                            label_visibility="hidden",
                            placeholder="Doctor's Location", 
                            help='Enter the location of the doctor')
            referring_doctor = Doctor(name=doctor_name, location=doctor_location)
        
        

        TEST_PRICES = {
            'Blood Test': 200,
            'Urine Test': 150,
            'X-Ray': 500,
            'MRI': 1500
        }
        testinfo_col1, testinfo_col2 =  st.columns(2)        
        test_name = testinfo_col1.selectbox(
                            label='Test Type',
                            options=list(TEST_PRICES.keys()),
                            help='Select the medical test')
        
        
        test_price = testinfo_col2.text_input(
                            label='Price',
                            disabled=True,
                            value =f"{TEST_PRICES[test_name]} Rupees",
                            )
        
        ## Payment Information
        payment_col1, payment_col2 = st.columns(2)
        payment_amount  = payment_col1.number_input(
                            label='Payment',
                            step=100,
                            help='Enter the payment amount')
        payment = Payment(amount=payment_amount)
        comments = payment_col2.text_area(
                            label='Comments',
                            help='Enter any comments')

            
        submitted = st.button(label='Submit')
        
        if submitted:
            try:
                medical_entry = MedicalRecord(
                    patient=patient,
                    doctor=referring_doctor,
                    medical_test=MedicalTest(name=test_name, price=TEST_PRICES[test_name]),
                    payment=payment,
                    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    comments=comments,
                    updated_by=st.session_state.user_role
                )
                db.create_doc(
                    self.database_collection, 
                    medical_entry.model_dump(mode="json")
                )
                self.show_temporary_messages(medical_entry)

            except Exception as e:
                st.write(e)



class LoginScreen:
    def __init__(self, user_auth: UserAuthentication):
        self.user_auth = user_auth

    @classmethod
    def show_pending_approval_screen(cls):
        pass
    
    def login_screen(self):
        """Display login form and handle authentication"""
        st.title("Login")
        
        auth_mode = st.radio("Choose an option:", ["Login", "Register", "Reset Password"], horizontal=True)
        
        if auth_mode == "Reset Password":
            self.()
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


    def reset_password_screen(self):
        """Handle password reset"""
        st.subheader("Reset Password")
        reset_email = st.text_input("Enter your email address")
        
        if st.button("Send Reset Email"):
            if not reset_email:
                st.error("Please enter your email address")
                return
            is_email_sent, error_message = self.user_auth.reset_password(reset_email)
            if is_email_sent:
                st.success("Password reset email sent! Check your inbox.")
            elif "EMAIL_NOT_FOUND" in error_message:
                st.error("No account found with this email address")
            else:
                st.error(f"Error sending reset email: {str(e)}")
            
                



class PrimeLabsUI:
    def __init__(self):
        self.user_auth = get_user_authentication()

    def render(self):
        # Check if user is authenticated and approved before rendering anything
        if check_authentication():
            # Check approval status for authenticated users
            if not check_user_approval_status(st.session_state.user_email):
                # Show pending approval screen and block all other content
                show_pending_approval_screen()
                return
        
        with st.sidebar:
            st.title('PrimeLabs')
            st.write('Primelabs management system')
            
            # Add login/logout buttons in sidebar
            if check_authentication():
                st.write(f"Logged in as: {st.session_state.user_email}")
                st.write(f"Role: {st.session_state.user_role}")
                if st.button("Logout"):
                    logout()
                
                # Show admin menu if user is project owner
                show_admin_menu()
            else:
                login_form()
            
            st.session_state.times_loaded = st.session_state.get('times_loaded', 0)
            st.session_state.times_loaded += 1
            st.write(f"Times loaded: {st.session_state.times_loaded}")
            
        # Show admin panel if requested
        if st.session_state.get('show_admin', False):
            admin_user_management()
        else:
            MedicalRecordForm().render()


if __name__ == '__main__':
    ui = PrimeLabsUI()
    ui.render()
