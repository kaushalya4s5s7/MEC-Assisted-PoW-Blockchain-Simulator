"""
Blockchain Environment - manages the overall simulation system.
"""

import random
import math
from typing import List, Dict, Optional, Tuple

from entities.miner import Miner, Transaction
from entities.coalition import Coalition
from entities.ecp import ECP

from simulation.config import (
    TIMESTEP,
    DIFFICULTY,
    BLOCK_REWARD_B,
    TRANSACTIONS_PER_BLOCK_I,
    TOTAL_TRANSACTIONS,
    AVERAGE_BLOCK_TIME,
    LAMBDA_BLOCK_RATE,
    METRIC_RECORDING_INTERVAL,
    get_transaction_fee_sample
)


class BlockchainEnvironment:
    """
    Represents the overall blockchain mining environment.

    Manages the simulation clock, block discovery, transaction generation,
    and metrics collection.

    Properties:
        - current_time: Simulation clock (in seconds)
        - difficulty: Mining difficulty
        - block_reward: Fixed reward per block
        - transaction_pool: Global pool of pending transactions
        - miners: List of all miner objects
        - coalitions: List of all coalition objects
        - ecp: The ECP object
        - blocks_found: Total blocks found
        - metrics: Performance metrics over time
    """

    def __init__(self, miners: List[Miner], coalitions: List[Coalition],
                 ecp: ECP, scenario_config: Dict):
        """
        Initialize the blockchain environment.

        Args:
            miners: List of miner objects
            coalitions: List of coalition objects
            ecp: ECP object
            scenario_config: Configuration for this scenario
        """
        # System components
        self.miners = miners
        self.coalitions = coalitions
        self.ecp = ecp

        # Scenario configuration
        self.scenario_config = scenario_config

        # Time
        self.current_time = 0.0
        self.timestep = TIMESTEP

        # Blockchain parameters
        self.difficulty = DIFFICULTY
        self.block_reward = BLOCK_REWARD_B
        self.transactions_per_block = TRANSACTIONS_PER_BLOCK_I

        # Transaction pool
        self.transaction_pool: List[Transaction] = []
        self.transaction_counter = 0

        # Mining statistics
        self.blocks_found = 0
        self.total_rewards_distributed = 0.0
        self.blocks_by_coalition: Dict[int, int] = {}

        # Metrics collection
        self.metrics: Dict[str, List] = {
            "time": [],
            "ecp_utility": [],
            "system_utility": [],
            "total_nonce_length": [],
            "avg_coalition_size": [],
            "blocks_found": [],
            "network_hashrate": [],
            "num_coalitions": [],
            "num_transactions": []
        }
        self.metrics_recorded = 0
        self.last_metric_time = 0.0

        # Initialize transaction pool
        self._generate_initial_transactions()

    def __repr__(self):
        return f"Blockchain(time={self.current_time:.0f}s, blocks={self.blocks_found}, miners={len(self.miners)}, coalitions={len(self.coalitions)})"

    # ========================================================================
    # TRANSACTION GENERATION
    # ========================================================================

    def _generate_initial_transactions(self):
        """Generate initial transaction pool."""
        for i in range(TOTAL_TRANSACTIONS):
            tx = Transaction(
                tx_id=self.transaction_counter,
                fee=get_transaction_fee_sample()
            )
            self.transaction_pool.append(tx)
            self.transaction_counter += 1

    def generate_transactions(self):
        """
        Create new transactions periodically.

        Generates transactions to maintain pool at target size.
        """
        # Maintain pool at target size
        target_size = TOTAL_TRANSACTIONS
        current_size = len(self.transaction_pool)

        if current_size < target_size:
            # Generate new transactions
            num_to_generate = target_size - current_size

            for _ in range(num_to_generate):
                tx = Transaction(
                    tx_id=self.transaction_counter,
                    fee=get_transaction_fee_sample()
                )
                self.transaction_pool.append(tx)
                self.transaction_counter += 1

    # ========================================================================
    # BLOCK DISCOVERY
    # ========================================================================

    def attempt_block_discovery(self) -> Optional[Coalition]:
        """
        Check if any coalition found a valid block.

        Uses Poisson process model:
            P(coalition finds block) = hashrate_share × base_probability
            base_probability = 1 - e^(-λt)

        Where:
            - λ = 1/average_block_time (Poisson rate)
            - hashrate_share = coalition_hashrate / total_network_hashrate

        Returns:
            Coalition that found the block, or None if no block found
        """
        # Calculate total network hashrate
        total_network_hashrate = self.get_total_network_hashrate()

        if total_network_hashrate == 0:
            return None

        # Base probability using Poisson process
        lambda_rate = LAMBDA_BLOCK_RATE
        base_prob = 1.0 - math.exp(-lambda_rate * self.timestep)

        # Check each coalition
        for coalition in self.coalitions:
            # Coalition's effective hashrate (members + ECP)
            coalition_hashrate = coalition.get_effective_hashrate()

            if coalition_hashrate == 0:
                continue

            # Hashrate share
            hashrate_share = coalition_hashrate / total_network_hashrate

            # Coalition's probability
            coalition_prob = hashrate_share * base_prob

            # Check if block found
            if random.random() < coalition_prob:
                return coalition

        return None

    def handle_block_found(self, coalition: Coalition):
        """
        Process a block discovery event.

        Args:
            coalition: Coalition that found the block
        """
        # Aggregate transactions from coalition members
        coalition.aggregate_transactions()

        # Select best transactions for block
        selected_tx = coalition.select_transactions_for_block(self.transactions_per_block)

        # Calculate total reward
        transaction_fees = sum(tx.fee for tx in selected_tx)
        total_reward = self.block_reward + transaction_fees

        # Distribute rewards to coalition members
        coalition.distribute_rewards(total_reward, self.ecp.price_per_hash)

        # Remove selected transactions from global pool
        for tx in selected_tx:
            if tx in self.transaction_pool:
                self.transaction_pool.remove(tx)

        # Remove transactions from miners
        for miner in self.miners:
            miner.clear_transactions(selected_tx)

        # Update statistics
        self.blocks_found += 1
        coalition.blocks_found += 1
        self.total_rewards_distributed += total_reward

        # Track blocks by coalition
        if coalition.coalition_id not in self.blocks_by_coalition:
            self.blocks_by_coalition[coalition.coalition_id] = 0
        self.blocks_by_coalition[coalition.coalition_id] += 1

    def select_transactions_for_block(self, coalition: Coalition) -> List[Transaction]:
        """
        Select best transactions for a block.

        Helper method that uses coalition's transaction selection.

        Args:
            coalition: Coalition selecting transactions

        Returns:
            List of selected transactions
        """
        return coalition.select_transactions_for_block(self.transactions_per_block)

    # ========================================================================
    # SIMULATION STEP
    # ========================================================================

    def step(self):
        """
        Advance simulation by one timestep.

        Performs all actions for a single simulation step:
        1. Miners collect transactions
        2. Coalitions aggregate transactions
        3. ECP adjusts pricing
        4. Attempt block discovery
        5. Generate new transactions
        6. Record metrics
        """
        # Advance time
        self.current_time += self.timestep

        # Miners collect transactions
        for miner in self.miners:
            miner.collect_transactions(self.transaction_pool, self.timestep)

        # Coalitions aggregate transactions
        for coalition in self.coalitions:
            coalition.aggregate_transactions()

        # ECP updates membership graph and optimizes
        if self.ecp:
            self.ecp.update_membership_graph(self.coalitions)

            # Adjust pricing (every 10 timesteps to reduce overhead)
            if int(self.current_time) % 10 == 0:
                self.ecp.set_optimal_price(self.coalitions)

            # Coalitions request compute from ECP
            for coalition in self.coalitions:
                # Calculate optimal compute demand
                optimal_demand = coalition.calculate_optimal_compute_demand(
                    self.ecp.price_per_hash,
                    self.ecp.operating_cost_per_hash
                )

                # Request compute
                if optimal_demand > 0:
                    coalition.request_ecp_compute(self.ecp, optimal_demand)

            # Optimize overlapping work
            if len(self.ecp.compute_requests) > 0:
                self.ecp.optimize_overlapping_work(self.ecp.compute_requests)

            # Calculate ECP utility
            self.ecp.calculate_utility()

            # Reset ECP load for next timestep
            self.ecp.reset_load()

        # Attempt block discovery
        finding_coalition = self.attempt_block_discovery()
        if finding_coalition:
            self.handle_block_found(finding_coalition)

        # Generate new transactions
        self.generate_transactions()

        # Record metrics (every METRIC_RECORDING_INTERVAL seconds)
        if self.current_time - self.last_metric_time >= METRIC_RECORDING_INTERVAL:
            self.record_metrics()
            self.last_metric_time = self.current_time

    # ========================================================================
    # METRICS RECORDING
    # ========================================================================

    def record_metrics(self):
        """
        Log performance data for graphing.

        Records all key metrics for analysis.
        """
        # Calculate system utility
        ecp_utility = self.ecp.calculate_utility() if self.ecp else 0.0

        # Calculate total miner utilities
        miner_utilities = sum(miner.get_total_utility() for miner in self.miners)
        system_utility = ecp_utility + miner_utilities

        # Calculate total nonce length (compute purchased)
        total_nonce_length = self.ecp.get_total_demand() if self.ecp else 0.0

        # Calculate average coalition size
        active_coalitions = [c for c in self.coalitions if len(c.members) > 0]
        if len(active_coalitions) > 0:
            avg_coalition_size = sum(len(c.members) for c in active_coalitions) / len(active_coalitions)
        else:
            avg_coalition_size = 0.0

        # Network hashrate
        network_hashrate = self.get_total_network_hashrate()

        # Record all metrics
        self.metrics["time"].append(self.current_time)
        self.metrics["ecp_utility"].append(ecp_utility)
        self.metrics["system_utility"].append(system_utility)
        self.metrics["total_nonce_length"].append(total_nonce_length)
        self.metrics["avg_coalition_size"].append(avg_coalition_size)
        self.metrics["blocks_found"].append(self.blocks_found)
        self.metrics["network_hashrate"].append(network_hashrate)
        self.metrics["num_coalitions"].append(len(active_coalitions))
        self.metrics["num_transactions"].append(len(self.transaction_pool))

        self.metrics_recorded += 1

    # ========================================================================
    # UTILITY CALCULATIONS
    # ========================================================================

    def get_total_network_hashrate(self) -> float:
        """
        Calculate total hashrate across all coalitions.

        Returns:
            Total network hashrate (including ECP compute)
        """
        total_hashrate = 0.0
        for coalition in self.coalitions:
            total_hashrate += coalition.get_effective_hashrate()
        return total_hashrate

    def calculate_system_utility(self) -> float:
        """
        Calculate total system utility.

        Formula (from paper):
            u_system = u_ECP + sum_{n,m}(u_{n,m})

        Returns:
            Total system utility
        """
        # ECP utility
        ecp_utility = self.ecp.calculate_utility() if self.ecp else 0.0

        # Sum of all miner utilities
        miner_utilities = sum(miner.get_total_utility() for miner in self.miners)

        system_utility = ecp_utility + miner_utilities
        return system_utility

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about the simulation."""
        # Calculate final metrics
        ecp_utility = self.ecp.calculate_utility() if self.ecp else 0.0
        system_utility = self.calculate_system_utility()

        # Average coalition size
        active_coalitions = [c for c in self.coalitions if len(c.members) > 0]
        avg_coalition_size = sum(len(c.members) for c in active_coalitions) / len(active_coalitions) if len(active_coalitions) > 0 else 0

        # Miner statistics
        avg_miner_earnings = sum(m.total_earnings for m in self.miners) / len(self.miners) if len(self.miners) > 0 else 0

        return {
            "current_time": self.current_time,
            "blocks_found": self.blocks_found,
            "total_rewards_distributed": self.total_rewards_distributed,
            "ecp_utility": ecp_utility,
            "system_utility": system_utility,
            "avg_coalition_size": avg_coalition_size,
            "num_coalitions": len(active_coalitions),
            "network_hashrate": self.get_total_network_hashrate(),
            "avg_miner_earnings": avg_miner_earnings,
            "transactions_in_pool": len(self.transaction_pool),
            "ecp_price": self.ecp.price_per_hash if self.ecp else 0,
            "ecp_demand": self.ecp.get_total_demand() if self.ecp else 0,
            "metrics_recorded": self.metrics_recorded
        }

    def get_metrics_summary(self) -> Dict:
        """Get summary statistics of recorded metrics."""
        import numpy as np

        summary = {}

        for metric_name, values in self.metrics.items():
            if len(values) > 0 and metric_name != "time":
                summary[metric_name] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "final": values[-1] if len(values) > 0 else 0
                }

        return summary

    def get_coalition_statistics(self) -> List[Dict]:
        """Get statistics for each coalition."""
        stats = []
        for coalition in self.coalitions:
            stats.append(coalition.get_statistics())
        return stats

    def get_miner_statistics(self) -> List[Dict]:
        """Get statistics for each miner."""
        stats = []
        for miner in self.miners:
            stats.append(miner.get_statistics())
        return stats

    # ========================================================================
    # SIMULATION CONTROL
    # ========================================================================

    def reset(self):
        """Reset simulation to initial state."""
        self.current_time = 0.0
        self.blocks_found = 0
        self.total_rewards_distributed = 0.0
        self.blocks_by_coalition = {}
        self.metrics_recorded = 0
        self.last_metric_time = 0.0

        # Clear metrics
        for key in self.metrics:
            self.metrics[key] = []

        # Reset transaction pool
        self.transaction_pool = []
        self.transaction_counter = 0
        self._generate_initial_transactions()

        # Reset all entities
        for miner in self.miners:
            miner.total_earnings = 0.0
            miner.earnings_history = []
            miner.current_utility = 0.0
            miner.utility_history = []
            miner.transactions = []

        for coalition in self.coalitions:
            coalition.blocks_found = 0
            coalition.total_rewards = 0.0
            coalition.rewards_history = []
            coalition.ecp_compute_purchased = 0.0
            coalition.ecp_cost_paid = 0.0
            coalition.current_utility = 0.0
            coalition.utility_history = []
            coalition.transaction_pool = []

        if self.ecp:
            self.ecp.current_load = 0.0
            self.ecp.total_revenue = 0.0
            self.ecp.total_cost = 0.0
            self.ecp.revenue_history = []
            self.ecp.price_history = []
            self.ecp.current_utility = 0.0
            self.ecp.utility_history = []
            self.ecp.compute_requests = []
            self.ecp.total_demand = 0.0
            self.ecp.demand_history = []
            self.ecp.overlap_savings = 0.0
            self.ecp.optimization_count = 0
            self.ecp.price_per_hash = self.ecp.price_per_hash  # Keep current price

    def is_complete(self, total_simulation_time: float) -> bool:
        """
        Check if simulation is complete.

        Args:
            total_simulation_time: Target simulation duration

        Returns:
            True if simulation time reached target
        """
        return self.current_time >= total_simulation_time
