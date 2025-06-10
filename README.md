# AI Database Query Bot

A text-to-SQL service that converts natural language questions about financial data into SQL queries, executes them, and returns the results.

## Features

- Text-to-SQL conversion using LLM
- SQL validation and safety checks
- Conversation history with MongoDB
- Observability with trace IDs
- API Gateway for orchestration
- LangGraph-based state management
- Follow-up question handling with contextualizer

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
- `GET /v1/conversation/{thread_id}` - Get conversation history

## Example Usage

```python
import requests

# Create a conversation
response = requests.post(
    "http://localhost:8080/v1/conversation/create",
    json={"user_id": "user123"}
)
thread_id = response.json()["thread_id"]

# Process a query
response = requests.post(
    "http://localhost:8080/v1/ai/query",
    json={
        "query": "What was our revenue in Q1 2023?",
        "thread_id": thread_id,
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
  - `state/` - State management
- `api/` - API endpoints and gateway
- `utils/` - Utility functions
- `schema_data/` - Database schema information

## Detailed Architecture

### Application Flow

The application follows a structured pipeline approach:

1. **HTTP Request** → `api/routes.py` receives the request with a natural language query
2. **Gateway Orchestration** → `api/enhanced_gateway.py` orchestrates the entire workflow
3. **State Management** → `core/state/state_manager.py` manages conversation state
4. **Query Contextualization** → `core/ai/contextualizer.py` handles follow-up questions
5. **Text-to-SQL Conversion** → `core/ai/text_to_sql.py` generates SQL from natural language
6. **SQL Validation** → `core/ai/sql_validator.py` validates the SQL for safety
7. **SQL Execution** → `core/db/query_executor.py` executes the SQL and returns results
8. **Response Formatting** → The gateway formats the response and returns it to the client

### Key Components and Interactions

#### 1. FastAPI Application (`app.py`)

- Initializes the FastAPI application
- Configures middleware, CORS, and error handling
- Mounts API routes from `api/routes.py`

#### 2. API Routes (`api/routes.py`)

- Defines API endpoints using FastAPI
- `QueryRequest` model processes incoming requests
- `QueryResponse` model structures responses
- Routes requests to the appropriate gateway methods

#### 3. Enhanced AI Gateway (`api/enhanced_gateway.py`)

- `EnhancedAIGateway` class orchestrates the entire workflow
- `process_query(query, thread_id, user_id)` → Main entry point for query processing
- `_generate_sql(state, contextualized_query)` → Generates SQL from natural language
- `_validate_sql(state)` → Validates SQL for safety
- `_execute_sql(state)` → Executes SQL query and processes results

#### 4. State Management (`core/state/state_manager.py`)

- `StateManager` class manages conversation state using LangGraph
- `State` schema defines the structure of the conversation state
- `Message` class represents conversation messages
- `get_state(thread_id)` → Retrieves state for a conversation
- `save_state(thread_id, state)` → Saves state and syncs with MongoDB
- `create_initial_state(query, thread_id, user_id)` → Creates a new conversation state

#### 5. Query Contextualizer (`core/ai/contextualizer.py`)

- `QueryContextualizer` class handles follow-up questions
- `contextualize(state)` → Rewrites ambiguous queries using conversation history
- Uses LangChain with OpenAI to understand context

#### 6. Text-to-SQL Service (`core/ai/text_to_sql.py`)

- `TextToSQLService` class converts natural language to SQL
- `generate_sql(question)` → Main method for SQL generation
- `_extract_sql_from_response(response)` → Extracts SQL from LLM responses
- `_add_schema_prefixes(sql)` → Adds schema prefixes to table names
- `_validate_sql(question, sql_query)` → Secondary validation of SQL

#### 7. SQL Validator (`core/ai/sql_validator.py`)

- `SQLValidator` class validates SQL for safety and correctness
- `validate(sql)` → Checks SQL syntax and potential SQL injection

#### 8. Query Executor (`core/db/query_executor.py`)

- `QueryExecutor` class executes SQL safely against the database
- `execute_sql_safely(sql)` → Executes SQL with safety measures
- `_connect_to_db()` → Manages database connections

#### 9. Conversation Store (`core/mongodb/conversation_store.py`)

- `ConversationStore` class manages conversation persistence in MongoDB
- `create_conversation(user_id)` → Creates a new conversation
- `add_message(conversation_id, role, content, metadata)` → Adds a message to conversation
- `get_conversation(conversation_id)` → Retrieves conversation history

### Data Flow for a Typical Query

1. **User Query**:
   - Request comes in to `/v1/ai/query` endpoint in `routes.py`
   - Request is validated against `QueryRequest` model
   - Query is passed to `enhanced_ai_gateway.process_query()`

2. **State Initialization**:
   - Gateway calls `state_manager.get_or_create_state()`
   - If a thread_id is provided, existing state is retrieved
   - If no thread_id or no state is found, a new state is created
   - User message is added to the conversation history

3. **Query Contextualization**:
   - Gateway calls `contextualizer.contextualize(state)`
   - If this is a follow-up question, it's rewritten using conversation history
   - Contextualized query is added to the state

4. **SQL Generation**:
   - Gateway calls `text_to_sql_service.generate_sql(contextualized_query)`
   - LangChain prompt is constructed with the database schema and query
   - OpenAI model generates SQL, which is extracted and processed
   - Generated SQL is added to the state

5. **SQL Validation**:
   - Gateway calls `sql_validator.validate(sql)`
   - SQL is checked for syntax errors and injection vulnerabilities
   - Validated SQL is added to the state

6. **SQL Execution**:
   - Gateway calls `query_executor.execute_sql_safely(sql)`
   - Connection is established with the PostgreSQL database
   - SQL is executed with safety parameters
   - Results are added to the state
   - Assistant message with results is added to conversation history

7. **Response Formatting**:
   - Gateway formats the response using `_format_success_response(state)`
   - Final state is saved to MongoDB via `state_manager.save_state()`
   - Response is returned to the client

### Error Handling

Each step has robust error handling:

1. If an error occurs during any step, an error message is added to the state
2. The error is logged using the structured logging system
3. The state is updated with the error information
4. An assistant message with the error is added to the conversation
5. The state is saved to MongoDB with the error information
6. An error response is returned to the client

### Async Implementation

The application uses async/await patterns:

1. API endpoints are defined as `async` functions
2. The gateway methods use `async` and `await`
3. Non-async operations (like database queries) are wrapped with `asyncio.run_in_executor()`
4. This ensures the application remains responsive under load

## Advanced Features

### Follow-up Questions

The system supports follow-up questions by:
1. Tracking conversation in the state manager
2. Using the contextualizer to rewrite ambiguous queries
3. Maintaining thread_id across multiple requests

### Schema Awareness

The system is aware of the database schema:
1. Schema is loaded from files in `schema_data/`
2. SQL generation includes schema context
3. Table references are automatically prefixed with schemas

