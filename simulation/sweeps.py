
import logging
import copy
from typing import Iterable, Dict, Any, List

logger = logging.getLogger(__name__)

def _run_sweep(
    scenario_name: str,
    param_name: str,
    param_range: Iterable,
    runs_per_value: int
) -> Dict[str, List[Any]]:
    """
    Generic helper function to run a parameter sweep.

    Args:
        scenario_name (str): The name of the scenario to run.
        param_name (str): The configuration parameter to vary.
        param_range (Iterable): The range of values for the parameter.
        runs_per_value (int): The number of simulation runs for each parameter value.

    Returns:
        Dict[str, List[Any]]: A dictionary containing the results of the sweep.
                                The keys are the parameter name and metric names.
    """
    from .engine import SimulationEngine
    from .config import get_scenario_config

    logger.info(f"Starting sweep for parameter '{param_name}' on scenario '{scenario_name}'...")
    
    base_config = get_scenario_config(scenario_name)
    all_results = {param_name: []}

    for value in param_range:
        logger.debug(f"Running simulation for {param_name} = {value}")
        
        # Create a deep copy of the config to avoid modifying the original
        temp_config = copy.deepcopy(base_config)
        temp_config[param_name] = value
        
        try:
            engine = SimulationEngine(temp_config)
            results = engine.run(num_runs=runs_per_value)
            
            # Store the parameter value
            all_results[param_name].append(value)
            
            # Store the mean of each result metric
            for key, stats in results.items():
                if isinstance(stats, dict) and 'mean' in stats:
                    if key not in all_results:
                        all_results[key] = []
                    all_results[key].append(stats['mean'])

        except Exception as e:
            logger.error(f"Failed to run sweep for {param_name}={value}: {e}", exc_info=True)
            # Skip this value and continue
            continue

    logger.info(f"Sweep for parameter '{param_name}' completed.")
    return all_results

def sweep_ecp_price(scenario_name: str, price_range: Iterable, runs_per_value: int) -> Dict[str, List[Any]]:
    """Runs a simulation sweep varying the ECP initial price."""
    return _run_sweep(scenario_name, 'ECP_INITIAL_PRICE', price_range, runs_per_value)

def sweep_num_miners(scenario_name: str, miner_range: Iterable, runs_per_value: int) -> Dict[str, List[Any]]:
    """Runs a simulation sweep varying the number of miners."""
    return _run_sweep(scenario_name, 'N_MINERS', miner_range, runs_per_value)

def sweep_transactions_per_block(scenario_name: str, tx_range: Iterable, runs_per_value: int) -> Dict[str, List[Any]]:
    """Runs a simulation sweep varying the number of transactions per block."""
    return _run_sweep(scenario_name, 'TRANSACTIONS_PER_BLOCK_I', tx_range, runs_per_value)

def sweep_block_reward(scenario_name: str, reward_range: Iterable, runs_per_value: int) -> Dict[str, List[Any]]:
    """Runs a simulation sweep varying the block reward."""
    return _run_sweep(scenario_name, 'BLOCK_REWARD_B', reward_range, runs_per_value)
