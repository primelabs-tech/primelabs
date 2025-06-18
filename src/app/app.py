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
