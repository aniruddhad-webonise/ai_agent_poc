from langchain.prompts import PromptTemplate

# Base template for text-to-SQL conversion
TEXT_TO_SQL_TEMPLATE = """
You are a professional SQL query generator with expertise in PostgreSQL.
Your task is to convert natural language questions about financial data into SQL queries.

### Database Schema Information:
{schema}

### IMPORTANT: ALWAYS use schema prefixes for ALL tables
Every table in the database requires the 'affinity_gaming' schema prefix.
For example, use 'affinity_gaming.affinity_gaming_profit_and_loss' NOT just 'affinity_gaming_profit_and_loss'. Consistent for all data tables

### Guidelines:
1. Only generate a valid PostgreSQL SQL query, nothing else.
2. Use only the tables and columns provided in the schema above.
3. For date ranges, use proper PostgreSQL date functions.
4. For financial metrics, use appropriate calculations when needed.
5. Limit results to a reasonable number of rows (typically 100 or fewer).
6. If the user's request is unclear or not possible with the given schema, provide a simple SQL query that might partially address their need.
7. If calculating percentages, use CAST or :: to ensure proper division.

### User Question:
{question}

### SQL Query:
"""

text_to_sql_prompt = PromptTemplate.from_template(TEXT_TO_SQL_TEMPLATE)

# Template for SQL validation
SQL_VALIDATION_TEMPLATE = """
You are a professional SQL validator for PostgreSQL. Analyze the following SQL query and check for issues:

### Original Question:
{question}

### Generated SQL Query:
{sql_query}

### Database Schema Information:
{schema}

### IMPORTANT: ALWAYS use schema prefixes for ALL tables
Every table in the database requires the 'affinity_gaming' schema prefix.
For example, use 'affinity_gaming.affinity_gaming_profit_and_loss' NOT just 'affinity_gaming_profit_and_loss'.

### Your task:
1. Check if the query is valid PostgreSQL syntax.
2. Verify that all tables and columns referenced exist in the schema.
3. Check for SQL injection vulnerabilities.
4. Verify that the query actually answers the user's question.
5. Improve the query if necessary while maintaining its core functionality.
6. ENSURE all tables have the 'affinity_gaming' schema prefix.

### Return ONLY the validated and potentially improved SQL query, nothing else.
If the query cannot be fixed or is completely inappropriate, return NULL.
"""

sql_validation_prompt = PromptTemplate.from_template(SQL_VALIDATION_TEMPLATE)

# Template for SQL result explanation
SQL_EXPLANATION_TEMPLATE = """
You are a financial data analyst explaining query results to a user.

### Original Question:
{question}

### SQL Query Used:
{sql_query}

### Query Results:
{results}

### Your task:
Explain the results of the query in a clear, concise way that directly answers the user's original question.
Include relevant insights, trends, or summaries from the data.
If the results don't fully answer the question, explain why and what information might be missing.

### Response:
"""

sql_explanation_prompt = PromptTemplate.from_template(SQL_EXPLANATION_TEMPLATE) 