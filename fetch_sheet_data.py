import pandas as pd
import requests
import io

spreadsheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRO2ZV-BOcL11_5NhlrOnn5Keph3-cVp7Tyr1t6RxsoDvxZjdOyDsmRkdvesJLbSnZwY8v3CATt1Of9/pub?gid=377625640&single=true&output=csv"

try:
    # Use requests to get data with proper headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(spreadsheet_url, headers=headers)
    response.raise_for_status()
    
    # Print raw content to see what we're dealing with
    print("Raw CSV Content (first 500 bytes):")
    print(response.content[:500])
    print("\n")
    
    # Load into pandas
    df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
    
    # Print column information
    print("DataFrame Shape:", df.shape)
    print("\nColumns in DataFrame:")
    for col in df.columns:
        print(f"  - {col}")
        
    print("\nFirst 5 rows:")
    print(df.head(5).to_string())
    
except Exception as e:
    print(f"Error: {str(e)}")