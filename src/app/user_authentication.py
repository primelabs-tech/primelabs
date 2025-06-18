import streamlit as st
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials
from google.oauth2 import service_account

from logger import logger
from utils import (
    get_firestore_admin_credential_dict,
    get_firebase_auth_config,
    get_firestore
)


USER_DB_COLLECTION = "users"


class UserAuthentication:
    def __init__(self):
        self._initialize_webapp()
        self.auth_client = self._get_auth_client()
        self.db: FirestoreCRUD = get_firestore()

    def login(self):
        pass

    def logout(self):
        pass

    def register(self):
        pass

    def reset_password(self):
        pass
        
    def _initialize_webapp(self):
        try:
            cred: dict = get_firestore_admin_credential_dict()
            cred = credentials.Certificate(cred)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            logger.error(f"Firebase initialization failed: {str(e)}")
            raise

    def _get_auth_client(self):
        auth_config = get_firebase_auth_config()

firebase = pyrebase.initialize_app(firebase_config)
firebase_auth = firebase.auth()

if __name__ == "__main__":
    user_auth = UserAuthentication()
    print (user_auth.db.get_docs(USER_DB_COLLECTION))