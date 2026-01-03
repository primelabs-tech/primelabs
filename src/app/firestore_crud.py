import logging
import streamlit as st
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account

from logger import logger


# Indian Standard Time offset (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


def get_firestore_admin_credential_dict()->dict:
    return {
                "type": st.secrets["type"],
                "project_id": st.secrets["project_id"],
                "private_key_id": st.secrets["private_key_id"],
                "private_key": st.secrets["private_key"].replace('\\n', '\n'),
                "client_email": st.secrets["client_email"],
                "client_id": st.secrets["client_id"],
                "auth_uri": st.secrets["auth_uri"],
                "token_uri": st.secrets["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["client_x509_cert_url"]
            }


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
        limit: int = 100,
        order_by: str = None,
        order_direction: str = "DESCENDING"
    ) -> List[Dict]:
        """Get documents from collection with optional filters and ordering"""
        try:
            query = self.db.collection(collection)
            
            # Apply filters if provided
            if filters:
                for field, op, value in filters:
                    query = query.where(filter=firestore.FieldFilter(field, op, value))
            
            # Apply ordering if specified
            if order_by:
                direction = (firestore.Query.DESCENDING 
                           if order_direction.upper() == "DESCENDING" 
                           else firestore.Query.ASCENDING)
                query = query.order_by(order_by, direction=direction)
            
            docs = query.limit(limit).stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Get docs failed: {str(e)}")
            raise

    def get_docs_by_date_range(
        self,
        collection: str,
        start_date: datetime,
        end_date: datetime,
        date_field: str = "date",
        additional_filters: List[tuple] = None,
        limit: int = 1000,
        order_direction: str = "DESCENDING"
    ) -> List[Dict]:
        """
        Get documents within a date range using server-side filtering.
        
        Args:
            collection: Firestore collection name
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            date_field: Name of the date field in documents
            additional_filters: Optional additional filters as list of (field, op, value) tuples
            limit: Maximum number of documents to return
            order_direction: "ASCENDING" or "DESCENDING"
            
        Returns:
            List of documents matching the date range
        """
        try:
            query = self.db.collection(collection)
            
            # Apply date range filters
            query = query.where(filter=firestore.FieldFilter(date_field, ">=", start_date))
            query = query.where(filter=firestore.FieldFilter(date_field, "<=", end_date))
            
            # Apply additional filters if provided
            if additional_filters:
                for field, op, value in additional_filters:
                    query = query.where(filter=firestore.FieldFilter(field, op, value))
            
            # Apply ordering
            direction = (firestore.Query.DESCENDING 
                        if order_direction.upper() == "DESCENDING" 
                        else firestore.Query.ASCENDING)
            query = query.order_by(date_field, direction=direction)
            
            docs = query.limit(limit).stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
            
        except Exception as e:
            logger.error(f"Get docs by date range failed: {str(e)}")
            raise

    def get_today_docs(
        self,
        collection: str,
        date_field: str = "date",
        additional_filters: List[tuple] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Get all documents for today (IST timezone).
        
        Args:
            collection: Firestore collection name
            date_field: Name of the date field in documents
            additional_filters: Optional additional filters
            limit: Maximum number of documents to return
            
        Returns:
            List of documents from today
        """
        # Get today's date range in IST
        now = datetime.now(IST)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return self.get_docs_by_date_range(
            collection=collection,
            start_date=start_of_day,
            end_date=end_of_day,
            date_field=date_field,
            additional_filters=additional_filters,
            limit=limit,
            order_direction="DESCENDING"
        )
