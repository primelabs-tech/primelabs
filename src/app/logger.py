import logging
import streamlit as st
from datetime import datetime, timezone, timedelta
from typing import Any


# Indian Standard Time offset (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


class Logger:
    def __init__(self):
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] [%(user_email)s:%(user_role)s] %(filename)s:%(lineno)d: %(message)s'
        )
        self.logger = logging.getLogger()

    def _extract_logging_params(self, kwargs: dict) -> dict:
        """Extract reserved logging parameters from kwargs"""
        logging_params = {}
        for key in ('exc_info', 'stack_info', 'stacklevel'):
            if key in kwargs:
                logging_params[key] = kwargs.pop(key)
        return logging_params

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info level message"""
        log_params = self._extract_logging_params(kwargs)
        self.logger.info(message, extra=self._get_extra_fields(**kwargs), **log_params)
        
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error level message"""
        log_params = self._extract_logging_params(kwargs)
        self.logger.error(message, extra=self._get_extra_fields(**kwargs), **log_params)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning level message"""
        log_params = self._extract_logging_params(kwargs)
        self.logger.warning(message, extra=self._get_extra_fields(**kwargs), **log_params)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug level message"""
        log_params = self._extract_logging_params(kwargs)
        self.logger.debug(message, extra=self._get_extra_fields(**kwargs), **log_params)

    def _get_extra_fields(self, **kwargs: Any) -> dict:
        """Get extra fields for logging"""
        extra = {
            'timestamp': datetime.now(IST).isoformat(),
            'user_email': st.session_state.get('user_email', 'anonymous'),
            'user_role': st.session_state.get('user_role', 'unknown')
        }
        extra.update(kwargs)
        return extra


# Global logger instance
logger = Logger()
