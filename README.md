# Ultravox: Documentation Crawler and RAG Agent

An intelligent documentation crawler and RAG (Retrieval-Augmented Generation) agent built using advanced AI technologies. The agent can crawl documentation websites, store content in a vector database, and provide intelligent answers to user questions by retrieving and analyzing relevant documentation chunks.

## Features

- Documentation website crawling and chunking
- Vector database storage
- Semantic search using AI embeddings
- RAG-based question answering
- Support for code block preservation
- Streamlit UI for interactive querying
- Available as both API endpoint and web interface

## Prerequisites

- Python 3.11+
- Required accounts and API keys
- Streamlit (for web interface)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/BollineniRohith123/Ultravox.git
cd Ultravox
```

2. Install dependencies (recommended to use a Python virtual environment):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
   - Rename `.env.example` to `.env`
   - Edit `.env` with your API keys and preferences

## Usage

### Crawl Documentation

To crawl and store documentation in the vector database:

```bash
python crawl_docs.py
```

### Streamlit Web Interface

For an interactive web interface to query the documentation:

```bash
streamlit run streamlit_ui.py
```

## Deployment

### Streamlit Cloud Deployment

1. **Supabase Setup**:
   - Create a new Supabase project
   - Enable vector similarity search
   - Create the `site_pages` table with the following schema:
     ```sql
     CREATE TABLE site_pages (
         id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
         url TEXT,
         chunk_number INTEGER,
         title TEXT,
         summary TEXT,
         content TEXT,
         metadata JSONB,
         embedding VECTOR(1536)
     );
     ```

2. **OpenAI API**:
   - Obtain an OpenAI API key from [OpenAI Platform](https://platform.openai.com/)

3. **Deployment Steps**:
   - Fork this repository
   - Go to [Streamlit Cloud](https://streamlit.io/cloud)
   - Click "Deploy an app"
   - Select your forked repository
   - Set the following secrets in Streamlit Cloud:
     * `OPENAI_API_KEY`
     * `SUPABASE_URL`
     * `SUPABASE_SERVICE_KEY`

### Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your API keys
4. Run: `streamlit run streamlit_ui.py`

### Troubleshooting

- Ensure Supabase URL is in format: `https://YOUR_PROJECT_ID.supabase.co`
- Verify API keys have correct permissions
- Check network connectivity and firewall settings

## Contributing

Contributions are welcome! Please read the contributing guidelines before getting started.

## License

[Specify your license here]
