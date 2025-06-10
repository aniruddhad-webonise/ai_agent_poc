import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Set

from .settings import SCHEMA_DATA_DIR, SCHEMA_MAX_TABLES, SCHEMA_MAX_VIEWS

logger = logging.getLogger(__name__)

class SchemaLoader:
    """
    Loads and processes database schema information from CSV files.
    Transforms schema data into a format suitable for LLM context.
    """
    
    def __init__(self, tables_csv: Path = None, views_csv: Path = None):
        """
        Initialize the schema loader with paths to CSV files.
        
        Args:
            tables_csv: Path to tables CSV file
            views_csv: Path to views CSV file
        """
        self.tables_csv = tables_csv or SCHEMA_DATA_DIR / "tables.csv"
        self.views_csv = views_csv or SCHEMA_DATA_DIR / "views.csv"
        self.tables_json = SCHEMA_DATA_DIR / "tables.json"
        self.views_json = SCHEMA_DATA_DIR / "views.json"
        
    def load_and_process(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load schema data from CSV files and process it into a structured format.
        
        Args:
            force_reload: Whether to force reload from CSV even if JSON exists
            
        Returns:
            Dict containing structured schema information
        """
        if not force_reload and self.tables_json.exists() and self.views_json.exists():
            logger.info("Loading schema from cached JSON files")
            return self._load_from_json()
            
        logger.info("Processing schema from CSV files")
        tables_data = self._process_tables_csv()
        views_data = self._process_views_csv()
        
        schema = {
            "tables": tables_data,
            "views": views_data
        }
        
        # Save processed data to JSON for faster loading next time
        self._save_to_json(tables_data, views_data)
        
        return schema
    
    def _process_tables_csv(self) -> Dict[str, Dict[str, Any]]:
        """
        Process tables CSV file into a structured format.
        
        Returns:
            Dict mapping table names to their column information
        """
        tables: Dict[str, Dict[str, Any]] = {}
        
        try:
            with open(self.tables_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    table_name = row.get('table_name')
                    if not table_name:
                        continue
                        
                    if table_name not in tables:
                        tables[table_name] = {
                            "description": row.get('table_description', ''),
                            "columns": {}
                        }
                        
                    column_name = row.get('column_name')
                    if column_name:
                        tables[table_name]["columns"][column_name] = {
                            "data_type": row.get('data_type', 'unknown'),
                            "nullable": row.get('is_nullable', 'YES').upper() == 'YES',
                            "description": row.get('column_description', '')
                        }
        except Exception as e:
            logger.error(f"Error processing tables CSV: {e}")
            raise
            
        # Limit to the most important tables if there are too many
        if len(tables) > SCHEMA_MAX_TABLES:
            logger.warning(f"Limiting tables from {len(tables)} to {SCHEMA_MAX_TABLES}")
            tables = dict(list(tables.items())[:SCHEMA_MAX_TABLES])
            
        return tables
    
    def _process_views_csv(self) -> Dict[str, Dict[str, Any]]:
        """
        Process views CSV file into a structured format.
        
        Returns:
            Dict mapping view names to their column information
        """
        views: Dict[str, Dict[str, Any]] = {}
        
        try:
            with open(self.views_csv, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    view_name = row.get('view_name')
                    if not view_name:
                        continue
                        
                    if view_name not in views:
                        views[view_name] = {
                            "description": row.get('view_description', ''),
                            "columns": {}
                        }
                        
                    column_name = row.get('column_name')
                    if column_name:
                        views[view_name]["columns"][column_name] = {
                            "data_type": row.get('data_type', 'unknown')
                        }
        except Exception as e:
            logger.error(f"Error processing views CSV: {e}")
            raise
            
        # Limit to the most important views if there are too many
        if len(views) > SCHEMA_MAX_VIEWS:
            logger.warning(f"Limiting views from {len(views)} to {SCHEMA_MAX_VIEWS}")
            views = dict(list(views.items())[:SCHEMA_MAX_VIEWS])
            
        return views
    
    def _save_to_json(self, tables_data: Dict, views_data: Dict) -> None:
        """
        Save processed schema data to JSON files.
        
        Args:
            tables_data: Processed tables data
            views_data: Processed views data
        """
        try:
            SCHEMA_DATA_DIR.mkdir(exist_ok=True, parents=True)
            
            with open(self.tables_json, 'w') as f:
                json.dump(tables_data, f, indent=2)
                
            with open(self.views_json, 'w') as f:
                json.dump(views_data, f, indent=2)
                
            logger.info(f"Saved processed schema to {self.tables_json} and {self.views_json}")
        except Exception as e:
            logger.error(f"Error saving schema to JSON: {e}")
            raise
    
    def _load_from_json(self) -> Dict[str, Any]:
        """
        Load schema data from cached JSON files.
        
        Returns:
            Dict containing schema information
        """
        try:
            with open(self.tables_json, 'r') as f:
                tables_data = json.load(f)
                
            with open(self.views_json, 'r') as f:
                views_data = json.load(f)
                
            return {
                "tables": tables_data,
                "views": views_data
            }
        except Exception as e:
            logger.error(f"Error loading schema from JSON: {e}")
            # Fall back to processing from CSV
            return self.load_and_process(force_reload=True)
    
    def get_schema_for_llm(self) -> str:
        """
        Generate a text representation of the schema optimized for LLM context.
        
        Returns:
            String representation of the schema
        """
        schema = self.load_and_process()
        
        tables_text = []
        for table_name, table_info in schema["tables"].items():
            # Always use fully qualified table names with schema prefix
            qualified_table_name = f"affinity_gaming.{table_name}"
            table_desc = f"Table: {qualified_table_name}"
            if table_info.get("description"):
                table_desc += f" - {table_info['description']}"
            
            columns_text = []
            for col_name, col_info in table_info["columns"].items():
                col_desc = f"  - {col_name} ({col_info['data_type']})"
                if col_info.get("description"):
                    col_desc += f" - {col_info['description']}"
                columns_text.append(col_desc)
            
            table_text = table_desc + "\n" + "\n".join(columns_text)
            tables_text.append(table_text)
        
        views_text = []
        for view_name, view_info in schema["views"].items():
            # Always use fully qualified view names with schema prefix
            qualified_view_name = f"affinity_gaming.{view_name}"
            view_desc = f"View: {qualified_view_name}"
            if view_info.get("description"):
                view_desc += f" - {view_info['description']}"
            
            columns_text = []
            for col_name, col_info in view_info["columns"].items():
                col_desc = f"  - {col_name} ({col_info['data_type']})"
                columns_text.append(col_desc)
            
            view_text = view_desc + "\n" + "\n".join(columns_text)
            views_text.append(view_text)
        
        # Combine all text and add a note about schema prefixes
        all_text = (
            "IMPORTANT: ALL tables and views must be referenced with 'affinity_gaming' schema prefix.\n"
            "Example: 'affinity_gaming.table_name' NOT just 'table_name'\n\n"
            + "\n\n".join(tables_text + views_text)
        )
        
        return all_text


# Singleton instance
schema_loader = SchemaLoader() 