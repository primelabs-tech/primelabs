import logging
import streamlit as st
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from google.cloud import firestore
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account

from logger import logger


# Indian Standard Time offset (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class PaginatedResult:
    """Result container for paginated queries."""
    documents: List[Dict]
    next_cursor: Optional[Any]  # Document snapshot for start_after()
    has_more: bool
    total_fetched: int


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

    def get_docs_for_date(
        self,
        collection: str,
        target_date: datetime,
        date_field: str = "date",
        additional_filters: List[tuple] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Get all documents for a specific date (IST timezone).
        
        Args:
            collection: Firestore collection name
            target_date: The date to fetch documents for (datetime object)
            date_field: Name of the date field in documents
            additional_filters: Optional additional filters
            limit: Maximum number of documents to return
            
        Returns:
            List of documents from the specified date
        """
        # Ensure the date is in IST
        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=IST)
        
        # Get start and end of the target date
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return self.get_docs_by_date_range(
            collection=collection,
            start_date=start_of_day,
            end_date=end_of_day,
            date_field=date_field,
            additional_filters=additional_filters,
            limit=limit,
            order_direction="DESCENDING"
        )

    # ==================== PAGINATION METHODS ====================

    def get_docs_paginated(
        self,
        collection: str,
        page_size: int = 20,
        cursor: Any = None,
        filters: List[tuple] = None,
        order_by: str = None,
        order_direction: str = "DESCENDING"
    ) -> PaginatedResult:
        """
        Get documents with cursor-based pagination using start_after().
        
        This is efficient for large datasets as it doesn't require offset counting.
        Firestore uses the cursor (document snapshot) to jump directly to the next page.
        
        Args:
            collection: Firestore collection name
            page_size: Number of documents per page
            cursor: Document snapshot from previous query's next_cursor (None for first page)
            filters: Optional list of (field, op, value) filter tuples
            order_by: Field to order by (required for consistent pagination)
            order_direction: "ASCENDING" or "DESCENDING"
            
        Returns:
            PaginatedResult with documents, next_cursor, has_more flag, and total_fetched
            
        Example:
            # First page
            result = db.get_docs_paginated("users", page_size=20, order_by="date")
            
            # Next page
            if result.has_more:
                result = db.get_docs_paginated("users", page_size=20, 
                                                cursor=result.next_cursor, order_by="date")
        """
        try:
            query = self.db.collection(collection)
            
            # Apply filters if provided
            if filters:
                for field, op, value in filters:
                    query = query.where(filter=firestore.FieldFilter(field, op, value))
            
            # Apply ordering (required for consistent pagination)
            if order_by:
                direction = (firestore.Query.DESCENDING 
                           if order_direction.upper() == "DESCENDING" 
                           else firestore.Query.ASCENDING)
                query = query.order_by(order_by, direction=direction)
            
            # Apply cursor for pagination (start after the last document of previous page)
            if cursor is not None:
                query = query.start_after(cursor)
            
            # Fetch page_size + 1 to check if there are more documents
            docs_stream = query.limit(page_size + 1).stream()
            docs_list = list(docs_stream)
            
            # Check if there are more documents beyond this page
            has_more = len(docs_list) > page_size
            
            # Only return page_size documents
            if has_more:
                docs_list = docs_list[:page_size]
            
            # Get the last document snapshot for the next cursor
            next_cursor = docs_list[-1] if docs_list else None
            
            # Convert to dictionaries
            documents = [{"id": doc.id, **doc.to_dict()} for doc in docs_list]
            
            return PaginatedResult(
                documents=documents,
                next_cursor=next_cursor,
                has_more=has_more,
                total_fetched=len(documents)
            )
            
        except Exception as e:
            logger.error(f"Paginated query failed: {str(e)}")
            raise

    def get_docs_by_date_range_paginated(
        self,
        collection: str,
        start_date: datetime,
        end_date: datetime,
        date_field: str = "date",
        page_size: int = 20,
        cursor: Any = None,
        additional_filters: List[tuple] = None,
        order_direction: str = "DESCENDING"
    ) -> PaginatedResult:
        """
        Get documents within a date range with cursor-based pagination.
        
        Args:
            collection: Firestore collection name
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            date_field: Name of the date field in documents
            page_size: Number of documents per page
            cursor: Document snapshot from previous query (None for first page)
            additional_filters: Optional additional filters
            order_direction: "ASCENDING" or "DESCENDING"
            
        Returns:
            PaginatedResult with documents and pagination info
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
            
            # Apply cursor for pagination
            if cursor is not None:
                query = query.start_after(cursor)
            
            # Fetch page_size + 1 to check for more
            docs_stream = query.limit(page_size + 1).stream()
            docs_list = list(docs_stream)
            
            has_more = len(docs_list) > page_size
            if has_more:
                docs_list = docs_list[:page_size]
            
            next_cursor = docs_list[-1] if docs_list else None
            documents = [{"id": doc.id, **doc.to_dict()} for doc in docs_list]
            
            return PaginatedResult(
                documents=documents,
                next_cursor=next_cursor,
                has_more=has_more,
                total_fetched=len(documents)
            )
            
        except Exception as e:
            logger.error(f"Paginated date range query failed: {str(e)}")
            raise

    def get_all_docs_generator(
        self,
        collection: str,
        batch_size: int = 100,
        filters: List[tuple] = None,
        order_by: str = None,
        order_direction: str = "DESCENDING"
    ):
        """
        Generator that yields all documents in batches using cursor-based pagination.
        
        Memory-efficient way to iterate over large collections without loading
        everything into memory at once.
        
        Args:
            collection: Firestore collection name
            batch_size: Number of documents to fetch per batch
            filters: Optional list of (field, op, value) filter tuples
            order_by: Field to order by
            order_direction: "ASCENDING" or "DESCENDING"
            
        Yields:
            Document dictionaries one at a time
            
        Example:
            for doc in db.get_all_docs_generator("medical_records", batch_size=100, order_by="date"):
                process(doc)
        """
        cursor = None
        
        while True:
            result = self.get_docs_paginated(
                collection=collection,
                page_size=batch_size,
                cursor=cursor,
                filters=filters,
                order_by=order_by,
                order_direction=order_direction
            )
            
            for doc in result.documents:
                yield doc
            
            if not result.has_more:
                break
                
            cursor = result.next_cursor

    def count_docs(
        self,
        collection: str,
        filters: List[tuple] = None
    ) -> int:
        """
        Count documents in a collection (with optional filters).
        
        Note: For very large collections, consider using Firestore's 
        aggregation queries if available in your SDK version.
        
        Args:
            collection: Firestore collection name
            filters: Optional list of (field, op, value) filter tuples
            
        Returns:
            Count of matching documents
        """
        try:
            query = self.db.collection(collection)
            
            if filters:
                for field, op, value in filters:
                    query = query.where(filter=firestore.FieldFilter(field, op, value))
            
            # Use count aggregation if available (Firestore SDK >= 2.11.0)
            try:
                count_query = query.count()
                result = count_query.get()
                return result[0][0].value
            except AttributeError:
                # Fallback: count by iterating (less efficient for large collections)
                # Only fetch document IDs to minimize data transfer
                return sum(1 for _ in query.select([]).stream())
                
        except Exception as e:
            logger.error(f"Count query failed: {str(e)}")
            raise
