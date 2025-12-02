
import logging
from typing import Dict, Any

# Use local imports to avoid circular dependencies
def _run_scenario(scenario_name: str, num_runs: int) -> Dict[str, Any]:
    """Helper function to run a single scenario."""
    from simulation.engine import SimulationEngine
    from simulation.config import get_scenario_config

    logger = logging.getLogger(__name__)
    logger.info(f"Running baseline scenario: {scenario_name} for {num_runs} runs...")
    
    try:
        config = get_scenario_config(scenario_name)
        engine = SimulationEngine(config)
        results = engine.run(num_runs=num_runs)
        logger.info(f"Finished running scenario: {scenario_name}")
        return results
    except Exception as e:
        logger.error(f"Error running scenario {scenario_name}: {e}", exc_info=True)
        return {"error": str(e)}

def run_non_cooperative(num_runs: int = 500) -> Dict[str, Any]:
    """Runs the non-cooperative baseline scenario."""
    return _run_scenario('non_cooperative', num_runs)

def run_single_coalition(num_runs: int = 500) -> Dict[str, Any]:
    """Runs the single coalition (J=1) baseline scenario."""
    return _run_scenario('single_coalition', num_runs)

def run_multi_coalition_j2(num_runs: int = 500) -> Dict[str, Any]:
    """Runs the multi-coalition (J=2) baseline scenario."""
    return _run_scenario('multi_coalition_j2', num_runs)

def run_multi_coalition_j3_naive(num_runs: int = 500) -> Dict[str, Any]:
    """Runs the naive multi-coalition (J=3) baseline scenario."""
    return _run_scenario('multi_coalition_j3_naive', num_runs)

def run_all_baseline_scenarios(num_runs: int = 500) -> Dict[str, Dict[str, Any]]:
    """
    Runs all defined baseline scenarios and collects their results.

    Args:
        num_runs (int): The number of simulation runs for each scenario.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary where keys are scenario names
                                   and values are the corresponding results.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Running all baseline scenarios for {num_runs} runs each...")
    
    scenarios = {
        'non_cooperative': run_non_cooperative,
        'single_coalition': run_single_coalition,
        'multi_coalition_j2': run_multi_coalition_j2,
        'multi_coalition_j3_naive': run_multi_coalition_j3_naive,
    }
    
    all_results = {}
    for name, run_func in scenarios.items():
        all_results[name] = run_func(num_runs=num_runs)
        
    logger.info("All baseline scenarios have been executed.")
    return all_results
