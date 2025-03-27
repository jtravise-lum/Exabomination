"""Main Streamlit application for Exabomination."""

import streamlit as st
from typing import Dict, Any

# Import components
from frontend.components.search_interface import search_interface, query_history_sidebar
from frontend.components.results_display import results_display
from frontend.components.filters_panel import filters_panel

# Import API client
from frontend.utils.api_client import api_client
from frontend.api.models import SearchFilters, SearchOptions, ErrorResponse

# Import configuration
from frontend.config import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_THRESHOLD,
    DEFAULT_INCLUDE_METADATA,
    DEFAULT_RERANK,
    THEME_PRIMARY_COLOR
)

# Set page config
st.set_page_config(
    page_title="Exabomination - Exabeam Documentation Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
st.markdown(f"""
<style>
    .stApp {{color: #333333;}}
    .stButton button {{background-color: {THEME_PRIMARY_COLOR}; color: white;}}
    a {{color: {THEME_PRIMARY_COLOR};}}
    .stProgress .st-bo {{background-color: {THEME_PRIMARY_COLOR};}}
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "search_error" not in st.session_state:
        st.session_state.search_error = None
    if "loading" not in st.session_state:
        st.session_state.loading = False
    if "metadata_options" not in st.session_state:
        st.session_state.metadata_options = None
    if "current_query" not in st.session_state:
        st.session_state.current_query = ""

# Initialize session state
init_session_state()

# Define a cached search function outside of any class
@st.cache_data(ttl=300)  # Cache for 5 minutes
def cached_search(query: str, filters_json: str, options_json: str, api_url: str, headers_dict: Dict):
    """Perform search with caching.
    
    Args:
        query: Search query
        filters_json: JSON string of filters
        options_json: JSON string of options
        api_url: API URL
        headers_dict: Headers dictionary
        
    Returns:
        Search response or error
    """
    try:
        # Parse JSON strings back to objects if provided
        filters = None if not filters_json else SearchFilters.model_validate_json(filters_json)
        options = None if not options_json else SearchOptions.model_validate_json(options_json)
        
        # Create request
        search_request = SearchRequest(
            query=query,
            filters=filters,
            options=options
        )
        
        # Make API call
        client = httpx.Client(timeout=30)
        response = client.post(
            api_url, 
            headers=headers_dict,
            content=search_request.model_dump_json()
        )
        
        if response.status_code == 200:
            return SearchResponse.model_validate(response.json())
        else:
            return ErrorResponse.model_validate(response.json())
    except Exception as e:
        # Create error response
        return ErrorResponse(
            error={
                "code": "connection_error",
                "message": f"Failed to connect to API: {str(e)}",
                "details": {"reason": "network_error"}
            },
            request_id=f"local_{int(time.time())}"
        )

# Define search function
def perform_search(query: str, filters: Dict[str, Any]):
    """Perform search using the API client.
    
    Args:
        query: The search query
        filters: Search filters
    """
    # Set loading state
    st.session_state.loading = True
    st.session_state.search_error = None
    
    # Show a debug message at the top
    debug_container = st.empty()
    debug_container.info(f"Searching for: {query}")
    
    # Convert filters dict to SearchFilters object and serialize to JSON
    search_filters = SearchFilters(**filters) if filters else None
    filters_json = "" if search_filters is None else search_filters.model_dump_json()
    
    # Create search options and serialize to JSON
    search_options = SearchOptions(
        max_results=DEFAULT_MAX_RESULTS,
        include_metadata=DEFAULT_INCLUDE_METADATA,
        rerank=DEFAULT_RERANK,
        threshold=DEFAULT_THRESHOLD
    )
    options_json = search_options.model_dump_json()
    
    try:
        # Make API call using cached function
        api_url = f"{api_client.base_url}/search"
        debug_container.info(f"Calling API at: {api_url}")
        
        # Try a direct API call first for debugging
        try:
            search_request = SearchRequest(
                query=query,
                filters=search_filters,
                options=search_options
            )
            direct_client = httpx.Client(timeout=30)
            direct_response = direct_client.post(
                api_url, 
                headers=api_client.headers,
                content=search_request.model_dump_json()
            )
            debug_container.info(f"Direct API call status: {direct_response.status_code}")
            
            # If successful, try to parse the response manually for debugging
            if direct_response.status_code == 200:
                try:
                    response_data = direct_response.json()
                    # Check a few key fields
                    debug_container.info(f"Response has {len(response_data.get('sources', []))} sources")
                    for i, source in enumerate(response_data.get('sources', [])[:3]):
                        debug_container.info(f"Source {i} chunk_id: {source.get('chunk_id')} (type: {type(source.get('chunk_id')).__name__})")
                except Exception as parse_err:
                    debug_container.warning(f"Failed to parse response: {str(parse_err)}")
        except Exception as direct_err:
            debug_container.warning(f"Direct API call failed: {str(direct_err)}")
            
            # If in development mode, create mock response
            if dev_mode:
                debug_container.info("Using mock data in development mode")
                import uuid
                from datetime import datetime
                
                # Create mock search response
                st.session_state.search_results = SearchResponse(
                    request_id=f"mock_{uuid.uuid4().hex[:12]}",
                    query=query,
                    answer=f"This is a mock answer for development purposes. The API is not available or couldn't be connected to. Your query was: **{query}**",
                    sources=[
                        SourceDocument(
                            id="mock_doc_1",
                            title="Mock Documentation",
                            url="https://docs.exabomination.com/example",
                            chunk_id="mock_1",
                            content="This is simulated content for the mock response. It contains information related to your query about " + query,
                            relevance_score=0.95,
                            metadata=DocumentMetadata(
                                document_type="use_case",
                                vendor="microsoft",
                                product="active_directory",
                                created_at=datetime.now().isoformat(),
                                updated_at=datetime.now().isoformat()
                            )
                        ),
                        SourceDocument(
                            id="mock_doc_2",
                            title="Additional Documentation",
                            url="https://docs.exabomination.com/related",
                            chunk_id="mock_2",
                            content="This is additional mock content related to " + query,
                            relevance_score=0.82,
                            metadata=DocumentMetadata(
                                document_type="tutorial",
                                vendor="cisco",
                                product="asa",
                                created_at=datetime.now().isoformat(),
                                updated_at=datetime.now().isoformat()
                            )
                        )
                    ],
                    suggested_queries=[
                        f"How to configure {query}?",
                        f"What are the requirements for {query}?",
                        f"Tell me more about {query}"
                    ],
                    metadata=SearchMetadata(
                        processing_time_ms=125,
                        filter_count=len(filters) if filters else 0,
                        total_matches=2,
                        threshold_applied=DEFAULT_THRESHOLD
                    )
                )
                
                debug_container.success("Created mock response for development")
                return
        
        # If not in dev mode or direct API call was successful, use the cached function
        result = cached_search(query, filters_json, options_json, api_url, api_client.headers)
        
        # Check if result is an error
        if isinstance(result, ErrorResponse):
            st.session_state.search_error = result
            debug_container.error(f"Search error: {result.error}")
        else:
            st.session_state.search_results = result
            debug_container.success("Search successful!")
            
    except Exception as e:
        # Create an error response without importing locally
        st.session_state.search_error = ErrorResponse(
            error={
                "code": "internal_error",
                "message": f"An error occurred: {str(e)}",
                "details": {"reason": "exception"}
            },
            request_id="local_error"
        )
        debug_container.error(f"Exception during search: {str(e)}")
    finally:
        # Reset loading state
        st.session_state.loading = False
        # Remove debug messages after successful load
        debug_container.empty()

# Function to handle filter changes
def handle_filter_change(filters: SearchFilters):
    """Handle filter changes and re-run search if needed.
    
    Args:
        filters: Updated filters
    """
    # Only re-run search if we have a current query
    if st.session_state.current_query:
        perform_search(st.session_state.current_query, filters.model_dump())

# Display the query history in the sidebar
query_history_sidebar()

# Import needed models at the module level
from frontend.api.models import (
    MetadataOptionsResponse, 
    ErrorResponse,
    SearchResponse,
    SearchFilters,
    SearchOptions,
    SearchRequest
)
import httpx
import time

# Define a cached function outside of any class to fetch metadata options
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_metadata_options(api_url, headers_dict):
    """Fetch metadata options from API with caching.
    
    Args:
        api_url: Full API URL
        headers_dict: Headers dictionary
        
    Returns:
        Metadata options or None if error
    """
    try:
        client = httpx.Client(timeout=30)
        response = client.get(api_url, headers=headers_dict)
        
        if response.status_code == 200:
            return MetadataOptionsResponse.model_validate(response.json())
        return None
    except Exception as e:
        st.warning(f"Failed to fetch metadata options: {str(e)}")
        return None

# Display API connection debug info 
st.sidebar.write("### API Connection")
st.sidebar.write(f"API URL: {api_client.base_url}")

# Create an expandable section for detailed connection info
with st.sidebar.expander("Connection Details", expanded=True):
    # Get API URL config from environment
    import os
    from dotenv import load_dotenv
    load_dotenv(".env.frontend")
    
    env_api_url = os.getenv("EXABOMINATION_API_URL", "Not set")
    st.write(f"**Environment API URL:** {env_api_url}")
    
    # Test multiple possible API endpoints
    import socket
    import httpx
    from urllib.parse import urlparse
    
    def check_port_open(host, port):
        """Check if a port is open on a host."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    # Parse the current API URL
    parsed_url = urlparse(api_client.base_url)
    host = parsed_url.hostname or 'localhost'
    port = parsed_url.port or 8888
    
    # Check the configured port
    if check_port_open(host, port):
        st.success(f"✅ Port {port} is open on {host}")
    else:
        st.error(f"❌ Port {port} is not accessible on {host}")
    
    # Check other common ports
    other_ports = [8000, 8080, 5000, 3000]
    st.write("### Checking other common ports:")
    
    for test_port in other_ports:
        if check_port_open(host, test_port):
            st.success(f"✅ Port {test_port} is open on {host}")
        else:
            st.warning(f"❌ Port {test_port} is not accessible on {host}")
    
    # Try to list running processes with ports (Linux only)
    try:
        import subprocess
        st.write("### Running processes with network ports:")
        result = subprocess.run(
            ["netstat", "-tulpn"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            st.code(result.stdout)
        else:
            st.error(f"Failed to run netstat: {result.stderr}")
    except Exception as e:
        st.warning(f"Could not list running processes: {str(e)}")
    
    # Try connecting to health endpoints on different ports
    ports_to_try = [port] + other_ports
    for test_port in ports_to_try:
        health_url = f"http://{host}:{test_port}/health"
        st.write(f"Testing health endpoint: {health_url}")
        
        try:
            response = httpx.get(health_url, timeout=1)
            if response.status_code == 200:
                st.success(f"✅ Health endpoint accessible on port {test_port}!")
                st.json(response.json() if response.headers.get('content-type') == 'application/json' else response.text)
                
                # If this is not our configured port, suggest updating the config
                if test_port != port:
                    st.info(f"Consider updating EXABOMINATION_API_URL in .env.frontend to use port {test_port}")
            else:
                st.error(f"API returned error: {response.status_code}")
        except Exception as e:
            st.warning(f"Could not connect to {health_url}: {str(e)}")
    
# Add dev mode toggle for when API is not available
with st.sidebar:
    dev_mode = st.checkbox("Development Mode (Mock Data)", value=True)

# Display the filters panel
try:
    # Get metadata options from API if not already loaded
    if st.session_state.metadata_options is None:
        # Fetch metadata options from API using the cached function
        api_url = f"{api_client.base_url}/metadata/options"
        st.sidebar.write(f"Metadata URL: {api_url}")
        
        # Direct, non-cached call for debugging (don't show headers in UI)
        try:
            direct_response = httpx.get(api_url, headers=api_client.headers, timeout=5)
            st.sidebar.write(f"Direct metadata call status: {direct_response.status_code}")
            if direct_response.status_code == 200:
                st.sidebar.write("Direct call successful")
            else:
                st.sidebar.write(f"Direct response: {direct_response.text[:100]}...")
        except Exception as e:
            st.sidebar.error(f"Direct metadata call failed: {str(e)}")
            
            # If in dev mode and API is not available, create mock metadata
            if dev_mode:
                st.sidebar.info("Using mock metadata in development mode")
                st.session_state.metadata_options = MetadataOptionsResponse(
                    document_types=[
                        "use_case",
                        "parser",
                        "rule",
                        "data_source",
                        "overview",
                        "tutorial"
                    ],
                    vendors=[
                        "microsoft",
                        "cisco",
                        "okta",
                        "palo_alto",
                        "aws"
                    ],
                    products={
                        "microsoft": [
                            "active_directory",
                            "azure_ad",
                            "exchange_online",
                            "windows"
                        ],
                        "cisco": [
                            "asa",
                            "firepower",
                            "ise",
                            "meraki"
                        ],
                        "okta": [
                            "identity_cloud"
                        ]
                    },
                    use_cases=[
                        "account_takeover",
                        "data_exfiltration",
                        "lateral_movement",
                        "privilege_escalation"
                    ],
                    date_range={
                        "oldest": "2022-01-15",
                        "newest": "2025-03-27"
                    }
                )
        
        # Try cached call if no mock data was set
        if st.session_state.metadata_options is None:
            metadata_options = fetch_metadata_options(api_url, api_client.headers)
            if metadata_options:
                st.session_state.metadata_options = metadata_options
                st.sidebar.success("Metadata options loaded successfully")
            else:
                st.sidebar.warning("Failed to load metadata options from API")
                
                # If all attempts failed and we're in dev mode, use mock data
                if dev_mode and st.session_state.metadata_options is None:
                    st.sidebar.info("Using mock metadata in development mode")
                    st.session_state.metadata_options = MetadataOptionsResponse(
                        document_types=["use_case", "parser", "rule"],
                        vendors=["microsoft", "cisco"],
                        products={
                            "microsoft": ["active_directory", "windows"],
                            "cisco": ["asa", "firepower"]
                        },
                        use_cases=["account_takeover", "lateral_movement"],
                        date_range={"oldest": "2022-01-15", "newest": "2025-03-27"}
                    )
    
    # Use available metadata options 
    filters = filters_panel(handle_filter_change, st.session_state.metadata_options)
except Exception as e:
    st.sidebar.error(f"Could not load filters: {str(e)}")
    st.error(f"Error details: {str(e)}")

# Main app layout
st.write("")

# Display the search interface
current_query = search_interface(
    on_search=perform_search,
    loading=st.session_state.loading
)

# Display results or error
results_display(
    result=st.session_state.search_results,
    error=st.session_state.search_error
)