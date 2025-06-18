import streamlit as st
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials
from google.oauth2 import service_account

from logger import logger
from utils import get_firestore_admin_credential_dict


FIRESTORE_DB_SECRET_KEY = "firestore_database_id"


class UserAuthentication:
    def __init__(self):
        self.initialize_webapp()
        self._set_db_client()
        

    def login(self):
        pass

    def logout(self):
        pass

    def register(self):
        pass

    def reset_password(self):
        pass

    def _set_admin_credential_dict(self):
        """
        Set the admin credentials from the secrets.
        """
        if not hasattr(self, 'admin_credential_dict'):
            return get_firestore_admin_credential_dict()
    
    def _get_credentials(self):
        if hasattr(self, "credentials"):
            return
        self._set_admin_credential_dict()
        self.credentials = service_account.Credentials.from_service_account_info(
             self.admin_credential_dict) 

    def _set_db_client(self):
        if hasattr(self, 'db_client'):
            return
        
        self._get_credentials()
        database_id = st.secrets.get(FIRESTORE_DB_SECRET_KEY, 
                                        "(default)")
        self.db_client = firestore.Client(
            project=self.admin_credential_dict["project_id"],
            credentials=self.credentials,
            database=database_id
        )

    def get_db_client(self) -> firestore.Client:
        try:
            self._set_db_client()
            return self.db_client
        except Exception as e:
            logger.error(f"Firestore initialization failed: {str(e)}")
            raise
        
    def initialize_webapp(self):
        try:
            self._set_admin_credential_dict()
            cred = credentials.Certificate(self.admin_credential_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            logger.error(f"Firebase initialization failed: {str(e)}")
            raise

if __name__ == "__main__":
    user_auth = UserAuthentication()
    import pdb; pdb.set_trace()
    print(user_auth.get_db_client())
