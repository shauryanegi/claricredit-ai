# Credit Memo RAG Application 📄🤖

A Retrieval-Augmented Generation (RAG) pipeline designed to streamline credit memo creation by extracting and processing financial data from PDF documents.

This application automates the process of parsing financial PDFs, chunking the extracted content, storing it as embeddings in a vector database (ChromaDB), and using a Large Language Model (LLM) to generate structured credit memo outputs.

## 🚀 Key Features

- **PDF Data Extraction**: Converts unstructured financial data from PDF files into clean Markdown.
- **Intelligent Chunking**: Splits the extracted text into semantically meaningful chunks.
- **Vector Embeddings**: Creates and stores vector representations of text chunks in a persistent ChromaDB database.
- **RAG Pipeline**: Retrieves relevant context from the vector DB to answer specific queries or generate full reports.
- **FastAPI Service**: Exposes the RAG pipeline via a simple and efficient REST API.

## ⚙️ Project Structure

Here's a breakdown of the key files and directories in this project:

```
.
├── resources/              # Core application logic and resources
│   ├── chunker.py          # Handles text chunking and embedding generation
│   ├── extractor.py        # Extracts text from PDFs and converts to Markdown
│   ├── pipeline.py         # Orchestrates the end-to-end RAG workflow
│   ├── rag.py              # Core RAG implementation (retrieval + generation)
│   └── prompts/            # Contains prompt templates for the LLM
├── app.py                  # FastAPI application entrypoint
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Dockerfile for building the application image
├── run.sh                  # Convenience script to start the API
├── requirements.txt        # Python dependencies
├── outputs/                # Default directory for extracted markdown and generated memos
└── chroma_db/              # Persistent storage for the Chroma vector database
```

## 📋 Getting Started

Follow these steps to set up and run the project locally.

### 1. Prerequisites

- Python 3.9+
- Docker and Docker Compose (for containerized deployment)

### 2. Installation

Clone the repository and install the required Python dependencies.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 🛠️ Usage

You can interact with the application either through the command line for direct processing or by running the FastAPI service.

### Method 1: Command-Line Interface

#### 1. Extract Content from a PDF

First, convert your target PDF into a Markdown file. This will be used as the source for the RAG pipeline.

```bash
python -m resources.extractor --pdf path/to/your/document.pdf
```

This command will save the extracted text to `outputs/document.md`.

#### 2. Run the RAG Pipeline from Markdown

Once you have the Markdown file, you can either generate a full credit memo or ask a specific question.

- **To generate a full credit memo:**

```bash
python -m resources.markdown_pipeline --md outputs/document.md --n_results 5
```

- **To query for a specific piece of information:**

```bash
python -m resources.markdown_pipeline --md outputs/document.md --query "What is the total assets?" --n_results 5
```

### Method 2: FastAPI Service

#### 1. Start the API Server

Use the provided shell script to launch the FastAPI application with Uvicorn.

```bash
./run.sh
```

The server will be running at `http://localhost:9999`.

#### 2. Access the API Docs

Navigate to `http://localhost:9999/docs` in your browser to access the interactive Swagger UI documentation, where you can test the API endpoints directly.

### Method 3: Docker Deployment 🐳

For a containerized setup, you can use the provided Docker files.

```bash
# Build and run the service using Docker Compose
docker-compose up --build
```

The service will be available at `http://localhost:9999`.
