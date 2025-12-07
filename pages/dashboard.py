# app_pages/dashboard.py

import streamlit as st
from data_loader import load_all_user_data
from utils import calculate_monthly_stats, calculate_percentage_change


def dashboard_page():
    """Render modern, clean dashboard"""
    
    # Load data first
    data = None
    try:
        with st.spinner("Loading your financial data..."):
            data = load_all_user_data(st.session_state.user['id'])
    except Exception as e:
        st.error(f"Error loading data: {e}")
    
    # Calculate stats
    current_income = current_spending = current_savings = 0.0
    income_change = spending_change = savings_change = 0.0
    
    if data is not None and not data.empty and 'YearMonth' in data.columns:
        try:
            available_months = sorted(data['YearMonth'].unique())
            
            if len(available_months) >= 1:
                current_month = available_months[-1]
                current_stats = calculate_monthly_stats(data, current_month)
                
                current_income = current_stats['income']
                current_spending = current_stats['spending']
                current_savings = current_stats['savings']
                
                if len(available_months) >= 2:
                    prev_month = available_months[-2]
                    prev_stats = calculate_monthly_stats(data, prev_month)
                    
                    income_change = calculate_percentage_change(current_income, prev_stats['income'])
                    spending_change = calculate_percentage_change(current_spending, prev_stats['spending'])
                    savings_change = calculate_percentage_change(current_savings, prev_stats['savings'])
        except Exception as e:
            st.warning(f"Could not calculate statistics: {e}")
    
    # Header
    st.markdown(f"""
        <div style='padding: 2rem 0 1rem 0;'>
            <h1 style='font-size: 2.5rem; font-weight: 700; color: white; margin-bottom: 0.5rem;'>
                Welcome back, {st.session_state.user['username']}
            </h1>
            <p style='font-size: 1.1rem; color: rgba(255, 255, 255, 0.85);'>
                Here's your financial overview
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Stats cards
    st.markdown("<div style='margin-bottom: 2rem;'>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        delta_color = "🟢" if income_change >= 0 else "🔴"
        st.markdown(f"""
            <div style='background: white; border-radius: 16px; padding: 1.75rem; 
                 box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid #10b981;'>
                <div style='color: #6b7280; font-size: 0.875rem; font-weight: 600; 
                     text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;'>
                    💰 Total Income
                </div>
                <div style='font-size: 2rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem;'>
                    J${current_income:,.0f}
                </div>
                <div style='font-size: 0.875rem; color: #6b7280;'>
                    {delta_color} {abs(income_change):.1f}% from last month
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        delta_color = "🔴" if spending_change > 0 else "🟢"
        st.markdown(f"""
            <div style='background: white; border-radius: 16px; padding: 1.75rem; 
                 box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid #ef4444;'>
                <div style='color: #6b7280; font-size: 0.875rem; font-weight: 600; 
                     text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;'>
                    💸 Total Spending
                </div>
                <div style='font-size: 2rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem;'>
                    J${current_spending:,.0f}
                </div>
                <div style='font-size: 0.875rem; color: #6b7280;'>
                    {delta_color} {abs(spending_change):.1f}% from last month
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        delta_color = "🟢" if savings_change >= 0 else "🔴"
        st.markdown(f"""
            <div style='background: white; border-radius: 16px; padding: 1.75rem; 
                 box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid #3b82f6;'>
                <div style='color: #6b7280; font-size: 0.875rem; font-weight: 600; 
                     text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;'>
                    🎯 Net Savings
                </div>
                <div style='font-size: 2rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem;'>
                    J${current_savings:,.0f}
                </div>
                <div style='font-size: 0.875rem; color: #6b7280;'>
                    {delta_color} {abs(savings_change):.1f}% from last month
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Feature selection section
    if 'selected_feature' not in st.session_state or st.session_state.selected_feature is None:
        display_feature_selection(data)
    else:
        # Render selected feature - UPDATED IMPORTS
        if st.session_state.selected_feature == 'analysis':
            from app_pages.spending_analysis import spending_analysis_page
            spending_analysis_page()
        elif st.session_state.selected_feature == 'planner':
            if 'selected_sub_feature' in st.session_state and st.session_state.selected_sub_feature == 'possible_savings':
                from app_pages.possible_savings import possible_savings_page
                possible_savings_page()
            else:
                from app_pages.budget_planner import budget_planner_page
                budget_planner_page()
        elif st.session_state.selected_feature == 'network':
            from app_pages.network_analysis import network_analysis_page
            network_analysis_page()
        elif st.session_state.selected_feature == 'timemachine':  
            from app_pages.financial_time_machine import financial_time_machine_page
            financial_time_machine_page()


def display_feature_selection(data):
    """Display modern feature cards"""
    
    st.markdown("""
        <div style='margin: 2rem 0 1.5rem 0;'>
            <h2 style='font-size: 1.5rem; font-weight: 700; color: white; margin-bottom: 0.5rem;'>
                What would you like to do?
            </h2>
            <p style='font-size: 1rem; color: rgba(255, 255, 255, 0.85);'>
                Choose a tool to get started
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Grid of feature cards
    col1, col2 = st.columns(2)
    
    with col1:
        # Spending Analysis Card
        st.markdown("""
            <div style='background: white; border-radius: 20px; padding: 2rem; 
                 margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.07);
                 transition: all 0.3s ease; cursor: pointer;'
                 onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 12px 24px rgba(0,0,0,0.15)';"
                 onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.07)';">
                <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                    <div style='font-size: 2.5rem; margin-right: 1rem;'>📊</div>
                    <div style='font-size: 1.5rem; font-weight: 700; color: #111827;'>
                        Spending Analysis
                    </div>
                </div>
                <p style='color: #6b7280; font-size: 1rem; line-height: 1.6; margin-bottom: 0;'>
                    Upload bank statements and visualize your spending patterns with detailed charts and insights
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open Spending Analysis", key="btn_analysis", use_container_width=True, type="primary"):
            st.session_state.selected_feature = 'analysis'
            st.rerun()
        
        # Network Analysis Card
        st.markdown("""
            <div style='background: white; border-radius: 20px; padding: 2rem; 
                 margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.07);
                 transition: all 0.3s ease; cursor: pointer;'
                 onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 12px 24px rgba(0,0,0,0.15)';"
                 onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.07)';">
                <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                    <div style='font-size: 2.5rem; margin-right: 1rem;'>🌐</div>
                    <div style='font-size: 1.5rem; font-weight: 700; color: #111827;'>
                        Network Analysis
                    </div>
                </div>
                <p style='color: #6b7280; font-size: 1rem; line-height: 1.6; margin-bottom: 0;'>
                    Discover spending patterns and merchant relationships with interactive visualizations
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open Network Analysis", key="btn_network", use_container_width=True, type="primary"):
            st.session_state.selected_feature = 'network'
            st.rerun()
    
    with col2:
        # Budget Planner Card
        st.markdown("""
            <div style='background: white; border-radius: 20px; padding: 2rem; 
                 margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.07);
                 transition: all 0.3s ease; cursor: pointer;'
                 onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 12px 24px rgba(0,0,0,0.15)';"
                 onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.07)';">
                <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                    <div style='font-size: 2.5rem; margin-right: 1rem;'>📅</div>
                    <div style='font-size: 1.5rem; font-weight: 700; color: #111827;'>
                        Budget Planner
                    </div>
                </div>
                <p style='color: #6b7280; font-size: 1rem; line-height: 1.6; margin-bottom: 0;'>
                    Set monthly budgets, track progress, and get alerts when approaching limits
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open Budget Planner", key="btn_planner", use_container_width=True, type="primary"):
            st.session_state.selected_feature = 'planner'
            st.rerun()
        
        # Time Machine Card (Featured)
        st.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 border-radius: 20px; padding: 2rem; margin-bottom: 1.5rem; 
                 box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
                 transition: all 0.3s ease; cursor: pointer;'
                 onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 16px 32px rgba(102, 126, 234, 0.4)';"
                 onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 8px 16px rgba(102, 126, 234, 0.3)';">
                <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
                    <div style='font-size: 2.5rem; margin-right: 1rem;'>🔮</div>
                    <div>
                        <div style='font-size: 1.5rem; font-weight: 700; color: white;'>
                            Time Machine
                        </div>
                        <div style='background: rgba(255,255,255,0.2); display: inline-block; 
                             padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; 
                             font-weight: 600; color: white; margin-top: 0.25rem;'>
                            ⭐ NEW
                        </div>
                    </div>
                </div>
                <p style='color: rgba(255,255,255,0.95); font-size: 1rem; line-height: 1.6; margin-bottom: 0;'>
                    See your financial future based on today's decisions. Compare 3 different scenarios.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Open Time Machine", key="btn_timemachine", use_container_width=True, type="secondary"):
            st.session_state.selected_feature = 'timemachine'
            st.rerun()
    
    # Quick stats section
    if data is not None and not data.empty:
        st.markdown("""
            <div style='margin-top: 3rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.2);'>
                <h3 style='font-size: 1.25rem; font-weight: 700; color: white; margin-bottom: 1rem;'>
                    📈 Quick Insights
                </h3>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            total_transactions = len(data)
            unique_merchants = data['Description'].nunique() if 'Description' in data.columns else 0
            months_tracked = data['YearMonth'].nunique() if 'YearMonth' in data.columns else 0
            avg_transaction = data['Amount'].mean() if 'Amount' in data.columns else 0
            
            with col1:
                st.markdown(f"""
                    <div style='background: rgba(255,255,255,0.1); border-radius: 12px; padding: 1.25rem; text-align: center;'>
                        <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; font-weight: 600; 
                             text-transform: uppercase; margin-bottom: 0.5rem;'>
                            Transactions
                        </div>
                        <div style='font-size: 1.75rem; font-weight: 700; color: white;'>
                            {total_transactions:,}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                    <div style='background: rgba(255,255,255,0.1); border-radius: 12px; padding: 1.25rem; text-align: center;'>
                        <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; font-weight: 600; 
                             text-transform: uppercase; margin-bottom: 0.5rem;'>
                            Merchants
                        </div>
                        <div style='font-size: 1.75rem; font-weight: 700; color: white;'>
                            {unique_merchants}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                    <div style='background: rgba(255,255,255,0.1); border-radius: 12px; padding: 1.25rem; text-align: center;'>
                        <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; font-weight: 600; 
                             text-transform: uppercase; margin-bottom: 0.5rem;'>
                            Months Tracked
                        </div>
                        <div style='font-size: 1.75rem; font-weight: 700; color: white;'>
                            {months_tracked}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                    <div style='background: rgba(255,255,255,0.1); border-radius: 12px; padding: 1.25rem; text-align: center;'>
                        <div style='color: rgba(255,255,255,0.8); font-size: 0.75rem; font-weight: 600; 
                             text-transform: uppercase; margin-bottom: 0.5rem;'>
                            Avg Transaction
                        </div>
                        <div style='font-size: 1.75rem; font-weight: 700; color: white;'>
                            J${avg_transaction:,.0f}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            pass
