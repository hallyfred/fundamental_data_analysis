import os

def count_real_rows(json_data):
    """
    Dynamically identifies the number of records (real rows) in a JSON.
    Works for flat structures (Overview) and nested ones (Cash Flow, Income Statement).
    """
    if isinstance(json_data, list):
        return len(json_data)
    
    elif isinstance(json_data, dict):
        # Looks for lists inside the dictionary values (e.g., annualReports, quarterlyReports)
        internal_lists = [len(value) for value in json_data.values() if isinstance(value, list)]
        
        if internal_lists:
            # If it finds lists of reports, it sums the length of all of them
            return sum(internal_lists)
        else:
            # If there are no inner lists, it's a flat dictionary (1 company = 1 row)
            return 1
            
    return 0


