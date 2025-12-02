"""
Coalition entity - represents a group of miners working together.
"""

import random
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.miner import Miner, Transaction
    from entities.ecp import ECP

from simulation.config import (
    BLOCK_REWARD_B,
    TRANSACTIONS_PER_BLOCK_I,
    DEFINITION_4_ENABLED,
    SMART_CONTRACT_ENABLED,
    TRUST_OVERHEAD_FACTOR,
    THEFT_PROBABILITY,
    THEFT_AMOUNT
)


class Coalition:
    """
    Represents a coalition of miners working together to mine blocks.

    Properties:
        - coalition_id: Unique identifier
        - members: List of miner objects in this coalition
        - head_miner: The leader/coordinator of the coalition
        - total_hashrate: Sum of all members' contributed hashrate
        - transaction_pool: Aggregated transactions from all members
        - blocks_found: Count of blocks successfully mined
        - total_rewards: Cumulative rewards earned
        - ecp_compute_purchased: Compute purchased from ECP
    """

    def __init__(self, coalition_id: int, head_miner: Optional['Miner'] = None):
        """
        Initialize a coalition.

        Args:
            coalition_id: Unique identifier
            head_miner: Optional head miner (coordinator)
        """
        self.coalition_id = coalition_id
        self.head_miner = head_miner

        # Membership
        self.members: List['Miner'] = []
        if head_miner:
            self.members.append(head_miner)

        # Transaction aggregation
        self.transaction_pool: List['Transaction'] = []

        # Mining statistics
        self.blocks_found = 0
        self.total_rewards = 0.0
        self.rewards_history = []

        # ECP compute
        self.ecp_compute_purchased = 0.0
        self.ecp_cost_paid = 0.0

        # Expected rewards (used for utility calculations)
        self.expected_rewards = BLOCK_REWARD_B

        # Utility tracking
        self.current_utility = 0.0
        self.utility_history = []

    def __repr__(self):
        return f"Coalition(id={self.coalition_id}, members={len(self.members)}, blocks={self.blocks_found})"

    def __hash__(self):
        return hash(self.coalition_id)

    def __eq__(self, other):
        if not isinstance(other, Coalition):
            return False
        return self.coalition_id == other.coalition_id

    # ========================================================================
    # MEMBERSHIP MANAGEMENT
    # ========================================================================

    def add_member(self, miner: 'Miner') -> bool:
        """
        Add a miner to the coalition.

        Args:
            miner: Miner to add

        Returns:
            True if successfully added, False otherwise
        """
        if miner in self.members:
            return False

        # Check Definition 4 if enabled
        if DEFINITION_4_ENABLED and len(self.members) > 0:
            if not self.check_definition_4(miner):
                return False

        self.members.append(miner)

        # Set as head if no head exists
        if self.head_miner is None:
            self.head_miner = miner

        return True

    def remove_member(self, miner: 'Miner') -> bool:
        """
        Remove a miner from the coalition.

        Args:
            miner: Miner to remove

        Returns:
            True if successfully removed, False otherwise
        """
        if miner not in self.members:
            return False

        self.members.remove(miner)

        # Elect new head if needed
        if self.head_miner == miner:
            self.head_miner = self.members[0] if len(self.members) > 0 else None

        return True

    def check_definition_4(self, new_miner: 'Miner') -> bool:
        """
        Verify that adding a new miner doesn't hurt existing members' utility.

        Definition 4 (from paper):
            Miner n can join coalition m if and only if:
            ∀i ∈ C_m: u'_{i,m} >= u_{i,m}

        Where:
            - u_{i,m} = current utility of member i in coalition m
            - u'_{i,m} = projected utility of member i after n joins

        Args:
            new_miner: Miner attempting to join

        Returns:
            True if joining satisfies Definition 4, False otherwise
        """
        if len(self.members) == 0:
            return True  # First member always allowed

        # Calculate current total work
        current_total_work = self.get_total_work()

        if current_total_work == 0:
            return True  # No work yet, allow joining

        # Calculate projected total work with new miner
        new_miner_work = new_miner.get_potential_work_contribution(self)
        projected_total_work = current_total_work + new_miner_work

        if projected_total_work == 0:
            return False  # Would result in zero work

        # Check each existing member's utility
        for member in self.members:
            member_work = member.get_work_contribution(self)

            # Current share
            current_share = member_work / current_total_work

            # Projected share after new miner joins
            projected_share = member_work / projected_total_work

            # Current utility (proportional to share)
            current_utility = current_share * self.expected_rewards

            # Projected utility
            # Note: More members may increase transaction pool quality
            # We assume expected_rewards stays constant or improves slightly
            projected_utility = projected_share * self.expected_rewards

            # Check if projected utility is worse
            epsilon = 1e-6  # Small tolerance for floating point
            if projected_utility < current_utility - epsilon:
                return False

        return True

    # ========================================================================
    # TRANSACTION AGGREGATION
    # ========================================================================

    def aggregate_transactions(self):
        """
        Combine transactions from all members.

        Creates union of all transactions collected by members.
        """
        # Clear current pool
        self.transaction_pool = []

        # Aggregate from all members
        seen_tx_ids = set()
        for member in self.members:
            for tx in member.get_transactions():
                if tx.tx_id not in seen_tx_ids:
                    self.transaction_pool.append(tx)
                    seen_tx_ids.add(tx.tx_id)

    def select_transactions_for_block(self, max_transactions: int = TRANSACTIONS_PER_BLOCK_I) -> List['Transaction']:
        """
        Select best transactions for a block.

        Uses greedy strategy: select transactions with highest fees.

        Args:
            max_transactions: Maximum number of transactions to include

        Returns:
            List of selected transactions
        """
        # Sort by fee (descending)
        sorted_tx = sorted(self.transaction_pool, key=lambda tx: tx.fee, reverse=True)

        # Take top transactions
        selected = sorted_tx[:max_transactions]

        return selected

    # ========================================================================
    # REWARD DISTRIBUTION
    # ========================================================================

    def distribute_rewards(self, block_reward: float, ecp_price: float):
        """
        Split rewards among members proportionally.

        Uses proportional share based on work contributed.
        Accounts for smart contract vs trust-based distribution.
        Also updates each miner's utility.

        Args:
            block_reward: Total reward to distribute (B + transaction_fees)
            ecp_price: Current ECP price (for calculating costs)
        """
        from simulation.utils import calculate_miner_utility

        total_work = self.get_total_work()

        if total_work == 0:
            return  # No work done, no distribution

        # Calculate net reward after ECP costs
        ecp_cost = ecp_price * self.ecp_compute_purchased
        net_reward = block_reward - ecp_cost

        # Apply smart contract vs trust-based distribution
        if not SMART_CONTRACT_ENABLED:
            # Trust overhead: members perceive reduced utility
            net_reward *= (1.0 - TRUST_OVERHEAD_FACTOR)

            # Coalition head theft risk
            if random.random() < THEFT_PROBABILITY:
                # Head steals some rewards
                net_reward *= (1.0 - THEFT_AMOUNT)

        if net_reward <= 0:
            return  # No reward to distribute

        # Distribute proportionally and update utility
        total_utility_from_this_block = 0
        for member in self.members:
            member_work = member.get_work_contribution(self)
            share = member_work / total_work if total_work > 0 else 0
            member_reward = share * net_reward

            # Record monetary reward
            member.receive_reward(member_reward)

            # Calculate and update utility for the member from this block's reward
            utility = calculate_miner_utility(member, self, net_reward, ecp_price, self.ecp_compute_purchased)
            member.update_utility(utility)
            total_utility_from_this_block += utility

        # Record coalition totals
        self.total_rewards += block_reward
        self.rewards_history.append(block_reward)
        self.ecp_cost_paid += ecp_cost
        self.current_utility = total_utility_from_this_block
        self.utility_history.append(self.current_utility)

    # ========================================================================
    # ECP COMPUTE MANAGEMENT
    # ========================================================================

    def request_ecp_compute(self, ecp: 'ECP', nonce_range: float):
        """
        Purchase computing power from ECP.

        Args:
            ecp: ECP object to purchase from
            nonce_range: Amount of compute to purchase
        """
        # Request allocation from ECP
        allocated = ecp.allocate_compute(self, nonce_range)

        # Record allocated compute
        self.ecp_compute_purchased = allocated

    def calculate_optimal_compute_demand(self, price: float, cost: float) -> float:
        """
        Calculate optimal compute to purchase from ECP.

        This heuristic now makes demand inversely proportional to coalition size,
        assuming larger coalitions are more self-sufficient.

        Args:
            price: Current ECP price
            cost: ECP operating cost

        Returns:
            Optimal compute amount to purchase
        """
        if price > self.expected_rewards * 0.5:
            return 0.0

        member_hashrate = self.get_total_work()
        if member_hashrate == 0:
            return 0.0

        # Heuristic: Demand is inversely proportional to the number of members.
        # Larger coalitions are assumed to be more self-sufficient.
        # The base demand is 50% of member hashrate, scaled down by num_members.
        num_members = self.get_size()
        demand_factor = 0.5 / (1 + (num_members - 1) * 0.1) # Diminishing demand with size
        optimal_compute = member_hashrate * demand_factor

        # Simple profitability check
        expected_cost = optimal_compute * price
        expected_benefit = self.expected_rewards * 0.2

        if expected_cost > expected_benefit:
            optimal_compute = (expected_benefit / price) if price > 0 else 0

        return max(0.0, optimal_compute)

    # ========================================================================
    # UTILITY CALCULATIONS
    # ========================================================================

    def calculate_member_utility(self, miner: 'Miner', rewards: float,
                                 ecp_price: float) -> float:
        """
        Calculate utility for a specific member.

        Formula (from paper):
            u_{n,m} = (w_{n,m} / W_m) × (R_m - p × l_m)

        Args:
            miner: Miner to calculate utility for
            rewards: Total rewards earned (R_m)
            ecp_price: Current ECP price (p)

        Returns:
            Utility value for the miner
        """
        total_work = self.get_total_work()

        if total_work == 0:
            return 0.0

        # Miner's work contribution
        member_work = miner.get_work_contribution(self)

        # Share of rewards
        share = member_work / total_work

        # Net reward after ECP costs
        net_reward = rewards - (ecp_price * self.ecp_compute_purchased)

        # Miner's utility
        utility = share * net_reward

        return max(0.0, utility)

    def get_expected_member_utility(self, miner: 'Miner') -> float:
        """
        Get expected utility for a member.

        Uses expected rewards rather than actual rewards.

        Args:
            miner: Miner to calculate expected utility for

        Returns:
            Expected utility value
        """
        total_work = self.get_total_work()

        if total_work == 0:
            return 0.0

        member_work = miner.get_work_contribution(self)
        share = member_work / total_work

        # Use expected rewards
        expected_utility = share * self.expected_rewards

        return max(0.0, expected_utility)

    def get_expected_utility_with_compute(self, compute: float, price: float,
                                         total_network_hashrate: float) -> float:
        """
        Calculate expected utility with a given amount of ECP compute.

        Used for optimization of compute purchase.

        Args:
            compute: Amount of compute to purchase
            price: ECP price
            total_network_hashrate: Total network hashrate

        Returns:
            Expected coalition utility
        """
        # Effective hashrate with this compute
        member_hashrate = self.get_total_work()
        effective_hashrate = member_hashrate + compute

        if total_network_hashrate == 0:
            return 0.0

        # Expected probability of finding a block
        # Simplified: proportional to hashrate share
        hashrate_share = effective_hashrate / (total_network_hashrate + compute)

        # Expected rewards
        expected_rewards = hashrate_share * self.expected_rewards

        # Cost
        cost = price * compute

        # Utility
        utility = expected_rewards - cost

        return max(0.0, utility)

    # ========================================================================
    # WORK AND HASHRATE CALCULATIONS
    # ========================================================================

    def get_total_work(self) -> float:
        """
        Calculate total work contributed by all members.

        Returns:
            Total effective hashrate from all members
        """
        total_work = 0.0
        for member in self.members:
            total_work += member.get_work_contribution(self)
        return total_work

    def get_effective_hashrate(self) -> float:
        """
        Get effective hashrate including ECP compute.

        Returns:
            Total hashrate (members + ECP)
        """
        member_hashrate = self.get_total_work()
        return member_hashrate + self.ecp_compute_purchased

    def get_expected_rewards(self) -> float:
        """
        Get expected rewards for this coalition.

        Returns:
            Expected reward value
        """
        return self.expected_rewards

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_statistics(self) -> Dict:
        """Get statistics about this coalition."""
        return {
            "coalition_id": self.coalition_id,
            "num_members": len(self.members),
            "total_hashrate": self.get_effective_hashrate(),
            "blocks_found": self.blocks_found,
            "total_rewards": self.total_rewards,
            "average_reward": self.total_rewards / self.blocks_found if self.blocks_found > 0 else 0,
            "ecp_compute": self.ecp_compute_purchased,
            "ecp_cost": self.ecp_cost_paid,
            "transaction_pool_size": len(self.transaction_pool)
        }

    def get_member_ids(self) -> List[int]:
        """Get list of member IDs."""
        return [m.miner_id for m in self.members]

    def has_member(self, miner: 'Miner') -> bool:
        """Check if miner is a member."""
        return miner in self.members

    def get_size(self) -> int:
        """Get number of members."""
        return len(self.members)
