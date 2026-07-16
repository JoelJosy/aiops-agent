# detector/test_api.py
from datetime import datetime, timezone, timedelta
from prometheus_api import fetch_metric

# 1. Target a 5-minute window relative to the current time
end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(minutes=5)

print(f"Querying Prometheus for range:")
print(f"    Start : {start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")
print(f"    End   : {end_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")
print(f"    Step  : 5s")
print("-" * 50)

# 2. Query the HTTP rate
query_str = 'rate(http_request_total[1m])'

try:
    df = fetch_metric(
        query=query_str,
        start=start_time,
        end=end_time,
        step="5s"
    )
    
    if df.empty:
        print("Warning: Returned DataFrame is empty. Make sure Locust is actively sending traffic!")
    else:
        print("Success! Prometheus metrics loaded into DataFrame.")
        print("-" * 50)
        
        # Display the structure info
        print(f"DataFrame Shape: {df.shape}")
        print("\nColumn Data Types:")
        print(df.dtypes)
        print("-" * 50)
        
        # Display first 10 rows
        print("\nPreviewing first few rows:")
        print(df.head(10))

        # Verification Checks (Filtered to a single series to get accurate step)
        sample_endpoint = "/items/{item_id}"
        filtered_df = df[df["endpoint"] == sample_endpoint]
        
        if not filtered_df.empty:
            time_diffs = filtered_df.index.to_series().diff().dropna()
            if not time_diffs.empty:
                avg_step = time_diffs.iloc[0].total_seconds()
                print("-" * 50)
                print(f"Time step validation (for {sample_endpoint}): Data points are spaced {avg_step}s apart.")
        else:
            # Fallback in case that endpoint didn't get hits yet
            time_diffs = df.index.to_series().drop_duplicates().diff().dropna()
            if not time_diffs.empty:
                avg_step = time_diffs.iloc[0].total_seconds()
                print("-" * 50)
                print(f"Time step validation (duplicates removed): Data points are spaced {avg_step}s apart.")
        
except Exception as e:
    print(f"Error fetching or processing data: {e}")