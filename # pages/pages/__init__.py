# pages/__init__.py
"""
Pages module - exports all page rendering functions
"""

from .auth_pages import login_page, register_page
from .dashboard import dashboard_page
from .spending_analysis import spending_analysis_page

__all__ = [
    'login_page',
    'register_page',
    'dashboard_page',
    'spending_analysis_page'
]
