# detector/dataset.py
import pandas as pd
from datetime import datetime, timezone
from typing import Union
from prometheus_api import fetch_metric
from metric_queries import QUERIES


def fetch_feature_table(start: Union[datetime, str], end: Union[datetime, str], step: str = "5s") -> pd.DataFrame:
    """
    Queries all aggregated metrics from Prometheus and aligns them 
    by timestamp into a single feature DataFrame.
    """
    feature_dfs = []

    for feature_name, query in QUERIES.items():
        try:
            # Fetch raw multi-series DataFrame
            raw_df = fetch_metric(query, start, end, step=step)
            
            # If empty, initialize a blank Series 
            if raw_df.empty:
                series = pd.Series(name=feature_name, dtype="float64")
            else:
                # Group by timestamp to ensure single series, selecting only the value
                series = raw_df["value"].groupby(level=0).first().rename(feature_name)
                
            feature_dfs.append(series)
            
        except Exception as e:
            print(f"Failed to fetch feature '{feature_name}': {e}")
            # Append empty placeholder series to keep index alignment
            feature_dfs.append(pd.Series(name=feature_name, dtype="float64"))

    if not feature_dfs:
        return pd.DataFrame()

    # Outer join merges them all on their shared timestamp indexes
    # Using outer join ensures gaps (like app-outages) preserve NaN structures properly
    wide_df = pd.concat(feature_dfs, axis=1)
    wide_df.index.name = "timestamp"
    
    return wide_df