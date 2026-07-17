from datetime import datetime, timezone, timedelta
from prometheus_api import fetch_feature_table

end_time = datetime.now(timezone.utc)
start_time = end_time - timedelta(minutes=10)

print(f"Building feature table for past 10 minutes...")
print(f"   Time range: {start_time.isoformat()} -> {end_time.isoformat()}\n")

df = fetch_feature_table(start_time, end_time, step="5s")

print("=" * 60)
print(f"Feature Table Successfully Generated!")
print(f"DataFrame Shape: {df.shape}")
print("=" * 60)

print("\nColumns in Wide Table:")
for col in df.columns:
    print(f" - {col}")

print("\nMissing-Value Count per Column (NaNs):")
print(df.isna().sum())

print("\nPreview (First 5 Rows):")
print(df.head(5))