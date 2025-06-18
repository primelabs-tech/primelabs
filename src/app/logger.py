import logging
import streamlit as st
from datetime import datetime
from typing import Any


class Logger:
    def __init__(self):
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(user_email)s:%(user_role)s] - %(message)s'
        )
        self.logger = logging.getLogger('PrimeLabs')

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info level message"""
        self.logger.info(message, extra=self._get_extra_fields(**kwargs))
        
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error level message"""
        self.logger.error(message, extra=self._get_extra_fields(**kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning level message"""
        self.logger.warning(message, extra=self._get_extra_fields(**kwargs))

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug level message"""
        self.logger.debug(message, extra=self._get_extra_fields(**kwargs))

    def _get_extra_fields(self, **kwargs: Any) -> dict:
        """Get extra fields for logging"""
        extra = {
            'timestamp': datetime.now().isoformat(),
            'user_email': st.session_state.get('user_email', 'anonymous'),
            'user_role': st.session_state.get('user_role', 'unknown')
        }
        extra.update(kwargs)
        return extra


# Global logger instance
logger = Logger()
