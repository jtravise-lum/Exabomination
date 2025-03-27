# EXASPERATION

**Exabeam Automated Search Assistant Preventing Exasperating Research And Time-wasting In Official Notes**

## Overview

EXASPERATION is a Retrieval Augmented Generation (RAG) system designed to make Exabeam's extensive documentation accessible and useful. By combining vector search technology with large language models, EXASPERATION allows users to ask natural language questions about Exabeam and receive accurate, contextual answers without needing to navigate through thousands of pages of documentation.

## The Problem

Exabeam's documentation, while comprehensive, can be challenging to navigate. With over 10,000 pages of content covering various data sources, parsers, correlation rules, and use cases, finding specific information can be time-consuming and frustrating. EXASPERATION transforms this "documentation wilderness" into a searchable knowledge base that responds to your queries directly.

## Features

- **Natural Language Queries**: Ask questions in plain English about Exabeam features, configurations, or troubleshooting
- **Contextual Understanding**: The system understands relationships between different parts of the documentation
- **Source Citations**: All responses include references to the original documentation
- **Low-latency Responses**: Get answers in seconds rather than hours of manual searching
- **Continuous Learning**: The system can be updated as new documentation is released

## Technical Architecture

EXASPERATION uses a modular architecture consisting of:

1. **Document Processing Pipeline**: Chunks Exabeam documentation and extracts metadata
2. **Vector Database**: Stores embeddings of document chunks for semantic search
3. **Retrieval Engine**: Finds the most relevant documentation segments for a given query
4. **LLM Integration**: Generates human-readable responses based on retrieved context
5. **API Layer**: FastAPI-based API for frontend communication
6. **Web Interface**: Streamlit-based user interface with search, filter, and feedback capabilities

## Getting Started

### Prerequisites

- Python 3.8+ (Python 3.10 or 3.11 recommended)
- 8GB+ RAM recommended
- 2GB disk space for vector database
- API keys for Voyage AI (embedding and reranking)
- Optional API keys for additional LLM services

### Installation

#### Component Architecture

EXASPERATION consists of two main components that can be run separately:

1. **ChromaDB Vector Database** - Runs in Docker
2. **Embedding and Query Pipeline** - Runs in Python virtual environment

This separation allows for more flexibility and better compatibility with different Python versions.

#### Option 1: Using Docker for ChromaDB (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/exasperation.git
cd exasperation

# Start ChromaDB with Docker
docker-compose up -d
```

#### Option 2: Setting up the Embedding Pipeline

```bash
# Create a dedicated virtual environment
python -m venv chromadb_venv
source chromadb_venv/bin/activate  # On Windows: chromadb_venv\Scripts\activate

# Copy example env file and configure
cp .env.example .env
# Edit .env to add your API keys

# Install minimal dependencies for embedding
pip install -r chromadb.requirements.txt

# Initialize the database (this will download and process documentation)
python -m src.initialize_db
```

For local ChromaDB installation (not recommended), set `use_server=False` when initializing the VectorDatabase class.

#### Important Notes

- The `chromadb.requirements.txt` file contains only the minimal dependencies needed for the embedding pipeline
- Docker Compose should be installed at the system level, not in the virtual environment
- The Python embedding pipeline is in a separate environment (chromadb_venv) from any web UI components
- Python 3.12+ may have compatibility issues with some packages - use Python 3.10-3.11 for best results

### Usage

#### Testing the Query Engine

```bash
# Test with default (mock) LLM
./test_query.py "What parsers are available for Windows Security events?"

# Test with Anthropic Claude
./test_query.py --provider anthropic --model claude-3-5-sonnet-20240620 "Explain the Audit Tampering use case"

# Test with OpenAI GPT
./test_query.py --provider openai --model gpt-4o "How does Exabeam detect lateral movement?"

# Using filters and adjusting parameters
./test_query.py --top-k 10 --temperature 0.3 "What MITRE ATT&CK techniques are covered by Exabeam?"
```

#### Running the Query Engine

After setting up the environment and initializing the database, you can use the query engine to test the system:

```bash
# Test with the mock LLM (no API key required)
./test_query.py --provider mock "What parsers are available for Windows Security events?"

# Test with Anthropic Claude (requires API key)
./test_query.py --provider anthropic "Explain the Audit Tampering use case"

# Test with OpenAI GPT (requires API key)
./test_query.py --provider openai "How does Exabeam detect lateral movement?"

# Adjust parameters
./test_query.py --top-k 10 --temperature 0.3 "What MITRE ATT&CK techniques are covered by Exabeam?"
```

#### Using the Web Interface

```bash
# Set up the frontend environment
./setup_frontend.sh

# Run the frontend application
./run_frontend.sh
```

Then open your browser to http://localhost:8501 to begin asking questions.

Make sure the API is running before starting the frontend:

```bash
# Run the API server
python -m frontend.api.main
```

The API runs on port 8888 by default.

## Example Queries

- "What parsers are available for 1Password?"
- "How does the Audit Tampering use case work with Microsoft products?"
- "Explain the T1070.001 MITRE technique and how Exabeam detects it"
- "What correlation rules are available for detecting lateral movement?"
- "How do I set up the integration with Cisco ACS?"

## Roadmap

- [x] Web interface for searching and viewing results
- [x] API layer for frontend-backend communication
- [x] User feedback mechanism for rating responses
- [ ] Add support for PDF documentation
- [ ] Enhanced analytics and usage tracking
- [ ] Create CLI interface for integration with scripts
- [ ] Add visualization for relationships between components
- [ ] Support for real-time documentation updates

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Exabeam team for creating such *thorough* documentation
- The open-source community for amazing tools that make this possible
- Everyone who has ever muttered "I know it's in the docs somewhere..." while searching frantically

---

**EXASPERATION**: *Because life's too short to read the manual... entirely.*
