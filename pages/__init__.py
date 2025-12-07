# app_pages/__init__.py
# Import all page functions
from .auth_pages import login_page, register_page
from .dashboard import dashboard_page
from .spending_analysis import spending_analysis_page
from .budget_planner import budget_planner_page
from .financial_time_machine import financial_time_machine_page
from .network_analysis import network_analysis_page
from .possible_savings import possible_savings_page

# Export all functions
__all__ = [
    'login_page',
    'register_page', 
    'dashboard_page',
    'spending_analysis_page',
    'budget_planner_page',
    'financial_time_machine_page',
    'network_analysis_page',
    'possible_savings_page'
]
