import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import Dict, List
import numpy as np

class AIAnalyzer:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)

    def analyze_historical_delays(self, timing_data: pd.DataFrame) -> Dict:
        """Analyze historical timing patterns"""
        if timing_data.empty:
            return {"error": "No data available for analysis"}

        try:
            # Convert delays to numerical format
            delays = timing_data['delay'].values.reshape(-1, 1)
            
            # Train model and detect anomalies
            self.model.fit(delays)
            anomalies = self.model.predict(delays)
            
            # Calculate statistics
            avg_delay = np.mean(delays)
            max_delay = np.max(delays)
            min_delay = np.min(delays)
            anomaly_count = len(anomalies[anomalies == -1])
            
            return {
                "average_delay": round(float(avg_delay), 2),
                "max_delay": round(float(max_delay), 2),
                "min_delay": round(float(min_delay), 2),
                "anomaly_count": anomaly_count,
                "total_records": len(delays),
                "reliability_score": round((1 - anomaly_count/len(delays)) * 100, 2)
            }
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def get_delay_prediction(self, historical_data: pd.DataFrame, station: str) -> Dict:
        """Predict potential delays for a station"""
        station_data = historical_data[historical_data['station'] == station]
        if len(station_data) < 5:
            return {"prediction": "Insufficient data for prediction"}

        delays = station_data['delay'].values
        avg_delay = np.mean(delays)
        std_delay = np.std(delays)
        
        return {
            "station": station,
            "predicted_delay": round(float(avg_delay), 2),
            "confidence": round(100 / (1 + std_delay), 2)
        }
