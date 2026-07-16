import pandas as pd
import numpy as np

# Define metric-specific configurations to handle different behaviors
METRIC_CONFIGS = {
    "request_rate": {"window": 12, "threshold": 3.5},
    "app_p95_latency_seconds": {"window": 8, "threshold": 4.0},  # Jittery, higher threshold
    "app_error_rate": {"window": 6, "threshold": 3.0},           # Fast reaction
    "redis_average_latency_seconds": {"window": 8, "threshold": 3.5},
    "cache_error_rate": {"window": 6, "threshold": 3.0},
    "downstream_average_latency_seconds": {"window": 8, "threshold": 3.5},
    "downstream_error_rate": {"window": 6, "threshold": 3.0},
    "process_cpu_rate": {"window": 10, "threshold": 3.5},
    "process_resident_memory_bytes": {"window": 20, "threshold": 2.5}, # Slow accumulation, tight threshold
}

class MADDetector:
    def __init__(self, configs=METRIC_CONFIGS, persistence_steps=3):
        self.configs = configs
        self.persistence_steps = persistence_steps

    def fit_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes streaming telemetry data by isolating calculations within sessions.
        """
        # Create a deep copy to protect the original data
        df_clean = df.copy()
        
        # memory and CPU can never be 0. 
        # Replace these artifact zeros with NaN so they inherit the last known true state.
        systemic_metrics = ["process_resident_memory_bytes", "process_cpu_rate", "app_p95_latency_seconds"]
        for metric in systemic_metrics:
            if metric in df_clean.columns:
                df_clean[metric] = df_clean[metric].replace(0, np.nan)
        
        # Smoothly interpolate and fill gaps across the timeline
        df_clean = df_clean.interpolate(method="linear").ffill().bfill()
        
        if "session_id" not in df_clean.columns:
            df_clean["session_id"] = 0

        output_df = pd.DataFrame(index=df.index)
        
        # Handle the special availability override immediately
        if "app_availability" in df_clean.columns:
            output_df["app_availability_anomaly"] = (df_clean["app_availability"] < 1.0).astype(int)
            output_df["app_availability_score"] = output_df["app_availability_anomaly"] * 10.0

        # Process each metric individually according to its configuration
        for metric, cfg in self.configs.items():
            if metric not in df_clean.columns:
                continue
                
            w = cfg["window"]
            t = cfg["threshold"]
            
            # SESSION ISOLATED ROLLING CALCULATIONS
            # Grouping by session_id prevents windows from crossing overnight/idle gaps
            grouped = df_clean.groupby("session_id")[metric]
            
            # Rolling Median
            rolling_median = grouped.rolling(window=w, min_periods=2).median().reset_index(level=0, drop=True)
            
            # Absolute Deviations
            deviations = (df_clean[metric] - rolling_median).abs()
            
            # Rolling MAD (Median of Absolute Deviations)
            rolling_mad = deviations.groupby(df_clean["session_id"]).rolling(window=w, min_periods=2).median().reset_index(level=0, drop=True)
            
            # Compute Anomaly Score (Modified Z-score)
            safe_mad = rolling_mad.replace(0, 1e-9)
            scores = 0.6745 * deviations / safe_mad
            
            # Raw Alerts (Instantly exceeding threshold)
            raw_alerts = scores > t
            
            # Apply Persistence Safeguard (Must be True for 2–3 consecutive samples)
            # rolling.sum() == persistence_steps verifies the alert is sustained
            persistent_alerts = (raw_alerts.astype(int)
                                 .groupby(df_clean["session_id"])
                                 .rolling(window=self.persistence_steps)
                                 .sum()
                                 .reset_index(level=0, drop=True) == self.persistence_steps).astype(int)

            output_df[f"{metric}_score"] = scores
            output_df[f"{metric}_anomaly"] = persistent_alerts

        return output_df