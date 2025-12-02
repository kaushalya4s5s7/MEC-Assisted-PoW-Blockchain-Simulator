"""
ECP (Edge Computing Provider) entity - provides computing power to coalitions.
"""

import random
from typing import List, Dict, Set, Optional, Tuple, TYPE_CHECKING
from itertools import combinations

if TYPE_CHECKING:
    from entities.coalition import Coalition
    from entities.miner import Miner

from simulation.config import (
    ECP_MAX_CAPACITY_L,
    ECP_OPERATING_COST_C,
    ECP_INITIAL_PRICE,
    ECP_PRICE_MIN,
    ECP_PRICE_MAX,
    OVERLAP_THRESHOLD,
    OVERLAP_SAVINGS_FACTOR,
    ECP_OPTIMIZATION_ENABLED,
    STACKELBERG_LEARNING_RATE,
    STACKELBERG_MAX_ITERATIONS,
    STACKELBERG_CONVERGENCE_THRESHOLD,
    STACKELBERG_STEP_DECAY
)


class ComputeRequest:
    """Represents a compute request from a coalition."""

    def __init__(self, coalition: 'Coalition', nonce_range: float):
        self.coalition = coalition
        self.nonce_range = nonce_range
        self.allocated = 0.0

    def __repr__(self):
        return f"Request(coalition={self.coalition.coalition_id}, nonce={self.nonce_range})"


class ECP:
    """
    Represents the Edge Computing Provider (ECP).

    The ECP rents computing power to coalitions using a Stackelberg game model.

    Properties:
        - total_capacity: Maximum computing power available
        - current_load: Currently utilized capacity
        - price_per_hash: Current price for computing services
        - operating_cost_per_hash: Cost to ECP for providing services
        - total_revenue: Cumulative earnings
        - membership_graph: Dictionary tracking which miners belong to which coalitions
        - compute_requests: Current compute requests from coalitions
    """

    def __init__(self):
        """Initialize the ECP."""
        # Capacity
        self.total_capacity = ECP_MAX_CAPACITY_L
        self.current_load = 0.0

        # Pricing
        self.price_per_hash = ECP_INITIAL_PRICE
        self.operating_cost_per_hash = ECP_OPERATING_COST_C

        # Financial tracking
        self.total_revenue = 0.0
        self.total_cost = 0.0
        self.revenue_history = []
        self.price_history = []

        # Utility tracking
        self.current_utility = 0.0
        self.utility_history = []

        # Request management
        self.compute_requests: List[ComputeRequest] = []
        self.total_demand = 0.0  # Cumulative demand across all timesteps
        self.current_demand = 0.0  # Instantaneous demand for this timestep
        self.demand_history = []

        # Membership tracking (for overlap optimization)
        self.membership_graph: Dict[int, Set[int]] = {}  # coalition_id -> set of miner_ids

        # Optimization statistics
        self.overlap_savings = 0.0
        self.optimization_count = 0

    def __repr__(self):
        return f"ECP(price={self.price_per_hash:.6f}, load={self.current_load/1e9:.2f}GH/s, revenue={self.total_revenue:.2f})"

    # ========================================================================
    # PRICING (STACKELBERG GAME)
    # ========================================================================

    def set_optimal_price(self, coalitions: List['Coalition']):
        """
        Adjust price based on demand using Stackelberg game logic.

        The ECP solves:
            max_p [u_ECP(p)] = max_p [(p - c) × sum_m(l_m(p))]

        Uses gradient ascent to find optimal price.

        Args:
            coalitions: List of coalitions (demand side)
        """
        if len(coalitions) == 0:
            return

        current_price = self.price_per_hash
        learning_rate = STACKELBERG_LEARNING_RATE
        epsilon = 0.01  # Small value for numerical gradient

        for iteration in range(STACKELBERG_MAX_ITERATIONS):
            # Calculate current utility
            current_utility = self._calculate_utility_at_price(coalitions, current_price)

            # Calculate utility at slightly higher price
            utility_plus = self._calculate_utility_at_price(coalitions, current_price + epsilon)

            # Numerical gradient
            gradient = (utility_plus - current_utility) / epsilon

            # Check convergence
            if abs(gradient) < STACKELBERG_CONVERGENCE_THRESHOLD:
                break

            # Gradient ascent step
            current_price = current_price + learning_rate * gradient

            # Clamp to reasonable range
            current_price = max(ECP_PRICE_MIN, min(ECP_PRICE_MAX, current_price))

            # Decay learning rate
            learning_rate *= STACKELBERG_STEP_DECAY

        # Update price
        self.price_per_hash = current_price
        self.price_history.append(current_price)

    def _calculate_utility_at_price(self, coalitions: List['Coalition'], price: float) -> float:
        """
        Calculate ECP utility at a specific price point.

        Simulates coalition demand at the given price.

        Args:
            coalitions: List of coalitions
            price: Price to evaluate

        Returns:
            ECP utility at this price
        """
        # Simulate demand at this price
        total_demand = 0.0
        for coalition in coalitions:
            demand = coalition.calculate_optimal_compute_demand(price, self.operating_cost_per_hash)
            total_demand += demand

        # Cap at capacity
        total_demand = min(total_demand, self.total_capacity)

        # Utility = (price - cost) × demand
        utility = (price - self.operating_cost_per_hash) * total_demand
        return max(0.0, utility)

    # ========================================================================
    # COMPUTE ALLOCATION
    # ========================================================================

    def allocate_compute(self, coalition: 'Coalition', nonce_range: float) -> float:
        """
        Assign GPU resources to a request.

        Args:
            coalition: Coalition requesting compute
            nonce_range: Amount of compute requested

        Returns:
            Amount of compute actually allocated
        """
        # Create compute request
        request = ComputeRequest(coalition, nonce_range)
        self.compute_requests.append(request)

        # Check capacity
        available_capacity = self.total_capacity - self.current_load

        if available_capacity <= 0:
            return 0.0  # No capacity available

        # Allocate up to available capacity
        allocated = min(nonce_range, available_capacity)
        request.allocated = allocated

        # Update load
        self.current_load += allocated

        # Update demand tracking (both cumulative and instantaneous)
        self.total_demand += allocated  # Cumulative
        self.current_demand += allocated  # This timestep only
        self.demand_history.append(allocated)

        # Record revenue
        revenue = allocated * self.price_per_hash
        self.total_revenue += revenue
        self.revenue_history.append(revenue)

        # Record cost
        cost = allocated * self.operating_cost_per_hash
        self.total_cost += cost

        return allocated

    def reset_load(self):
        """Reset current load (called at end of each timestep)."""
        self.current_load = 0.0
        self.compute_requests = []
        self.current_demand = 0.0  # Reset instantaneous demand, NOT total_demand

    # ========================================================================
    # OVERLAP OPTIMIZATION (INNOVATION 3)
    # ========================================================================

    def update_membership_graph(self, coalitions: List['Coalition']):
        """
        Update membership graph with current coalition memberships.

        Args:
            coalitions: List of all coalitions
        """
        self.membership_graph = {}
        for coalition in coalitions:
            miner_ids = set(m.miner_id for m in coalition.members)
            self.membership_graph[coalition.coalition_id] = miner_ids

    def optimize_overlapping_work(self, requests: List[ComputeRequest]) -> float:
        """
        Detect and optimize when coalitions share members.

        When coalitions have overlapping membership, the ECP can coordinate
        their work to avoid duplicate computation, reducing operating costs.

        Args:
            requests: List of compute requests

        Returns:
            Total cost savings from optimization
        """
        if not ECP_OPTIMIZATION_ENABLED:
            return 0.0

        if len(requests) < 2:
            return 0.0  # Need at least 2 requests to optimize

        total_savings = 0.0

        # Find pairs with significant overlap
        for req1, req2 in combinations(requests, 2):
            overlap_ratio = self.calculate_overlap_ratio(req1.coalition, req2.coalition)

            if overlap_ratio >= OVERLAP_THRESHOLD:
                # Calculate savings from coordinating work
                savings = self.calculate_overlap_savings(req1, req2, overlap_ratio)
                total_savings += savings

        self.overlap_savings += total_savings
        self.optimization_count += 1

        return total_savings

    def calculate_overlap_ratio(self, coalition1: 'Coalition', coalition2: 'Coalition') -> float:
        """
        Calculate membership overlap between two coalitions.

        Args:
            coalition1: First coalition
            coalition2: Second coalition

        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        # Get member sets
        members1 = self.membership_graph.get(coalition1.coalition_id, set())
        members2 = self.membership_graph.get(coalition2.coalition_id, set())

        if len(members1) == 0 or len(members2) == 0:
            return 0.0

        # Calculate overlap
        shared_members = members1 & members2
        total_members = max(len(members1), len(members2))

        overlap_ratio = len(shared_members) / total_members

        return overlap_ratio

    def calculate_overlap_savings(self, req1: ComputeRequest, req2: ComputeRequest,
                                  overlap_ratio: float) -> float:
        """
        Quantify cost reduction from coordination.

        When coalitions share members, the ECP can eliminate duplicate work
        by coordinating nonce ranges.

        Args:
            req1: First compute request
            req2: Second compute request
            overlap_ratio: Overlap ratio between coalitions

        Returns:
            Cost savings
        """
        # Calculate potential duplicate work
        duplicate_work = min(req1.nonce_range, req2.nonce_range) * overlap_ratio

        # Calculate savings (cost of duplicate work eliminated)
        savings = duplicate_work * self.operating_cost_per_hash * OVERLAP_SAVINGS_FACTOR

        return savings

    # ========================================================================
    # UTILITY CALCULATION
    # ========================================================================

    def calculate_utility(self) -> float:
        """
        Calculate total utility (profit) for the ECP.

        Formula (from paper):
            u_ECP = sum_m(p × l_m) - sum_m(c × l_m)
            u_ECP = (p - c) × sum_m(l_m)

        Returns:
            ECP utility (profit)
        """
        profit_per_unit = self.price_per_hash - self.operating_cost_per_hash

        # Apply overlap savings to reduce costs
        adjusted_cost = self.operating_cost_per_hash
        if ECP_OPTIMIZATION_ENABLED and self.overlap_savings > 0:
            # Reduce effective cost based on optimization
            cost_reduction = self.overlap_savings / self.total_demand if self.total_demand > 0 else 0
            adjusted_cost = max(0, self.operating_cost_per_hash - cost_reduction)

        adjusted_profit_per_unit = self.price_per_hash - adjusted_cost
        utility = adjusted_profit_per_unit * self.total_demand

        self.current_utility = max(0.0, utility)
        self.utility_history.append(self.current_utility)

        return self.current_utility

    def get_total_demand(self) -> float:
        """
        Get total compute demand from all coalitions.

        Returns:
            Total demand
        """
        return self.total_demand

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_statistics(self) -> Dict:
        """Get statistics about the ECP."""
        return {
            "price_per_hash": self.price_per_hash,
            "current_load": self.current_load,
            "capacity_utilization": self.current_load / self.total_capacity if self.total_capacity > 0 else 0,
            "total_revenue": self.total_revenue,
            "total_cost": self.total_cost,
            "total_profit": self.total_revenue - self.total_cost,
            "current_utility": self.current_utility,
            "total_demand": self.total_demand,
            "num_requests": len(self.compute_requests),
            "overlap_savings": self.overlap_savings,
            "optimization_count": self.optimization_count
        }

    def get_average_price(self) -> float:
        """Get average price over history."""
        if len(self.price_history) == 0:
            return self.price_per_hash
        return sum(self.price_history) / len(self.price_history)

    def get_average_demand(self) -> float:
        """Get average demand over history."""
        if len(self.demand_history) == 0:
            return 0.0
        return sum(self.demand_history) / len(self.demand_history)

    def get_capacity_utilization(self) -> float:
        """Get current capacity utilization percentage."""
        if self.total_capacity == 0:
            return 0.0
        return (self.current_load / self.total_capacity) * 100.0
