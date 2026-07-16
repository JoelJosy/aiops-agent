import pandas as pd
import numpy as np

METRIC_CONFIGS = {
    "request_rate": {"alpha": 0.3, "threshold": 3.5},
    "app_p95_latency_seconds": {"alpha": 0.2, "threshold": 4.0}, # Lower alpha handles jitter
    "app_error_rate": {"alpha": 0.4, "threshold": 3.0},
    "redis_average_latency_seconds": {"alpha": 0.3, "threshold": 3.5},
    "cache_error_rate": {"alpha": 0.4, "threshold": 3.0},
    "downstream_average_latency_seconds": {"alpha": 0.3, "threshold": 3.5},
    "downstream_error_rate": {"alpha": 0.4, "threshold": 3.0},
    "process_cpu_rate": {"alpha": 0.3, "threshold": 3.5},
    "process_resident_memory_bytes": {"alpha": 0.1, "threshold": 2.5}, # Tight alpha captures slow drift
}

class ForecastResidualDetector:
    def __init__(self, configs=METRIC_CONFIGS, persistence_steps=3):
        self.configs = configs
        self.persistence_steps = persistence_steps

    def _exponential_smoothing(self, series: pd.Series, alpha: float) -> pd.Series:
        """Calculates the predicted value stream using single exponential smoothing."""
        forecast = np.zeros_like(series)
        if len(series) == 0:
            return pd.Series(forecast, index=series.index)
            
        forecast[0] = series.iloc[0] # Initial seed
        for t in range(1, len(series)):
            forecast[t] = alpha * series.iloc[t-1] + (1 - alpha) * forecast[t-1]
        return pd.Series(forecast, index=series.index)

    def fit_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        df_clean = df.copy()
        
        # Infrastructure Zero-Dropout Patch
        systemic_metrics = ["process_resident_memory_bytes", "process_cpu_rate", "app_p95_latency_seconds"]
        for metric in systemic_metrics:
            if metric in df_clean.columns:
                df_clean[metric] = df_clean[metric].replace(0, np.nan)
        df_clean = df_clean.interpolate(method="linear").ffill().bfill()
        
        if "session_id" not in df_clean.columns:
            df_clean["session_id"] = 0

        output_df = pd.DataFrame(index=df.index)
        
        # Availability Override Layer
        if "app_availability" in df_clean.columns:
            output_df["app_availability_anomaly"] = (df_clean["app_availability"] < 1.0).astype(int)

        for metric, cfg in self.configs.items():
            if metric not in df_clean.columns:
                continue
                
            alpha = cfg["alpha"]
            t = cfg["threshold"]
            
            # 1. Compute Forecasts isolated inside sessions
            forecasts = df_clean.groupby("session_id")[metric].apply(
                lambda x: self._exponential_smoothing(x, alpha)
            ).reset_index(level=0, drop=True)
            
            # 2. Calculate the Absolute Residuals (Prediction Errors)
            residuals = (df_clean[metric] - forecasts).abs()
            
            # 3. Apply Rolling MAD to the Residuals (using a fixed evaluation window of 12 steps)
            grouped_res = residuals.groupby(df_clean["session_id"])
            rolling_median_res = grouped_res.rolling(window=12, min_periods=2).median().reset_index(level=0, drop=True)
            dev_from_med_res = (residuals - rolling_median_res).abs()
            rolling_mad_res = dev_from_med_res.groupby(df_clean["session_id"]).rolling(window=12, min_periods=2).median().reset_index(level=0, drop=True)
            
            # 4. Compute Anomaly Score on the Error
            safe_mad = rolling_mad_res.replace(0, 1e-9)
            scores = 0.6745 * dev_from_med_res / safe_mad
            
            raw_alerts = scores > t
            
            # 5. Persistence Filter
            persistent_alerts = (raw_alerts.astype(int)
                                 .groupby(df_clean["session_id"])
                                 .rolling(window=self.persistence_steps)
                                 .sum()
                                 .reset_index(level=0, drop=True) == self.persistence_steps).astype(int)

            output_df[f"{metric}_score"] = scores
            output_df[f"{metric}_anomaly"] = persistent_alerts

        return output_df