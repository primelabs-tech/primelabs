import logging
import streamlit as st
from typing import Dict, List, Optional
from google.cloud import firestore
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account

from logger import logger
from utils import get_firestore_admin_credential_dict


FIRESTORE_DB_ID = "firestore_database_id"

class FirestoreCRUD:
    def __init__(self, use_admin_sdk: bool = False):
        """Initialize Firestore client with optional Admin SDK (now always uses google.cloud.firestore.Client)"""
        self.db = self._initialize_firestore()
        
    def _initialize_firestore(self):
        try:
            credentials_dict = get_firestore_admin_credential_dict()
            creds = service_account.Credentials.from_service_account_info(credentials_dict)
            database_id = st.secrets.get(FIRESTORE_DB_ID, "(default)")
            return firestore.Client(
                project=st.secrets["project_id"],
                credentials=creds,
                database=database_id
            )
        except Exception as e:
            logger.error(f"Firestore initialization failed: {str(e)}")
            raise

    # CRUD Operations
    def create_doc(
        self,
        collection: str,
        data: Dict,
        doc_id: Optional[str] = None
    ) -> str:
        """Create document with optional custom ID"""
        try:
            doc_ref = self.db.collection(collection)
            if doc_id:
                doc_ref = doc_ref.document(doc_id)
                doc_ref.set(data)
                return doc_id
            else:
                new_doc = doc_ref.add(data)
                return new_doc[1].id
        except Exception as e:
            logger.error(f"Create failed: {str(e)}")
            raise

    def read_doc(
        self,
        collection: str,
        doc_id: str
    ) -> Optional[Dict]:
        """Read single document"""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except NotFound:
            logger.warning(f"Document {doc_id} not found")
            return None
        except Exception as e:
            logger.error(f"Read failed: {str(e)}")
            raise

    def update_doc(
        self,
        collection: str,
        doc_id: str,
        updates: Dict,
        merge: bool = True
    ) -> None:
        """Update existing document"""
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.set(updates, merge=merge)
        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            raise

    def delete_doc(
        self,
        collection: str,
        doc_id: str
    ) -> None:
        """Delete document"""
        try:
            self.db.collection(collection).document(doc_id).delete()
        except Exception as e:
            logger.error(f"Delete failed: {str(e)}")
            raise

    def query_collection(
        self,
        collection: str,
        filters: List[tuple],
        limit: int = 10
    ) -> List[Dict]:
        """Query collection with filters"""
        try:
            query = self.db.collection(collection)
            for field, op, value in filters:
                query = query.where(field, op, value)
            docs = query.limit(limit).stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise

    def get_docs(
        self,
        collection: str,
        filters: List[tuple] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get documents from collection with optional filters"""
        try:
            query = self.db.collection(collection)
            
            # Apply filters if provided
            if filters:
                for field, op, value in filters:
                    query = query.where(field, op, value)
            
            docs = query.limit(limit).stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Get docs failed: {str(e)}")
            raise
