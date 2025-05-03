import csv
import json
import sys

def csv_to_json(csv_file_path, json_file_path):
    """
    Convert CSV file to JSON format
    
    Args:
        csv_file_path (str): Path to the CSV file
        json_file_path (str): Path where JSON output will be saved
    """
    # List to store the data
    data = []
    
    # Read the CSV file
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
            # Create a CSV reader
            csv_reader = csv.DictReader(csv_file)
            
            # Convert each row to a dictionary and add to the data list
            for row in csv_reader:
                # Remove empty strings
                row_dict = {k: v for k, v in row.items() if k and k.strip()}
                data.append(row_dict)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return False
    
    # Write the data to a JSON file
    try:
        with open(json_file_path, mode='w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=2, ensure_ascii=False)
        print(f"Successfully converted {csv_file_path} to {json_file_path}")
        return True
    except Exception as e:
        print(f"Error writing JSON file: {e}")
        return False

if __name__ == "__main__":
    input_file = "data.csv"
    output_file = "data.json"
    
    # Allow command line arguments to specify input and output files
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    csv_to_json(input_file, output_file) 