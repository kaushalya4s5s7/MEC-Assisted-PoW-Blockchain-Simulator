
import csv
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ResultsExporter:
    """
    Handles exporting of simulation results to various formats.
    """

    def _ensure_dir_exists(self, filename: str):
        """Ensure the directory for the given filename exists."""
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

    def export_to_csv(self, results: Dict[str, Any], filename: str):
        """
        Exports a dictionary of results to a CSV file.

        Args:
            results (Dict[str, Any]): The results dictionary.
            filename (str): The path to the output CSV file.
        """
        self._ensure_dir_exists(filename)
        try:
            # This handles nested dictionaries by flattening them
            if results and isinstance(next(iter(results.values())), dict):
                df = pd.json_normalize(results, sep='_')
            else:
                df = pd.DataFrame([results])

            df.to_csv(filename, index=False)
            logger.info(f"Results successfully exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")

    def export_to_json(self, results: Dict[str, Any], filename: str):
        """
        Exports a dictionary of results to a JSON file.

        Args:
            results (Dict[str, Any]): The results dictionary.
            filename (str): The path to the output JSON file.
        """
        self._ensure_dir_exists(filename)
        metadata = {
            "export_timestamp": datetime.now().isoformat(),
            "scenario": results.get("scenario_name", "unknown")
        }
        data_to_export = {"metadata": metadata, "results": results}
        
        try:
            with open(filename, 'w') as f:
                json.dump(data_to_export, f, indent=4)
            logger.info(f"Results successfully exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")

    def create_summary_table(self, all_scenario_results: Dict[str, Any], filename: str = "results/summary_statistics.csv"):
        """
        Creates a summary table comparing different scenarios.

        Args:
            all_scenario_results (Dict[str, Any]): A dictionary where keys are scenario names
                                                  and values are their results.
            filename (str): The output CSV file path.
        """
        self._ensure_dir_exists(filename)
        summary_data = []
        for scenario, results in all_scenario_results.items():
            row = {
                "Scenario": scenario,
                "ECP Utility": results.get("ecp_utility", {}).get("mean", "N/A"),
                "System Utility": results.get("system_utility", {}).get("mean", "N/A"),
                "Average Coalition Size": results.get("avg_coalition_size", {}).get("mean", "N/A"),
                "Bandwidth (KB/s)": results.get("bandwidth", {}).get("mean", "N/A")
            }
            summary_data.append(row)
        
        try:
            df = pd.DataFrame(summary_data)
            df.to_csv(filename, index=False)
            logger.info(f"Summary table created at {filename}")
        except Exception as e:
            logger.error(f"Failed to create summary table: {e}")


    def create_improvement_table(self, baseline: Dict[str, Any], enhanced: Dict[str, Any], filename: str = "results/improvement_analysis.csv"):
        """
        Creates a table showing improvement percentages between baseline and enhanced results.

        Args:
            baseline (Dict[str, Any]): The baseline results dictionary.
            enhanced (Dict[str, Any]): The enhanced results dictionary.
            filename (str): The output CSV file path.
        """
        self._ensure_dir_exists(filename)
        from .statistics import StatisticsAnalyzer  # Local import
        analyzer = StatisticsAnalyzer()
        
        improvement_data = []
        metrics = set(baseline.keys()) & set(enhanced.keys())

        for metric in metrics:
            if isinstance(baseline[metric], dict) and isinstance(enhanced[metric], dict):
                base_val = baseline[metric].get("mean")
                enh_val = enhanced[metric].get("mean")
                
                if base_val is not None and enh_val is not None:
                    improvement = analyzer.calculate_improvement_percentage(base_val, enh_val)
                    row = {
                        "Innovation": "Enhanced vs Baseline",
                        "Metric": metric,
                        "Baseline": base_val,
                        "Enhanced": enh_val,
                        "Improvement %": improvement
                    }
                    improvement_data.append(row)
        
        try:
            df = pd.DataFrame(improvement_data)
            df.to_csv(filename, index=False)
            logger.info(f"Improvement analysis table created at {filename}")
        except Exception as e:
            logger.error(f"Failed to create improvement table: {e}")

    def export_metrics_history(self, metrics_history: List[Dict[str, Any]], filename: str):
        """
        Exports time-series metric data to a CSV file.

        Args:
            metrics_history (List[Dict[str, Any]]): A list of dictionaries, where each
                                                     dict represents a time step.
            filename (str): The output CSV file path.
        """
        self._ensure_dir_exists(filename)
        if not metrics_history:
            logger.warning("Metrics history is empty. Nothing to export.")
            return

        try:
            df = pd.DataFrame(metrics_history)
            df.to_csv(filename, index_label="time_step")
            logger.info(f"Metrics history exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export metrics history: {e}")
