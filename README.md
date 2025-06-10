# AI Database Query Bot

A text-to-SQL service that converts natural language questions about financial data into SQL queries, executes them, and returns the results.

## Features

- Text-to-SQL conversion using LLM
- SQL validation and safety checks
- Conversation history with MongoDB
- Observability with trace IDs
- API Gateway for orchestration

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Configure environment variables in `.env` file:
   ```
   OPENAI_API_KEY=your_api_key
   OPENAI_MODEL=gpt-4o-mini
   DB_URL=postgresql://user:password@host:port/dbname
   ```

## Running the Service

Start the FastAPI server:

```
cd aibot
python run.py
```

The API will be available at http://localhost:8080

## API Endpoints

- `POST /v1/ai/query` - Process a natural language query
- `POST /v1/conversation/create` - Create a new conversation
- `GET /v1/conversation/{conversation_id}` - Get conversation history

## Example Usage

```python
import requests

# Create a conversation
response = requests.post(
    "http://localhost:8080/v1/conversation/create",
    json={"user_id": "user123"}
)
conversation_id = response.json()["conversation_id"]

# Process a query
response = requests.post(
    "http://localhost:8080/v1/ai/query",
    json={
        "query": "What was our revenue in Q1 2023?",
        "conversation_id": conversation_id,
        "user_id": "user123"
    }
)

# Print the results
results = response.json()
print(f"SQL Query: {results['sql']}")
print(f"Results: {results['results']}")
```

## Project Structure

- `config/` - Configuration and settings
- `core/` - Core application logic
  - `ai/` - AI services (text-to-SQL)
  - `db/` - Database connectors
  - `mongodb/` - Conversation storage
- `api/` - API endpoints and gateway
- `utils/` - Utility functions
- `schema_data/` - Database schema information

