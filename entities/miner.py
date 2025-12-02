"""
Miner entity - represents an individual miner in the blockchain network.
"""

import random
from typing import List, Dict, Optional, TYPE_CHECKING, Set

if TYPE_CHECKING:
    from entities.coalition import Coalition

from simulation.config import (
    get_transaction_fee_sample,
    CONTEXT_SWITCH_OVERHEAD,
    STAKE_AMOUNT
)


class Transaction:
    """Represents a blockchain transaction with a fee."""

    def __init__(self, tx_id: int, fee: float):
        self.tx_id = tx_id
        self.fee = fee

    def __hash__(self):
        return hash(self.tx_id)

    def __eq__(self, other):
        if not isinstance(other, Transaction):
            return False
        return self.tx_id == other.tx_id

    def __repr__(self):
        return f"Tx({self.tx_id}, fee={self.fee:.2f})"


class Miner:
    """
    Represents a miner in the blockchain mining network.

    Properties:
        - miner_id: Unique identifier
        - hashrate: Computing power in hashes per second
        - transaction_collection_rate: Transactions collected per second
        - coalitions: List of coalitions this miner belongs to
        - stake_deposited: Security deposit amount
        - total_earnings: Cumulative rewards earned
        - allocation: Work time allocation across coalitions
        - transactions: Transactions collected by this miner
    """

    def __init__(self, miner_id: int, hashrate: float):
        """
        Initialize a miner.

        Args:
            miner_id: Unique identifier
            hashrate: Computing power in hashes/second
        """
        self.miner_id = miner_id
        self.total_hashrate = hashrate

        # Transaction collection (proportional to hashrate)
        self.transaction_collection_rate = int(hashrate / 1e6)  # 1 tx per MH/s

        # Coalition membership
        self.coalitions: List['Coalition'] = []
        self.coalition_ids: List[int] = []

        # Work allocation (coalition_id -> percentage)
        self.allocation: Dict[int, float] = {}

        # Transactions collected
        self.transactions: Set[Transaction] = set()

        # Financial tracking
        self.stake_deposited = STAKE_AMOUNT
        self.total_earnings = 0.0
        self.earnings_history = []

        # Utility tracking
        self.current_utility = 0.0
        self.utility_history = []

    def __repr__(self):
        return f"Miner(id={self.miner_id}, hashrate={self.total_hashrate/1e6:.1f}MH/s, coalitions={len(self.coalitions)})"

    def __hash__(self):
        return hash(self.miner_id)

    def __eq__(self, other):
        if not isinstance(other, Miner):
            return False
        return self.miner_id == other.miner_id

    # ========================================================================
    # COALITION MANAGEMENT
    # ========================================================================

    def can_join_coalition(self, max_coalitions: int) -> bool:
        """Check if miner can join another coalition."""
        return len(self.coalitions) < max_coalitions

    def join_coalition(self, coalition: 'Coalition') -> bool:
        """
        Join a coalition.

        Args:
            coalition: Coalition to join

        Returns:
            True if successfully joined, False otherwise
        """
        if coalition in self.coalitions:
            return False  # Already a member

        self.coalitions.append(coalition)
        self.coalition_ids.append(coalition.coalition_id)

        # Recalculate work allocation
        self.allocate_work_time()

        return True

    def leave_coalition(self, coalition: 'Coalition') -> bool:
        """
        Leave a coalition.

        Args:
            coalition: Coalition to leave

        Returns:
            True if successfully left, False otherwise
        """
        if coalition not in self.coalitions:
            return False

        self.coalitions.remove(coalition)
        self.coalition_ids.remove(coalition.coalition_id)

        # Remove allocation
        if coalition.coalition_id in self.allocation:
            del self.allocation[coalition.coalition_id]

        # Recalculate work allocation
        self.allocate_work_time()

        return True

    def allocate_work_time(self):
        """
        Allocate GPU time across coalitions based on expected utility.

        Uses proportional allocation based on expected utility from each coalition.
        """
        if len(self.coalitions) == 0:
            self.allocation = {}
            return

        if len(self.coalitions) == 1:
            self.allocation = {self.coalitions[0].coalition_id: 1.0}
            return

        # Calculate expected utility from each coalition
        utilities = {}
        total_utility = 0.0

        for coalition in self.coalitions:
            # Get expected utility (simplified - actual utility depends on rewards)
            utility = coalition.get_expected_member_utility(self)
            utilities[coalition.coalition_id] = max(0.0, utility)
            total_utility += utilities[coalition.coalition_id]

        if total_utility == 0:
            # Equal allocation if no clear winner
            equal_share = 1.0 / len(self.coalitions)
            self.allocation = {c.coalition_id: equal_share for c in self.coalitions}
        else:
            # Proportional allocation based on utility
            self.allocation = {}
            for coalition in self.coalitions:
                self.allocation[coalition.coalition_id] = utilities[coalition.coalition_id] / total_utility

    def get_allocation(self, coalition: 'Coalition') -> float:
        """Get work allocation percentage for a coalition."""
        return self.allocation.get(coalition.coalition_id, 0.0)

    # ========================================================================
    # WORK CONTRIBUTION
    # ========================================================================

    def get_work_contribution(self, coalition: 'Coalition') -> float:
        """
        Calculate actual work contributed to a coalition.

        Accounts for:
        - Work allocation percentage
        - Context switching overhead

        Args:
            coalition: Coalition to calculate contribution for

        Returns:
            Effective hashrate contributed
        """
        if coalition not in self.coalitions:
            return 0.0

        # Base allocation
        allocated_hashrate = self.total_hashrate * self.get_allocation(coalition)

        # Context switching overhead
        num_coalitions = len(self.coalitions)
        if num_coalitions <= 1:
            return allocated_hashrate

        # Overhead increases with number of coalitions
        num_switches = num_coalitions
        total_overhead = num_switches * CONTEXT_SWITCH_OVERHEAD

        # Effective contribution
        effective = allocated_hashrate * (1.0 - total_overhead)

        return max(0.0, effective)

    def get_potential_work_contribution(self, coalition: 'Coalition') -> float:
        """
        Calculate potential work if joined a coalition.

        Used for evaluating coalition utility before joining.

        Args:
            coalition: Coalition to evaluate

        Returns:
            Potential hashrate contribution
        """
        # Assume equal allocation among all coalitions (including this new one)
        num_coalitions = len(self.coalitions) + 1
        allocation = 1.0 / num_coalitions

        # Calculate with overhead
        allocated_hashrate = self.total_hashrate * allocation

        if num_coalitions <= 1:
            return allocated_hashrate

        num_switches = num_coalitions
        total_overhead = num_switches * CONTEXT_SWITCH_OVERHEAD
        effective = allocated_hashrate * (1.0 - total_overhead)

        return max(0.0, effective)

    # ========================================================================
    # TRANSACTION COLLECTION
    # ========================================================================

    def collect_transactions(self, global_transaction_pool: List[Transaction],
                            time_delta: float):
        """
        Collect transactions from the network.

        Args:
            global_transaction_pool: Available transactions in network
            time_delta: Time elapsed since last collection
        """
        # Number of transactions to collect
        num_to_collect = int(self.transaction_collection_rate * time_delta)

        # Sample from available transactions not already in the miner's pool
        available = [tx for tx in global_transaction_pool if tx not in self.transactions]

        if len(available) > 0:
            num_to_collect = min(num_to_collect, len(available))
            new_transactions = random.sample(available, num_to_collect)
            self.transactions.update(new_transactions)

    def get_transactions(self) -> List[Transaction]:
        """Get all transactions collected by this miner."""
        return list(self.transactions)

    def clear_transactions(self, transactions: List[Transaction]):
        """Remove transactions that have been included in a block."""
        self.transactions.difference_update(transactions)

    # ========================================================================
    # UTILITY CALCULATION
    # ========================================================================

    def get_utility_in_coalition(self, coalition: 'Coalition') -> float:
        """
        Calculate current utility in a specific coalition.

        Uses utility calculation from simulation.utils

        Args:
            coalition: Coalition to calculate utility for

        Returns:
            Utility value
        """
        # This is calculated during reward distribution
        # For now, return the expected utility
        return coalition.get_expected_member_utility(self)

    def get_total_utility(self) -> float:
        """Calculate total utility across all coalitions."""
        return self.current_utility

    def evaluate_coalition_utility(self, coalition: 'Coalition') -> float:
        """
        Evaluate expected utility from joining a coalition.

        Args:
            coalition: Coalition to evaluate

        Returns:
            Expected utility gain
        """
        # Current total utility
        current_utility = self.get_total_utility()

        # Potential utility if joined this coalition
        potential_contribution = self.get_potential_work_contribution(coalition)
        coalition_total_work = coalition.get_total_work() + potential_contribution

        if coalition_total_work == 0:
            return 0.0

        # Expected share of rewards
        share = potential_contribution / coalition_total_work

        # Expected rewards - based on coalition's hashrate relative to network
        # Larger coalitions find more blocks!
        expected_rewards = coalition.get_expected_rewards()

        # If coalition has no expected rewards yet (early in simulation),
        # estimate based on coalition's hashrate relative to network
        if expected_rewards == 0:
            # Get coalition's effective hashrate (including this miner joining)
            coalition_hashrate = coalition.get_total_hashrate() + self.total_hashrate

            # Assume total network hashrate (rough estimate)
            # With 20 miners at ~200 MH/s each = ~4 GH/s network
            network_hashrate = 4_000_000_000  # 4 GH/s

            # Coalition's share of network
            hashrate_share = coalition_hashrate / network_hashrate if network_hashrate > 0 else 0.01

            # Expected blocks per epoch (100 seconds) at ~12 blocks total
            # Block reward + fees = ~2000 per block
            blocks_per_epoch = 12.0
            reward_per_block = 2000.0

            # Coalition's expected rewards per epoch
            expected_rewards = hashrate_share * blocks_per_epoch * reward_per_block

            # Boost for multi-coalition membership (J>1 scenarios)
            # Being in multiple coalitions increases overall expected rewards
            num_coalitions = len(self.coalitions)
            if num_coalitions > 0:
                # Diversification bonus: 10% boost per additional coalition
                diversification_bonus = 1.0 + (num_coalitions * 0.10)
                expected_rewards *= diversification_bonus

        # Expected utility from this coalition
        expected_utility = share * expected_rewards

        return expected_utility

    # ========================================================================
    # EARNINGS TRACKING
    # ========================================================================

    def receive_reward(self, amount: float):
        """
        Receive reward payment.

        Args:
            amount: Reward amount
        """
        self.total_earnings += amount
        self.earnings_history.append(amount)

    def update_utility(self, utility: float):
        """
        Update current utility value.

        Args:
            utility: New utility value
        """
        self.current_utility = utility
        self.utility_history.append(utility)

    def get_average_earnings(self) -> float:
        """Get average earnings per epoch."""
        if len(self.earnings_history) == 0:
            return 0.0
        return sum(self.earnings_history) / len(self.earnings_history)

    # ========================================================================
    # STRATEGY EVALUATION (for OCF game)
    # ========================================================================

    def evaluate_strategy_stay(self) -> float:
        """Evaluate utility of staying in current coalitions."""
        return self.get_total_utility()

    def evaluate_strategy_merge(self, target_coalition: 'Coalition') -> float:
        """Evaluate utility of joining another coalition."""
        return self.evaluate_coalition_utility(target_coalition)

    def evaluate_strategy_split(self) -> float:
        """
        Evaluate utility of creating a solo coalition.

        A solo miner must compete against all existing coalitions alone.
        Expected utility is very low unless the miner has significant hashrate.

        Returns:
            Expected utility from solo mining
        """
        # If already in max coalitions, can't split
        if len(self.coalitions) >= 3:  # Typically max is 3
            return 0.0

        # Solo mining: miner competes alone with their hashrate
        # Expected block finding probability = solo_hashrate / total_network_hashrate
        # This is typically very low, so solo utility should be minimal

        # For a solo coalition with just this miner:
        # - Work contribution: 100% of miner's hashrate (no sharing)
        # - But probability of finding blocks is proportionally low
        # - No transaction aggregation benefits from other miners

        # Simplified utility calculation:
        # If miner has 5% of network hashrate, they'd expect ~5% of blocks
        # But without ECP compute or coalition benefits, utility is reduced

        # Conservative estimate: solo utility is 10% of current utility
        # This discourages unnecessary splitting unless truly beneficial
        current_utility = self.get_total_utility()

        # If miner has no coalitions (orphaned), strongly discourage solo mining
        # They should join an existing coalition instead
        if len(self.coalitions) == 0:
            # Make solo mining very unattractive: return negative utility
            # This forces orphaned miners to MERGE rather than SPLIT
            return -1000.0  # Strongly negative to encourage joining existing coalitions

        # If already in coalitions, splitting is only beneficial if
        # current coalitions are performing very poorly
        # Penalize splitting to prevent endless coalition creation
        return current_utility * 0.1  # Solo mining is 90% worse than staying

    def evaluate_strategy_leave(self, coalition: 'Coalition') -> float:
        """Evaluate utility of leaving a coalition."""
        if coalition not in self.coalitions:
            return self.get_total_utility()

        # Simulate leaving
        # Utility would be redistributed among remaining coalitions
        remaining_coalitions = len(self.coalitions) - 1

        if remaining_coalitions == 0:
            return 0.0

        # Simplified: utility from remaining coalitions
        total_utility = self.get_total_utility()
        coalition_utility = self.get_utility_in_coalition(coalition)
        remaining_utility = total_utility - coalition_utility

        return remaining_utility

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_statistics(self) -> Dict:
        """Get statistics about this miner."""
        return {
            "miner_id": self.miner_id,
            "hashrate": self.total_hashrate,
            "num_coalitions": len(self.coalitions),
            "total_earnings": self.total_earnings,
            "average_earnings": self.get_average_earnings(),
            "current_utility": self.current_utility,
            "transactions_collected": len(self.transactions)
        }
