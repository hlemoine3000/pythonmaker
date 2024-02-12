import ast
import re

def extract_single_function_name(code):
    # Parse the code into an AST
    parsed_code = ast.parse(code)
    
    # This class collects names of function definitions
    class FunctionNameCollector(ast.NodeVisitor):
        def __init__(self):
            self.function_names = []
            
        def visit_FunctionDef(self, node):
            self.function_names.append(node.name)
            self.generic_visit(node)
    
    # Create a collector and walk the AST to collect function names
    collector = FunctionNameCollector()
    collector.visit(parsed_code)
    
    # Check if there is exactly one function in the string
    if len(collector.function_names) == 1:
        return collector.function_names[0]
    else:
        return None  # Return None or raise an exception if the condition is not met

def extract_substring(s: str, start_marker: str, end_marker: str):
    start = s.find(start_marker) + len(start_marker)
    end = s.find(end_marker, start)
    if start >= len(start_marker) and end != -1:
        return s[start:end]
    else:
        return s