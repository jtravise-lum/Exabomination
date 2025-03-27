"""Help system component for the EXASPERATION frontend."""

import streamlit as st
from typing import Dict, List, Any, Optional


def help_system():
    """Render the help system in the sidebar."""
    with st.sidebar.expander("Help & Documentation", expanded=False):
        st.markdown("""
        ## How to Use EXASPERATION
        
        EXASPERATION is a search assistant for Exabeam documentation.
        
        ### Basic Search
        
        1. Enter your question in the search box
        2. Click "Search" or press Enter
        3. View the generated answer and sources
        
        ### Advanced Features
        
        - **Filters**: Use the sidebar to filter by document type, vendor, or product
        - **Examples**: Click on example questions for quick searches
        - **History**: View and reuse your previous searches from the sidebar
        - **Feedback**: Rate answers to help improve results
        
        ### Search Tips
        
        - Be specific in your questions
        - Include product names when asking about specific integrations
        - Mention "rule", "parser", or "use case" when looking for specific content types
        - For MITRE ATT&CK related queries, include the technique ID if known
        """)
        
        st.markdown("---")
        
        st.markdown("""
        ### Keyboard Shortcuts
        
        - **Ctrl+Enter** - Submit search
        - **Esc** - Clear search input
        - **?** - Show this help
        """)


def show_tooltip(text: str, tooltip: str, icon: str = "ℹ️"):
    """Show a tooltip next to text.
    
    Args:
        text: Text to display
        tooltip: Tooltip content
        icon: Icon to display for the tooltip
    """
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.write(text)
    with col2:
        st.write(f"<span title='{tooltip}'>{icon}</span>", unsafe_allow_html=True)


def guided_tour():
    """Show a guided tour for new users."""
    if "show_tour" not in st.session_state:
        st.session_state.show_tour = False
        st.session_state.tour_step = 0
    
    # Tour steps content
    tour_steps = [
        {
            "title": "Welcome to EXASPERATION!",
            "content": "This tour will guide you through the main features. Click Next to continue.",
            "position": "center"
        },
        {
            "title": "Search Interface",
            "content": "Enter your questions about Exabeam documentation here.",
            "position": "bottom"
        },
        {
            "title": "Results Display",
            "content": "Your answers will appear here, with sources and citations.",
            "position": "bottom"
        },
        {
            "title": "Filtering Options",
            "content": "Use these filters to narrow down your search results.",
            "position": "left"
        },
        {
            "title": "History",
            "content": "Your search history is saved here for quick access.",
            "position": "left"
        },
        {
            "title": "Ready to Go!",
            "content": "You're all set. Start searching by entering a question.",
            "position": "center"
        }
    ]
    
    # Show tour toggle in the sidebar
    if st.sidebar.button("Start Guided Tour", key="start_tour"):
        st.session_state.show_tour = True
        st.session_state.tour_step = 0
    
    # Render current tour step if tour is active
    if st.session_state.show_tour:
        step = tour_steps[st.session_state.tour_step]
        
        with st.container():
            st.markdown(f"## {step['title']}")
            st.markdown(step['content'])
            
            col1, col2, col3 = st.columns([1, 1, 5])
            with col1:
                if st.button("Previous", key="tour_prev", disabled=st.session_state.tour_step == 0):
                    st.session_state.tour_step -= 1
                    st.rerun()
            with col2:
                if st.button("Next", key="tour_next"):
                    if st.session_state.tour_step < len(tour_steps) - 1:
                        st.session_state.tour_step += 1
                        st.rerun()
                    else:
                        st.session_state.show_tour = False
                        st.rerun()
            with col3:
                if st.button("Skip Tour", key="tour_skip"):
                    st.session_state.show_tour = False
                    st.rerun()


def faq_section():
    """Show frequently asked questions."""
    with st.expander("Frequently Asked Questions", expanded=False):
        st.markdown("""
        ### Frequently Asked Questions
        
        #### What type of questions can I ask?
        
        You can ask any question related to Exabeam documentation, including:
        - How specific features work
        - Details about data sources and parsers
        - Configuration instructions
        - Use case implementations
        - Troubleshooting steps
        
        #### How are the answers generated?
        
        Answers are generated using a Retrieval Augmented Generation (RAG) system:
        1. Your query is processed and expanded with relevant security terminology
        2. The system searches a database of Exabeam documentation
        3. Relevant documents are retrieved and ranked by relevance
        4. An AI model generates a concise answer based on these documents
        5. The system includes citations to help you verify the information
        
        #### How can I improve the results?
        
        - Be specific in your questions
        - Use proper terminology when possible
        - Provide context about what you're trying to achieve
        - Use the feedback buttons to indicate helpful or unhelpful answers
        - Try rephrasing your question if you don't get a satisfactory answer
        
        #### Are there usage limits?
        
        During this initial release, there are no strict usage limits. However, we recommend:
        - Focus on work-related queries about Exabeam documentation
        - Avoid submitting the same query multiple times in succession
        - Use the search history feature to revisit previous queries
        """)


# Create help content that can be inserted into the app
help_content = {
    "search_tips": """
    **Tips for effective searching:**
    - Be specific in your question
    - Include relevant keywords
    - Specify the product or vendor when applicable
    """,
    
    "filters_help": """
    **Using filters:**
    - Document Type: Select the type of content (use case, parser, etc.)
    - Vendor: Filter by technology vendor
    - Product: Filter by specific product
    - Date Range: Limit to documents created within a date range
    """,
    
    "results_help": """
    **Understanding results:**
    - The answer is generated based on the retrieved documents
    - Sources show the documents used to generate the answer
    - Relevance score indicates how closely the source matches your query
    """
}