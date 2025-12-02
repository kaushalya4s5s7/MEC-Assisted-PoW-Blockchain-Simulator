"""
Metrics collection and tracking module.
"""

import logging
from typing import Dict, List
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and manages simulation metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = []
        self.summary = {}

    def record(self, metric: Dict):
        """
        Record a metric snapshot.

        Args:
            metric: Dictionary of metric values
        """
        self.metrics.append(metric.copy())

    def get_summary(self) -> Dict:
        """
        Get summary statistics.

        Returns:
            Summary dictionary
        """
        if len(self.metrics) == 0:
            return {}

        import numpy as np

        # Extract time series
        ecp_utilities = [m.get('ecp_utility', 0) for m in self.metrics]
        system_utilities = [m.get('system_utility', 0) for m in self.metrics]

        self.summary = {
            'total_records': len(self.metrics),
            'ecp_utility_mean': np.mean(ecp_utilities),
            'system_utility_mean': np.mean(system_utilities),
        }

        return self.summary

    def export_csv(self, filename: str):
        """
        Export metrics to CSV.

        Args:
            filename: Output filename
        """
        import pandas as pd

        if len(self.metrics) == 0:
            logger.warning("No metrics to export")
            return

        df = pd.DataFrame(self.metrics)
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filename, index=False)
        logger.info(f"Exported metrics to {filename}")

    def export_json(self, filename: str):
        """
        Export metrics to JSON.

        Args:
            filename: Output filename
        """
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w') as f:
            json.dump({
                'metrics': self.metrics,
                'summary': self.get_summary()
            }, f, indent=2)
        logger.info(f"Exported metrics to {filename}")
