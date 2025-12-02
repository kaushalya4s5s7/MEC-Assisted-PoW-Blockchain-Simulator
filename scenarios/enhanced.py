
import logging
from typing import Dict, Any

# Use local imports to avoid circular dependencies
def _run_enhanced_scenario(scenario_name: str, num_runs: int) -> Dict[str, Any]:
    """Helper function to run a single enhanced scenario."""
    from simulation.engine import SimulationEngine
    from simulation.config import get_scenario_config

    logger = logging.getLogger(__name__)
    logger.info(f"Running enhanced scenario: {scenario_name} for {num_runs} runs...")
    
    try:
        config = get_scenario_config(scenario_name)
        # Verify that innovations are enabled
        if not all(config.get(f) for f in ['INNOVATION_SMART_CONTRACTS', 'INNOVATION_BLOOM_FILTER', 'INNOVATION_ZK_PROOFS', 'INNOVATION_DUAL_CHANNEL']):
            logger.warning(f"Scenario {scenario_name} is running but not all innovations are enabled in config.")
        
        engine = SimulationEngine(config)
        results = engine.run(num_runs=num_runs)
        logger.info(f"Finished running enhanced scenario: {scenario_name}")
        return results
    except Exception as e:
        logger.error(f"Error running enhanced scenario {scenario_name}: {e}", exc_info=True)
        return {"error": str(e)}

def run_enhanced_j3(num_runs: int = 500) -> Dict[str, Any]:
    """Runs the enhanced multi-coalition (J=3) scenario."""
    return _run_enhanced_scenario('enhanced_j3', num_runs)

def run_enhanced_j5(num_runs: int = 500) -> Dict[str, Any]:
    """Runs the enhanced multi-coalition (J=5) scenario."""
    return _run_enhanced_scenario('enhanced_j5', num_runs)

def run_enhanced_j7(num_runs: int = 500) -> Dict[str, Any]:
    """Runs the enhanced multi-coalition (J=7) scenario."""
    return _run_enhanced_scenario('enhanced_j7', num_runs)

def run_all_enhanced_scenarios(num_runs: int = 500) -> Dict[str, Dict[str, Any]]:
    """
    Runs all defined enhanced scenarios and collects their results.

    Args:
        num_runs (int): The number of simulation runs for each scenario.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary with scenario names as keys and results as values.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Running all enhanced scenarios for {num_runs} runs each...")
    
    scenarios = {
        'enhanced_j3': run_enhanced_j3,
        'enhanced_j5': run_enhanced_j5,
        'enhanced_j7': run_enhanced_j7,
    }
    
    all_results = {}
    for name, run_func in scenarios.items():
        all_results[name] = run_func(num_runs=num_runs)
        
    logger.info("All enhanced scenarios have been executed.")
    return all_results

def compare_with_baseline(baseline_results: Dict[str, Any], enhanced_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares enhanced results with baseline results and calculates improvements.

    Args:
        baseline_results (Dict[str, Any]): The results from a baseline scenario run.
        enhanced_results (Dict[str, Any]): The results from an enhanced scenario run.

    Returns:
        Dict[str, Any]: A dictionary detailing the percentage improvements.
    """
    from analysis.statistics import StatisticsAnalyzer
    analyzer = StatisticsAnalyzer()
    
    logger = logging.getLogger(__name__)
    logger.info("Comparing enhanced results with baseline...")

    comparison = {}
    metrics_to_compare = ['system_utility', 'ecp_utility', 'avg_coalition_size', 'bandwidth']

    for metric in metrics_to_compare:
        base_metric = baseline_results.get(metric, {})
        enh_metric = enhanced_results.get(metric, {})
        
        base_mean = base_metric.get('mean')
        enh_mean = enh_metric.get('mean')

        if base_mean is not None and enh_mean is not None:
            improvement = analyzer.calculate_improvement_percentage(base_mean, enh_mean)
            comparison[metric] = {
                'baseline_mean': base_mean,
                'enhanced_mean': enh_mean,
                'improvement_pct': improvement
            }
            logger.info(f"Improvement for {metric}: {improvement:.2f}%")
        else:
            logger.warning(f"Could not compare metric '{metric}' due to missing data.")
            
    return comparison
