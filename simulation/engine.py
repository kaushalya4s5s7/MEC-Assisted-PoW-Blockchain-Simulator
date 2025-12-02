"""
Simulation Engine - Main discrete event simulation loop.

This module implements the core simulation engine that orchestrates:
- Coalition formation (OCF game)
- ECP pricing updates
- Transaction collection
- Block discovery
- Reward distribution
- Metrics recording
"""

import random
import logging
from typing import List, Dict, Optional, Set
from tqdm import tqdm

from entities.miner import Miner, Transaction
from entities.coalition import Coalition
from entities.ecp import ECP
from simulation.config import (
    N_MINERS, BLOCK_REWARD_B, TRANSACTIONS_PER_BLOCK_I,
    TOTAL_TRANSACTIONS, DIFFICULTY, TIMESTEP,
    WARMUP_PERIOD, COLLECTION_PERIOD, TOTAL_SIMULATION_TIME,
    get_hashrate_sample, get_transaction_fee_sample,
    reset_random_seeds, OCF_MAX_ITERATIONS,
    OCF_CONVERGENCE_EPSILON, ECP_OPTIMIZATION_ENABLED
)
from simulation.utils import (
    calculate_miner_utility, calculate_ecp_utility,
    calculate_system_utility, get_block_finder
)


logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Main simulation engine implementing discrete event simulation.

    Manages the complete lifecycle of a simulation run including:
    - Initialization of miners, coalitions, ECP
    - Coalition formation via OCF game
    - Block discovery and reward distribution
    - Metrics collection
    """

    def __init__(self, scenario_config: Dict):
        """
        Initialize simulation engine with scenario configuration.

        Args:
            scenario_config: Configuration dictionary for the scenario
        """
        self.config = scenario_config
        self.scenario_name = scenario_config['name']

        # Simulation state
        self.current_time = 0.0
        self.is_warmup = True

        # Entities
        self.miners: List[Miner] = []
        self.coalitions: List[Coalition] = []
        self.ecp: Optional[ECP] = None

        # Transaction pool
        self.global_transaction_pool: Set[Transaction] = set()

        # Metrics
        self.metrics_history = []
        self.current_metrics = {}

        # Statistics
        self.blocks_found = 0
        self.total_rewards_distributed = 0.0

        logger.info(f"Initialized simulation engine for scenario: {self.scenario_name}")

    def initialize(self):
        """Initialize all entities for a simulation run."""
        logger.debug("Initializing simulation entities...")

        # Reset random seeds for reproducibility if configured
        reset_random_seeds()

        # Create miners
        self.miners = []
        for i in range(N_MINERS):
            hashrate = get_hashrate_sample()
            miner = Miner(miner_id=i, hashrate=hashrate)
            self.miners.append(miner)

        logger.debug(f"Created {len(self.miners)} miners")

        # Create ECP if enabled
        if self.config.get('ecp_enabled', True):
            self.ecp = ECP()
            logger.debug("Created ECP")

        # Create initial coalitions
        self.coalitions = []

        # For non-zero coalition scenarios, seed with a few initial coalitions
        # to avoid everyone splitting in the first OCF iteration
        max_coalitions = self.config.get('max_coalitions', 3)
        if max_coalitions > 0:
            # Create 2-3 initial seed coalitions with random miners
            import random
            num_seed_coalitions = min(3, max(1, N_MINERS // 5))

            # Shuffle miners for random assignment
            available_miners = self.miners.copy()
            random.shuffle(available_miners)

            # Create seed coalitions
            for i in range(num_seed_coalitions):
                # Pick a random miner as coalition head
                if available_miners:
                    head_miner = available_miners.pop(0)
                    coalition = Coalition(coalition_id=i, head_miner=head_miner)
                    self.coalitions.append(coalition)
                    head_miner.join_coalition(coalition)

            # Remaining miners will join coalitions via OCF game
            logger.debug(f"Created {len(self.coalitions)} seed coalitions")
        else:
            # Non-cooperative scenario: Each miner becomes their own solo coalition
            # This allows them to mine individually without cooperation
            logger.debug("Non-cooperative mode: Creating solo coalitions for each miner")
            for i, miner in enumerate(self.miners):
                solo_coalition = Coalition(coalition_id=i, head_miner=miner)
                self.coalitions.append(solo_coalition)
                miner.join_coalition(solo_coalition)
            logger.debug(f"Created {len(self.coalitions)} solo coalitions (non-cooperative)")

        # Initialize transaction pool
        self.global_transaction_pool = {
            Transaction(tx_id=i, fee=get_transaction_fee_sample())
            for i in range(TOTAL_TRANSACTIONS)
        }

        logger.debug(f"Created {len(self.global_transaction_pool)} transactions")

        # Reset simulation state
        self.current_time = 0.0
        self.is_warmup = True
        self.blocks_found = 0
        self.total_rewards_distributed = 0.0
        self.metrics_history = []

        logger.info("Simulation initialized successfully")

    def run(self, num_runs: int = 1) -> Dict:
        """
        Run complete simulation with multiple repetitions.

        Args:
            num_runs: Number of simulation runs for statistical analysis

        Returns:
            Aggregated results across all runs
        """
        logger.info(f"Starting simulation: {num_runs} runs")

        all_results = []

        # Progress bar
        for run_num in tqdm(range(num_runs), desc=f"Running {self.scenario_name}"):
            logger.debug(f"Starting run {run_num + 1}/{num_runs}")

            # Run single simulation
            result = self.single_run()
            all_results.append(result)

            logger.debug(f"Completed run {run_num + 1}/{num_runs}")

        # Aggregate results
        aggregated = self.aggregate_results(all_results)

        logger.info(f"Simulation completed: {num_runs} runs")

        return aggregated

    def single_run(self) -> Dict:
        """
        Execute a single simulation run.

        Returns:
            Metrics from this run
        """
        # Initialize
        self.initialize()

        # Warmup period - let coalitions form
        logger.debug(f"Warmup period: {WARMUP_PERIOD}s")
        self.is_warmup = True
        for t in range(0, WARMUP_PERIOD, int(TIMESTEP)):
            self.step(t)

        # Collection period - record metrics
        logger.debug(f"Collection period: {COLLECTION_PERIOD}s")
        self.is_warmup = False
        for t in range(WARMUP_PERIOD, TOTAL_SIMULATION_TIME, int(TIMESTEP)):
            self.step(t)

            # Record metrics every 10 seconds
            if t % 10 == 0:
                self.record_metrics(t)

        # Return final metrics
        return self.get_final_metrics()

    def step(self, time: float):
        """
        Execute one timestep of the simulation.

        Args:
            time: Current simulation time
        """
        self.current_time = time

        # 1. Coalition formation (OCF game) - every 50 seconds (optimized for speed)
        # Skip OCF for non-cooperative scenario (max_coalitions = 0)
        max_coalitions = self.config.get('max_coalitions', 3)
        if time % 50 == 0 and max_coalitions > 0:
            self.run_coalition_formation()

        # 2. Miners collect transactions
        self.miners_collect_transactions()

        # 3. Coalitions aggregate transactions
        for coalition in self.coalitions:
            coalition.aggregate_transactions()

        # 4. ECP updates pricing - every 50 seconds (optimized for speed)
        if self.ecp and time % 50 == 0:
            self.ecp.set_optimal_price(self.coalitions)

        # 5. Coalitions request ECP compute
        if self.ecp:
            self.coalitions_request_compute()

        # 6. Attempt block discovery
        self.attempt_block_discovery()

        # 7. Reset ECP load
        if self.ecp:
            self.ecp.reset_load()

    def run_coalition_formation(self):
        """
        Execute OCF game for coalition formation.

        Implements alternating iteration algorithm where miners
        evaluate strategies (MERGE, SPLIT, LEAVE, STAY) and execute
        the best one.
        """
        max_coalitions = self.config.get('max_coalitions', 3)
        logger.info(f"    - OCF: Using max_coalitions = {max_coalitions}")

        if max_coalitions == 0:
            # Non-cooperative mode - no coalitions
            return

        logger.info(f"    - [Time: {self.current_time:.2f}s] Running coalition formation game...")

        # Iterate until convergence
        for iteration in range(OCF_MAX_ITERATIONS):
            changes_made = False

            # Log progress
            if (iteration + 1) % 10 == 0:
                logger.info(f"      - OCF iteration {iteration + 1}/{OCF_MAX_ITERATIONS}...")

            # Random order to avoid bias
            miners_order = self.miners.copy()
            random.shuffle(miners_order)

            for miner in miners_order:
                # Evaluate all strategies
                current_utility = miner.get_total_utility()
                best_strategy = ('STAY', current_utility, None)

                # MERGE: Try joining existing coalitions
                if len(miner.coalitions) < max_coalitions:
                    for coalition in self.coalitions:
                        if coalition not in miner.coalitions:
                            # Check if can join
                            if coalition.check_definition_4(miner):
                                projected_utility = miner.evaluate_coalition_utility(coalition)
                                if projected_utility > best_strategy[1] + OCF_CONVERGENCE_EPSILON:
                                    best_strategy = ('MERGE', projected_utility, coalition)

                # SPLIT: Create solo coalition
                if len(miner.coalitions) < max_coalitions:
                    solo_utility = miner.evaluate_strategy_split()
                    if solo_utility > best_strategy[1] + OCF_CONVERGENCE_EPSILON:
                        best_strategy = ('SPLIT', solo_utility, None)

                # LEAVE: Leave a coalition
                for coalition in miner.coalitions:
                    leave_utility = miner.evaluate_strategy_leave(coalition)
                    if leave_utility > best_strategy[1] + OCF_CONVERGENCE_EPSILON:
                        best_strategy = ('LEAVE', leave_utility, coalition)

                # Execute best strategy
                strategy, utility, target = best_strategy

                if strategy == 'MERGE' and target:
                    if target.add_member(miner):
                        miner.join_coalition(target)
                        changes_made = True
                        logger.info(f"      - Miner {miner.miner_id} MERGED into Coalition {target.coalition_id}")

                elif strategy == 'SPLIT':
                    # Create new coalition with this miner
                    new_coalition = Coalition(len(self.coalitions), miner)
                    self.coalitions.append(new_coalition)
                    miner.join_coalition(new_coalition)
                    changes_made = True
                    logger.info(f"      - Miner {miner.miner_id} SPLIT to form Coalition {new_coalition.coalition_id}")

                elif strategy == 'LEAVE' and target:
                    target.remove_member(miner)
                    miner.leave_coalition(target)
                    changes_made = True
                    logger.info(f"      - Miner {miner.miner_id} LEFT Coalition {target.coalition_id}")

                    # Remove empty coalitions
                    if len(target.members) == 0:
                        self.coalitions.remove(target)

            # Check convergence
            if not changes_made:
                logger.info(f"    - OCF game converged in {iteration + 1} iterations.")
                break
        else:
            logger.info(f"    - OCF game finished after {OCF_MAX_ITERATIONS} iterations (max).")

        # Update ECP membership graph
        if self.ecp and ECP_OPTIMIZATION_ENABLED:
            self.ecp.update_membership_graph(self.coalitions)

    def miners_collect_transactions(self):
        """Miners collect transactions from the network."""
        pool_list = list(self.global_transaction_pool)
        for miner in self.miners:
            miner.collect_transactions(pool_list, TIMESTEP)

    def coalitions_request_compute(self):
        """Coalitions calculate and request optimal compute from ECP."""
        if not self.ecp:
            return

        for coalition in self.coalitions:
            # Calculate optimal compute demand
            optimal_compute = coalition.calculate_optimal_compute_demand(
                self.ecp.price_per_hash,
                self.ecp.operating_cost_per_hash
            )

            if optimal_compute > 0:
                coalition.request_ecp_compute(self.ecp, optimal_compute)

        # Apply overlap optimization
        if ECP_OPTIMIZATION_ENABLED:
            self.ecp.optimize_overlapping_work(self.ecp.compute_requests)

    def attempt_block_discovery(self):
        """
        Check if any coalition discovers a block.

        Uses Poisson process with hashrate-proportional probability.
        """
        if len(self.coalitions) == 0:
            return

        # Calculate total network hashrate
        total_hashrate = 0.0
        for coalition in self.coalitions:
            total_hashrate += coalition.get_effective_hashrate()

        if total_hashrate == 0:
            return

        # Check which coalition (if any) finds a block
        winner = get_block_finder(self.coalitions, total_hashrate, TIMESTEP, DIFFICULTY)

        if winner:
            self.handle_block_found(winner)

    def handle_block_found(self, coalition: Coalition):
        """
        Handle block discovery by a coalition.

        Args:
            coalition: Coalition that found the block
        """
        logger.debug(f"Block found by Coalition {coalition.coalition_id}")

        # Select transactions for block
        selected_transactions = coalition.select_transactions_for_block(TRANSACTIONS_PER_BLOCK_I)

        # Calculate rewards
        block_reward = BLOCK_REWARD_B
        transaction_fees = sum(tx.fee for tx in selected_transactions)
        total_reward = block_reward + transaction_fees

        # Distribute rewards
        ecp_price = self.ecp.price_per_hash if self.ecp else 0.0
        coalition.distribute_rewards(total_reward, ecp_price)

        # Update coalition stats
        coalition.blocks_found += 1

        # Update global stats
        self.blocks_found += 1
        self.total_rewards_distributed += total_reward

        logger.info(
            f"    - [Time: {self.current_time:.2f}s] Block {self.blocks_found} found by Coalition {coalition.coalition_id}! "
            f"Reward: {total_reward:.2f}, Txs: {len(selected_transactions)}"
        )

        # Remove transactions from global pool
        self.global_transaction_pool.difference_update(selected_transactions)

        # Remove from miners' pools
        for miner in self.miners:
            miner.clear_transactions(selected_transactions)

        logger.debug(f"Block {self.blocks_found}: Reward={total_reward:.2f}, Coalition={coalition.coalition_id}")

    def record_metrics(self, time: float):
        """
        Record current metrics.

        Args:
            time: Current simulation time
        """
        if self.is_warmup:
            return

        # Calculate utilities
        ecp_utility = calculate_ecp_utility(self.ecp) if self.ecp else 0.0
        # System utility should always be calculated (includes miner earnings even without ECP)
        system_utility = calculate_system_utility(self.miners, self.ecp)

        # Calculate average coalition size
        avg_coalition_size = sum(len(c.members) for c in self.coalitions) / len(self.coalitions) if self.coalitions else 0

        # Total nonce length (ECP compute)
        total_nonce = self.ecp.get_total_demand() if self.ecp else 0.0

        # Calculate bandwidth consumption
        bandwidth = self.calculate_bandwidth()

        metrics = {
            'time': time,
            'ecp_utility': ecp_utility,
            'system_utility': system_utility,
            'total_nonce_length': total_nonce,
            'avg_coalition_size': avg_coalition_size,
            'num_coalitions': len(self.coalitions),
            'blocks_found': self.blocks_found,
            'total_rewards': self.total_rewards_distributed,
            'ecp_price': self.ecp.price_per_hash if self.ecp else 0.0,
            'bandwidth_kb': bandwidth / 1024,  # Convert bytes to KB
        }

        self.metrics_history.append(metrics)
        self.current_metrics = metrics

    def calculate_bandwidth(self) -> float:
        """
        Calculate total bandwidth consumption for transaction synchronization.

        Compares naive approach (sending all transactions to all coalitions)
        vs optimized approach (using Bloom filters for efficient synchronization).

        Returns:
            Total bandwidth in bytes across all miners
        """
        from protocols.bloom_filter import BloomFilterSync
        from simulation.config import TRANSACTION_SIZE

        total_bandwidth = 0.0
        bloom_enabled = self.config.get('bloom_filter', False)

        for miner in self.miners:
            num_coalitions = len(miner.coalitions)
            if num_coalitions == 0:
                continue

            # Number of transactions this miner has
            num_transactions = len(miner.transactions)
            if num_transactions == 0:
                continue

            if bloom_enabled:
                # Use Bloom filter optimization (Innovation 1)
                # Create Bloom filter syncer
                bloom_sync = BloomFilterSync(capacity=max(1000, num_transactions))

                # Assume ~10-20% new transactions per sync period
                # (rest are already synchronized via Bloom filter)
                num_new_transactions = int(num_transactions * 0.15)

                # Calculate optimized bandwidth:
                # - Initial: Bloom filter sent to each coalition (small)
                # - Updates: Only new/missing transactions sent
                bandwidth = bloom_sync.calculate_bandwidth_optimized(
                    num_transactions=num_transactions,
                    num_coalitions=num_coalitions,
                    num_new_transactions=num_new_transactions
                )
            else:
                # Naive approach: send all transactions to all coalitions
                # Bandwidth = num_transactions × num_coalitions × transaction_size
                bandwidth = num_transactions * num_coalitions * TRANSACTION_SIZE

            total_bandwidth += bandwidth

        return total_bandwidth

    def get_final_metrics(self) -> Dict:
        """
        Get final aggregated metrics from this run.

        Returns:
            Dictionary of final metrics
        """
        if len(self.metrics_history) == 0:
            return {}

        # Calculate averages
        avg_ecp_utility = sum(m['ecp_utility'] for m in self.metrics_history) / len(self.metrics_history)
        avg_system_utility = sum(m['system_utility'] for m in self.metrics_history) / len(self.metrics_history)
        avg_coalition_size = sum(m['avg_coalition_size'] for m in self.metrics_history) / len(self.metrics_history)
        avg_nonce_length = sum(m['total_nonce_length'] for m in self.metrics_history) / len(self.metrics_history)
        avg_bandwidth_kb = sum(m.get('bandwidth_kb', 0.0) for m in self.metrics_history) / len(self.metrics_history)

        return {
            'scenario': self.scenario_name,
            'blocks_found': self.blocks_found,
            'total_rewards': self.total_rewards_distributed,
            'avg_ecp_utility': avg_ecp_utility,
            'avg_system_utility': avg_system_utility,
            'avg_coalition_size': avg_coalition_size,
            'avg_nonce_length': avg_nonce_length,
            'avg_bandwidth_kb': avg_bandwidth_kb,
            'final_num_coalitions': len(self.coalitions),
            'metrics_history': self.metrics_history
        }

    def aggregate_results(self, results: List[Dict]) -> Dict:
        """
        Aggregate results from multiple runs.

        Args:
            results: List of results from individual runs

        Returns:
            Aggregated results with statistics
        """
        if len(results) == 0:
            return {}

        import numpy as np

        # Extract metrics
        ecp_utilities = [r['avg_ecp_utility'] for r in results]
        system_utilities = [r['avg_system_utility'] for r in results]
        coalition_sizes = [r['avg_coalition_size'] for r in results]
        nonce_lengths = [r['avg_nonce_length'] for r in results]
        bandwidth_kbs = [r.get('avg_bandwidth_kb', 0.0) for r in results]

        # Calculate statistics
        aggregated = {
            'scenario': self.scenario_name,
            'num_runs': len(results),
            'ecp_utility': {
                'mean': np.mean(ecp_utilities),
                'std': np.std(ecp_utilities),
                'min': np.min(ecp_utilities),
                'max': np.max(ecp_utilities),
                'ci_95': self.calculate_ci(ecp_utilities)
            },
            'system_utility': {
                'mean': np.mean(system_utilities),
                'std': np.std(system_utilities),
                'min': np.min(system_utilities),
                'max': np.max(system_utilities),
                'ci_95': self.calculate_ci(system_utilities)
            },
            'avg_coalition_size': {
                'mean': np.mean(coalition_sizes),
                'std': np.std(coalition_sizes),
            },
            'avg_nonce_length': {
                'mean': np.mean(nonce_lengths),
                'std': np.std(nonce_lengths),
            },
            'avg_bandwidth_kb': {
                'mean': np.mean(bandwidth_kbs),
                'std': np.std(bandwidth_kbs),
                'min': np.min(bandwidth_kbs),
                'max': np.max(bandwidth_kbs),
            },
            'blocks_found': sum(r['blocks_found'] for r in results) / len(results),
            'total_rewards': sum(r['total_rewards'] for r in results) / len(results),
        }

        return aggregated

    def calculate_ci(self, data: List[float], confidence: float = 0.95) -> tuple:
        """
        Calculate confidence interval.

        Args:
            data: Data values
            confidence: Confidence level

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        import numpy as np
        from scipy import stats

        if len(data) < 2:
            return (0.0, 0.0)

        mean = np.mean(data)
        std_error = np.std(data, ddof=1) / np.sqrt(len(data))
        t_value = stats.t.ppf((1 + confidence) / 2, len(data) - 1)
        margin = t_value * std_error

        return (mean - margin, mean + margin)
