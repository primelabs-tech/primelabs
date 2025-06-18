import time
import logging
from datetime import datetime

import streamlit as st
from auth import (
    check_authentication, 
    login_form, 
    logout, 
    require_auth
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
from firestore_crud import FirestoreCRUD


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@st.cache_resource
def get_firestore():
    return FirestoreCRUD(use_admin_sdk=True)


db = get_firestore()


class Form:
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


class PrimeLabsUI:
    def __init__(self):
        pass

    def render(self):
        with st.sidebar:
            st.title('PrimeLabs')
            st.write('Primelabs management system')
            
            # Add login/logout buttons in sidebar
            if check_authentication():
                st.write(f"Logged in as: {st.session_state.user_email}")
                st.write(f"Role: {st.session_state.user_role}")
                if st.button("Logout"):
                    logout()
            else:
                login_form()
            
            st.session_state.times_loaded = st.session_state.get('times_loaded', 0)
            st.session_state.times_loaded += 1
            st.write(f"Times loaded: {st.session_state.times_loaded}")
            
        Form().render()

if __name__ == '__main__':
    ui = PrimeLabsUI()
    ui.render()