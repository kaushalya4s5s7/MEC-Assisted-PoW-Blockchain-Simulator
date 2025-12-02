
import logging
import numpy as np
from scipy import stats
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class StatisticsAnalyzer:
    """
    A class for performing statistical analysis on simulation results.
    """

    def calculate_confidence_interval(self, data: List[float], confidence: float = 0.95) -> tuple:
        """
        Calculates the confidence interval for a given dataset.

        Args:
            data (List[float]): A list of numerical data.
            confidence (float): The desired confidence level.

        Returns:
            tuple: A tuple containing the mean, lower bound, and upper bound of the interval.
        """
        if not data or len(data) < 2:
            return (np.mean(data) if data else 0, np.mean(data) if data else 0, np.mean(data) if data else 0)
        
        mean = np.mean(data)
        sem = stats.sem(data)
        if sem == 0:
            return mean, mean, mean
            
        t_val = stats.t.ppf((1 + confidence) / 2., len(data)-1)
        margin_of_error = t_val * sem
        
        return mean, mean - margin_of_error, mean + margin_of_error

    def calculate_improvement_percentage(self, baseline: float, improved: float) -> float:
        """
        Calculates the percentage improvement of a metric.

        Args:
            baseline (float): The baseline value.
            improved (float): The improved value.

        Returns:
            float: The percentage improvement.
        """
        if baseline == 0:
            return float('inf') if improved > 0 else 0.0
        
        return ((improved - baseline) / baseline) * 100

    def validate_against_paper(self, results: Dict[str, Any], expected_improvements: Dict[str, Any], tolerance: float = 0.05) -> Dict[str, Any]:
        """
        Validates simulation results against expected improvements from the paper.

        Args:
            results (Dict[str, Any]): A dictionary of simulation results.
            expected_improvements (Dict[str, Any]): A dictionary of expected improvements.
            tolerance (float): The allowed tolerance for validation.

        Returns:
            Dict[str, Any]: A validation report.
        """
        report = {}
        for scenario, expected in expected_improvements.items():
            if scenario not in results:
                continue

            actual = results[scenario]
            # Assuming 'system_utility' is a key metric to check
            actual_utility = actual.get('system_utility', {}).get('mean', 0)
            
            # This is a placeholder for the actual comparison logic
            # which might be more complex
            diff = self.calculate_improvement_percentage(expected, actual_utility)
            
            report[scenario] = {
                'expected': expected,
                'actual': actual_utility,
                'difference': diff,
                'passed': abs(diff) <= tolerance * 100
            }
        return report

    def aggregate_runs(self, list_of_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregates results from multiple simulation runs.

        Args:
            list_of_results (List[Dict[str, Any]]): A list of result dictionaries.

        Returns:
            Dict[str, Any]: A dictionary of aggregated statistics.
        """
        if not list_of_results:
            return {}

        aggregated = {}
        # Assuming all results have the same keys
        for key in list_of_results[0].keys():
            # This is a simplification. A real implementation would handle nested dicts.
            if isinstance(list_of_results[0][key], (int, float)):
                data = [res[key] for res in list_of_results]
                aggregated[key] = {
                    'mean': np.mean(data),
                    'std': np.std(data),
                    'min': np.min(data),
                    'max': np.max(data)
                }
        return aggregated

    def perform_t_test(self, baseline_results: List[float], enhanced_results: List[float]) -> tuple:
        """
        Performs an independent t-test to check for significant improvement.

        Args:
            baseline_results (List[float]): The results from the baseline scenario.
            enhanced_results (List[float]): The results from the enhanced scenario.

        Returns:
            tuple: A tuple containing a boolean for statistical significance and the p-value.
        """
        if not baseline_results or not enhanced_results:
            return False, 1.0

        t_stat, p_value = stats.ttest_ind(baseline_results, enhanced_results, equal_var=False)
        
        # We are looking for an improvement, so this is a one-tailed test.
        # We check if the mean of enhanced is greater than baseline.
        is_significant = (p_value / 2 < 0.05) and (np.mean(enhanced_results) > np.mean(baseline_results))

        return is_significant, p_value
