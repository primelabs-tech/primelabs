from typing import Optional

import streamlit as st
import pyrebase
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, auth
from google.oauth2 import service_account
from datetime import datetime

from logger import logger
from firestore_crud import get_firestore_admin_credential_dict, FirestoreCRUD
from utils import (
    get_firebase_auth_config,
    get_firestore,
    is_project_owner,
)
from data_models import UserRole, AuthorizationStatus


USER_DB_COLLECTION = "users"


class UserAuthentication:
    def __init__(self):
        self._initialize_webapp()
        self.auth_client = self._get_auth_client()
        self.db: FirestoreCRUD = get_firestore()
        self.auth_client = self._get_auth_client()
        self._initialize_session_state()
    
    def register(self, 
                    email: str, 
                    password: str,
                    name: str = "")->tuple[bool, str]:
        """Create user in firebase auth and db"""
        user = None
        try:
            user = self.auth_client.create_user_with_email_and_password(
                        email, password)
            user_data = {
                "email": email,
                "name": name,
                "role": UserRole.EMPLOYEE.value, 
                "status": "pending_approval",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.db.create_doc(
                USER_DB_COLLECTION, 
                user_data,
                doc_id=user['localId']
            )
            return True, ""
        except Exception as e:
            if user:
                self.auth_client.delete_user(user['localId'])
            error_message = f"Error creating user: {str(e)}"
            logger.error(error_message)
            return False, error_message

    def login(self, email: str, password: str):
        """Login user and return user email"""
        if self.verify_token_validity():
            return
        try:
            user = self.auth_client.sign_in_with_email_and_password(
                        email, password)
            decoded_token = auth.verify_id_token(user['idToken'])
            user_email = decoded_token['email']
            user_role = self._get_user_role(user_email).value
            user_name = self._get_user_name(user_email)
            
            st.session_state.authenticated = True
            st.session_state.user_role = user_role
            st.session_state.user_email = user_email
            st.session_state.user_name = user_name
            st.session_state.user_token = user['idToken']
            st.session_state.user_id = decoded_token['uid']

            return True, ""
        except Exception as e:
            error_message = f"Error logging in: {str(e)}"
            logger.error(error_message)
            return False, error_message

    def reset_password(self, email: str)->tuple[bool, str]:
        """Send password reset email"""
        try:
            self.auth_client.send_password_reset_email(email)
            return True, ""
        except Exception as e:
            error_message = f"Error sending password reset email: {str(e)}"
            logger.error(error_message)
            return False, error_message

    def logout(self):
        """Logout the user"""
        self._initialize_session_state()

    def check_authentication(self):
        """Check if the user is authenticated"""
        if not self.verify_token_validity():
            self.logout()
            return False
        return True

    def is_current_user_owner(self)->AuthorizationStatus:
        """Check if the user is the project owner"""
        if not self.check_authentication():
            return AuthorizationStatus.UNAUTHENTICATED
        if is_project_owner(st.session_state.user_email):
            return AuthorizationStatus.OWNER
        return AuthorizationStatus.NON_OWNER

    def require_authorization(self, role: UserRole = None)->AuthorizationStatus:
        """Get authorization status of the user"""
        if not self.check_authentication():
            return AuthorizationStatus.UNAUTHENTICATED
        if not self.check_user_approval_status(
            st.session_state.user_email):
            return AuthorizationStatus.PENDING_APPROVAL
        if role and st.session_state.user_role != role.value:
            return AuthorizationStatus.UNAUTHORIZED
        
        return AuthorizationStatus.APPROVED

    @classmethod
    def verify_token_validity(cls):
        """Verify if the current token is still valid"""
        if not hasattr(st.session_state, 'user_token') or not st.session_state.user_token:
            return False
        try:
            decoded_token = auth.verify_id_token(st.session_state.user_token)
            return True
        except Exception as e:
            # Token is invalid or expired
            return False
    
    def check_user_approval_status(self, email):
        """Check if user account is approved (status must be 'approved')"""
        if not UserAuthentication.verify_token_validity():
            return False
        if is_project_owner(email):
            return True
        
        try:
            user_docs = self.db.get_docs(
                            USER_DB_COLLECTION, 
                            filters=[("email", "==", email)]
                        )
            if user_docs:
                user_data = user_docs[0]
                status = user_data.get("status", "")
                # Only 'approved' status grants access
                return status == "approved"
            else:
                return False
                
        except Exception as e:
            st.error(f"Error checking user status: {str(e)}")
            return False
    
    def can_manage_user_status(self, email: str) -> bool:
        """Check if user can manage other users' status (only Admin role users)"""
        if not self.check_authentication():
            return False
        
        # Project owners can always manage users
        if is_project_owner(email):
            return True
        
        # Only Admin role users can manage other users' status
        user_role = st.session_state.get('user_role', '')
        return user_role == UserRole.ADMIN.value
    
    def get_user_status(self, email: str) -> str:
        """Get user's current status (approved, pending_approval, rejected)"""
        if not UserAuthentication.verify_token_validity():
            return "unauthenticated"
        if is_project_owner(email):
            return "approved"
        
        try:
            user_docs = self.db.get_docs(
                            USER_DB_COLLECTION, 
                            filters=[("email", "==", email)]
                        )
            if user_docs:
                user_data = user_docs[0]
                return user_data.get("status", "pending_approval")
            else:
                return "pending_approval"
                
        except Exception as e:
            st.error(f"Error getting user status: {str(e)}")
            return "pending_approval"    

    def _get_user_role(self, email)->UserRole:
        """Get user role from db or return default role"""
        try:
            user_docs = self.db.get_docs(
                            USER_DB_COLLECTION, 
                            filters=[("email", "==", email)]
                        )
            if user_docs:
                user_data = user_docs[0]
                return UserRole(user_data.get("role", UserRole.EMPLOYEE.value))
            elif is_project_owner(email):
                return UserRole.ADMIN
            else:
                return UserRole.EMPLOYEE
                
        except Exception as e:
            st.error(f"Error getting user role: {str(e)}")
            return UserRole.EMPLOYEE
    
    def _get_user_name(self, email: str) -> str:
        """Get user name from db or return email as fallback"""
        try:
            user_docs = self.db.get_docs(
                            USER_DB_COLLECTION, 
                            filters=[("email", "==", email)]
                        )
            if user_docs:
                user_data = user_docs[0]
                name = user_data.get("name", "")
                return name if name else email
            return email
                
        except Exception as e:
            logger.error(f"Error getting user name: {str(e)}")
            return email
        
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
        firebase = pyrebase.initialize_app(auth_config)
        return firebase.auth()

    def _initialize_session_state(self):
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.user_email = None
        st.session_state.user_name = None
        st.session_state.user_token = None
        st.session_state.user_id = None

if __name__ == "__main__":
    user_auth = UserAuthentication()
    print (user_auth.db.get_docs(USER_DB_COLLECTION))