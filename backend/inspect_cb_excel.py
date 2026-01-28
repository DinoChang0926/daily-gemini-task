import requests
import pandas as pd
import urllib3
import io

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://cbas16889.pscnet.com.tw/api/MiDownloadExcel/GetExcel_IssuedCB"
try:
    print(f"Downloading from {url}...")
    resp = requests.get(url, verify=False, timeout=30)
    if resp.status_code == 200:
        print("Download success. Parsing Excel...")
        try:
            # Load into pandas to see columns
            df = pd.read_excel(io.BytesIO(resp.content))
            # print("Columns:", df.columns.tolist())
            for col in df.columns:
                print(f"Col: {col}")
            # print("First 5 rows:")
            # print(df.head().to_string())
        except Exception as e:
            print(f"Error parsing Excel: {e}")
    else:
        print(f"Failed to download. Status code: {resp.status_code}")
except Exception as e:
    print(f"Error executing request: {e}")
