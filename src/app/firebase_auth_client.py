"""
Firebase Authentication Client using REST API.
Replaces pyrebase to avoid gcloud/pkg_resources compatibility issues with Python 3.13+.
"""

import requests
from typing import Optional


class FirebaseAuthClient:
    """Firebase Authentication client using REST API."""
    
    FIREBASE_AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts"
    
    def __init__(self, api_key: str):
        """Initialize the Firebase Auth client.
        
        Args:
            api_key: Firebase Web API key
        """
        self.api_key = api_key
    
    def _make_request(self, endpoint: str, data: dict) -> dict:
        """Make a request to Firebase Auth REST API.
        
        Args:
            endpoint: API endpoint (e.g., 'signInWithPassword')
            data: Request payload
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.FIREBASE_AUTH_URL}:{endpoint}?key={self.api_key}"
        response = requests.post(url, json=data)
        
        if response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            raise Exception(f"Firebase Auth Error: {error_message}")
        
        return response.json()
    
    def create_user_with_email_and_password(self, email: str, password: str) -> dict:
        """Create a new user with email and password.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Dictionary containing user data including 'localId' and 'idToken'
        """
        data = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        return self._make_request("signUp", data)
    
    def sign_in_with_email_and_password(self, email: str, password: str) -> dict:
        """Sign in a user with email and password.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Dictionary containing user data including 'localId' and 'idToken'
        """
        data = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        return self._make_request("signInWithPassword", data)
    
    def send_password_reset_email(self, email: str) -> dict:
        """Send a password reset email.
        
        Args:
            email: User's email address
            
        Returns:
            Response data
        """
        data = {
            "requestType": "PASSWORD_RESET",
            "email": email
        }
        return self._make_request("sendOobCode", data)
    
    def delete_user(self, id_token: str) -> dict:
        """Delete a user account.
        
        Args:
            id_token: User's ID token
            
        Returns:
            Response data
        """
        data = {
            "idToken": id_token
        }
        return self._make_request("delete", data)
    
    def refresh_token(self, refresh_token: str) -> dict:
        """Refresh an ID token using a refresh token.
        
        Args:
            refresh_token: User's refresh token
            
        Returns:
            Dictionary containing new tokens
        """
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        response = requests.post(url, data=data)
        
        if response.status_code != 200:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            raise Exception(f"Firebase Auth Error: {error_message}")
        
        return response.json()
