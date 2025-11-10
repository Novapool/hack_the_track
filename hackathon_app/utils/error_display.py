"""
Streamlit Error Display Utilities

Provides enhanced error display and debugging information for the dashboard.
"""

import streamlit as st
import traceback
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def display_detailed_error(error: Exception, context: str = "", show_traceback: bool = True):
    """
    Display a detailed error message in Streamlit with debugging information.

    Args:
        error: The exception that occurred
        context: Additional context about where/why the error occurred
        show_traceback: Whether to show the full traceback (default: True)
    """
    st.error("🔴 An error occurred")

    with st.expander("🔍 Error Details", expanded=True):
        # Basic error info
        st.markdown(f"**Error Type:** `{type(error).__name__}`")
        st.markdown(f"**Error Message:** {str(error)}")

        if context:
            st.markdown(f"**Context:** {context}")

        # Timestamp
        st.markdown(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Full traceback
        if show_traceback:
            st.markdown("**Full Traceback:**")
            tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            st.code(tb_str, language="python")

    # Log file location
    log_dir = Path(__file__).parent.parent / "logs"
    log_file = log_dir / f"tire_whisperer_{datetime.now().strftime('%Y%m%d')}.log"

    if log_file.exists():
        st.info(f"📄 Detailed logs available at: `{log_file}`")
        st.markdown("Check the log file for more information about what happened before this error.")


def display_warning_with_logs(message: str, details: Optional[str] = None):
    """
    Display a warning message with optional additional details.

    Args:
        message: Main warning message
        details: Additional details to show in expander
    """
    st.warning(f"⚠️ {message}")

    if details:
        with st.expander("ℹ️ More Information"):
            st.markdown(details)


def display_debug_info(data: dict, title: str = "Debug Information"):
    """
    Display debug information in an expander.

    Args:
        data: Dictionary of debug information to display
        title: Title for the debug section
    """
    with st.expander(f"🐛 {title}", expanded=False):
        for key, value in data.items():
            st.markdown(f"**{key}:** `{value}`")


def create_error_report(error: Exception, context: str = "") -> str:
    """
    Create a formatted error report string.

    Args:
        error: The exception that occurred
        context: Additional context

    Returns:
        Formatted error report string
    """
    report = [
        "=" * 80,
        "ERROR REPORT",
        "=" * 80,
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Error Type: {type(error).__name__}",
        f"Error Message: {str(error)}",
        ""
    ]

    if context:
        report.extend([
            f"Context: {context}",
            ""
        ])

    report.extend([
        "Traceback:",
        "-" * 80,
        "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        "=" * 80
    ])

    return "\n".join(report)


def safe_execute(func, *args, error_context: str = "", **kwargs):
    """
    Safely execute a function and display errors in Streamlit if they occur.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        error_context: Context description for error messages
        **kwargs: Keyword arguments for the function

    Returns:
        Function result, or None if an error occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        display_detailed_error(e, context=error_context)
        return None


def display_data_quality_warning(issue: str, recommendation: str):
    """
    Display a data quality warning with recommendations.

    Args:
        issue: Description of the data quality issue
        recommendation: Recommended action to take
    """
    st.warning(f"📊 Data Quality Issue: {issue}")
    st.info(f"💡 Recommendation: {recommendation}")


def check_log_file_size():
    """
    Check the size of the current log file and display a warning if it's large.
    """
    log_dir = Path(__file__).parent.parent / "logs"
    log_file = log_dir / f"tire_whisperer_{datetime.now().strftime('%Y%m%d')}.log"

    if log_file.exists():
        size_mb = log_file.stat().st_size / (1024 * 1024)
        if size_mb > 10:  # Warn if log file is larger than 10MB
            st.sidebar.warning(f"⚠️ Log file is large ({size_mb:.1f} MB). Consider clearing old logs.")
