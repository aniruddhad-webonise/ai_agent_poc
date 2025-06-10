import logging
import time
import functools
from typing import Callable, Any
import inspect

logger = logging.getLogger(__name__)

def trace(operation_name: str = None):
    """
    Decorator for tracing function execution with timing.
    
    Args:
        operation_name: Name of the operation being traced
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get the function name if operation_name is not provided
            op_name = operation_name or func.__name__
            
            # Try to extract trace_id from args or kwargs
            trace_id = None
            
            # Check for trace_id in kwargs
            if 'trace_id' in kwargs:
                trace_id = kwargs['trace_id']
            
            # Check for trace_id in args by inspecting function signature
            if trace_id is None:
                try:
                    sig = inspect.signature(func)
                    param_names = list(sig.parameters.keys())
                    
                    # Skip self/cls for methods
                    if param_names and param_names[0] in ('self', 'cls'):
                        param_names = param_names[1:]
                    
                    # Look for trace_id parameter
                    if 'trace_id' in param_names and len(args) > param_names.index('trace_id'):
                        trace_id_idx = param_names.index('trace_id')
                        trace_id = args[trace_id_idx]
                except Exception:
                    pass
            
            # Start timing
            start_time = time.time()
            
            # Log operation start
            if trace_id:
                logger.info(f"Operation '{op_name}' started (trace_id: {trace_id})")
            else:
                logger.info(f"Operation '{op_name}' started")
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Log operation completion
                if trace_id:
                    logger.info(f"Operation '{op_name}' completed in {duration:.3f}s (trace_id: {trace_id})")
                else:
                    logger.info(f"Operation '{op_name}' completed in {duration:.3f}s")
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                
                # Log operation failure
                if trace_id:
                    logger.error(f"Operation '{op_name}' failed after {duration:.3f}s: {str(e)} (trace_id: {trace_id})")
                else:
                    logger.error(f"Operation '{op_name}' failed after {duration:.3f}s: {str(e)}")
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator