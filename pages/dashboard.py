# pages/dashboard.py

import streamlit as st
from data_loader import load_all_user_data
from utils import calculate_monthly_stats, calculate_percentage_change


def dashboard_page():
    """Render main dashboard"""
    # Header
    st.markdown(f"""
        <div style='text-align: center; padding: 2rem 0 1rem 0;'>
            <h1 style='font-size: 3rem; font-weight: 700; color: white; margin-bottom: 0.5rem;'>
                💼 Finance Hub Dashboard
            </h1>
            <p style='font-size: 1.25rem; color: rgba(255, 255, 255, 0.9);'>
                Welcome back, {st.session_state.user['username']}! Your financial command center
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Load and display stats
    display_quick_stats()
    
    # Feature selection
    if 'selected_feature' not in st.session_state or st.session_state.selected_feature is None:
        display_feature_selection()
    else:
        # Render selected feature
        if st.session_state.selected_feature == 'analysis':
            from .spending_analysis import spending_analysis_page
            spending_analysis_page()
        elif st.session_state.selected_feature == 'planner':
            # Check if sub-feature is selected
            if 'selected_sub_feature' in st.session_state and st.session_state.selected_sub_feature == 'possible_savings':
                from .possible_savings import possible_savings_page
                possible_savings_page()
            else:
                from .budget_planner import budget_planner_page
                budget_planner_page()
        elif st.session_state.selected_feature == 'network':
            from .network_analysis import network_analysis_page
            network_analysis_page()
        elif st.session_state.selected_feature == 'timemachine':  # ← ADD THIS BLOCK
            from .financial_time_machine import financial_time_machine_page
            financial_time_machine_page()


def display_quick_stats():
    """Display quick statistics cards"""
    try:
        with st.spinner("Loading your financial data..."):
            data = load_all_user_data(st.session_state.user['id'])
    except Exception as e:
        st.error(f"Error loading data: {e}")
        data = None
    
    # Initialize default values
    current_income = current_spending = current_savings = 0.0
    income_change = spending_change = savings_change = 0.0
    income_arrow = spending_arrow = savings_arrow = "→"
    income_class = spending_class = savings_class = "positive"
    
    if data is not None and not data.empty and 'YearMonth' in data.columns:
        try:
            available_months = sorted(data['YearMonth'].unique())
            
            if len(available_months) >= 1:
                current_month = available_months[-1]
                current_stats = calculate_monthly_stats(data, current_month)
                
                current_income = current_stats['income']
                current_spending = current_stats['spending']
                current_savings = current_stats['savings']
                
                # Calculate changes if previous month exists
                if len(available_months) >= 2:
                    prev_month = available_months[-2]
                    prev_stats = calculate_monthly_stats(data, prev_month)
                    
                    income_change = calculate_percentage_change(current_income, prev_stats['income'])
                    spending_change = calculate_percentage_change(current_spending, prev_stats['spending'])
                    savings_change = calculate_percentage_change(current_savings, prev_stats['savings'])
                    
                    # Set arrows and classes
                    income_arrow = "↑" if income_change > 0 else ("↓" if income_change < 0 else "→")
                    spending_arrow = "↑" if spending_change > 0 else ("↓" if spending_change < 0 else "→")
                    savings_arrow = "↑" if savings_change > 0 else ("↓" if savings_change < 0 else "→")
                    
                    income_class = "positive" if income_change >= 0 else "negative"
                    spending_class = "negative" if spending_change > 0 else "positive"
                    savings_class = "positive" if savings_change >= 0 else "negative"
        except Exception as e:
            st.warning(f"Could not calculate statistics: {e}")
    
    # Display stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div class="stat-card income">
                <div class="stat-title">💰 Total Income</div>
                <div class="stat-value">J${current_income:,.0f}</div>
                <div class="stat-change {income_class}">{income_arrow} {abs(income_change):.1f}% from last month</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-card spending">
                <div class="stat-title">💸 Total Spending</div>
                <div class="stat-value">J${current_spending:,.0f}</div>
                <div class="stat-change {spending_class}">{spending_arrow} {abs(spending_change):.1f}% from last month</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stat-card savings">
                <div class="stat-title">🎯 Net Savings</div>
                <div class="stat-value">J${current_savings:,.0f}</div>
                <div class="stat-change {savings_class}">{savings_arrow} {abs(savings_change):.1f}% from last month</div>
            </div>
        """, unsafe_allow_html=True)


def display_feature_selection():
    """Display feature selection cards - UPDATED WITH TIME MACHINE"""
    
    # ========================================
    # FIRST ROW - EXISTING 3 FEATURES
    # ========================================
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-title">Spending Analysis</div>
                <div class="feature-desc">Upload statements and analyze your spending patterns with detailed insights</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Analysis", key="btn_analysis", use_container_width=True):
            st.session_state.selected_feature = 'analysis'
            st.rerun()
    
    with col2:
        st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📅</div>
                <div class="feature-title">Budget Planner</div>
                <div class="feature-desc">Create and manage your monthly budgets efficiently</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Planner", key="btn_planner", use_container_width=True):
            st.session_state.selected_feature = 'planner'
            st.rerun()
    
    with col3:
        st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🌐</div>
                <div class="feature-title">Network Analysis</div>
                <div class="feature-desc">Visualize transaction patterns and relationships</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Open Network", key="btn_network", use_container_width=True):
            st.session_state.selected_feature = 'network'
            st.rerun()
    
    # ========================================
    # SECOND ROW - TIME MACHINE (CENTERED)
    # ========================================
    st.markdown("<br/>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class="feature-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 border: 3px solid gold; box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);">
                <div class="feature-icon" style="font-size: 4rem;">🔮</div>
                <div class="feature-title" style="color: white; font-size: 1.5rem;">Financial Time Machine</div>
                <div class="feature-desc" style="color: rgba(255,255,255,0.95); font-size: 1rem;">
                    ⭐ NEW! See your financial future based on today's decisions. 
                    Visualize 3 possible paths and when you'll retire.
                </div>
                <div style="background: rgba(255,255,255,0.2); padding: 0.5rem; border-radius: 8px; 
                     margin-top: 1rem; color: white; font-weight: 600;">
                    🚀 Revolutionary Feature - Never Done Before!
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔮 Launch Time Machine", key="btn_timemachine", 
                     use_container_width=True, type="primary"):
            st.session_state.selected_feature = 'timemachine'
            st.rerun()
