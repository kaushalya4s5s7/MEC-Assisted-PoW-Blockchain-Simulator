"""
Utility calculation functions implementing mathematical formulas from the paper.
"""

import math
import random
import numpy as np
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.miner import Miner
    from entities.coalition import Coalition
    from entities.ecp import ECP

# ============================================================================
# UTILITY CALCULATIONS (Core formulas from paper)
# ============================================================================

def calculate_miner_utility(miner: 'Miner', coalition: 'Coalition',
                           rewards: float, ecp_price: float,
                           ecp_compute_purchased: float) -> float:
    """
    Calculate utility for a miner in a specific coalition.

    Formula (from paper):
        u_{n,m} = (w_{n,m} / W_m) × (R_m - p × l_m)

    Where:
        - w_{n,m} = work contributed by miner n to coalition m
        - W_m = total work by all members of coalition m
        - R_m = reward earned by coalition m (block reward + transaction fees)
        - p = ECP price per unit compute
        - l_m = compute purchased by coalition m from ECP

    Args:
        miner: Miner object
        coalition: Coalition object
        rewards: Total rewards earned by coalition (R_m)
        ecp_price: Current ECP price (p)
        ecp_compute_purchased: Compute purchased from ECP (l_m)

    Returns:
        Utility value for the miner in this coalition
    """
    # Get miner's contribution to coalition
    work_contributed = miner.get_work_contribution(coalition)

    # Get total work by all coalition members
    total_work = coalition.get_total_work()

    if total_work == 0:
        return 0.0

    # Calculate share of rewards
    work_share = work_contributed / total_work

    # Calculate net reward after ECP costs
    net_reward = rewards - (ecp_price * ecp_compute_purchased)

    # Miner's utility is their proportional share of net reward
    utility = work_share * net_reward

    return max(0.0, utility)  # Utility cannot be negative


def calculate_coalition_utility(coalition: 'Coalition', rewards: float,
                                ecp_price: float,
                                ecp_compute_purchased: float) -> float:
    """
    Calculate total utility for a coalition.

    Formula (from paper):
        u_m = R_m - p × l_m - overhead_costs

    Where:
        - R_m = B + sum(transaction_fees) if block found, else 0
        - B = fixed block reward
        - p = ECP price
        - l_m = compute purchased from ECP

    Args:
        coalition: Coalition object
        rewards: Total rewards (R_m)
        ecp_price: Current ECP price (p)
        ecp_compute_purchased: Compute purchased (l_m)

    Returns:
        Coalition utility value
    """
    utility = rewards - (ecp_price * ecp_compute_purchased)
    return max(0.0, utility)


def calculate_ecp_utility(ecp: 'ECP') -> float:
    """
    Calculate total utility (profit) for the ECP.

    Formula (from paper):
        u_ECP = sum_m(p × l_m) - sum_m(c × l_m)
        u_ECP = (p - c) × sum_m(l_m)

    Where:
        - p = price per unit compute
        - c = operating cost per unit
        - l_m = compute purchased by coalition m

    Args:
        ecp: ECP object with price, cost, and demand information

    Returns:
        ECP utility (profit)
    """
    total_demand = ecp.get_total_demand()
    profit_per_unit = ecp.price_per_hash - ecp.operating_cost_per_hash
    utility = profit_per_unit * total_demand
    return max(0.0, utility)


def calculate_system_utility(miners: List['Miner'], ecp: 'ECP') -> float:
    """
    Calculate total system utility across entire network.

    Formula (from paper):
        u_system = u_ECP + sum_{n,m}(u_{n,m})

    Args:
        miners: List of all miner objects
        ecp: ECP object (can be None for non-cooperative)

    Returns:
        Total system utility
    """
    # ECP utility (0 if no ECP)
    ecp_utility = calculate_ecp_utility(ecp) if ecp else 0.0

    # Sum of all miner utilities/earnings
    # For non-cooperative (no ECP), use total_earnings
    # For coalition scenarios (with ECP), use calculated utility
    if ecp:
        miner_utilities = sum(miner.get_total_utility() for miner in miners)
    else:
        # Non-cooperative: use actual earnings since there's no ECP cost to subtract
        miner_utilities = sum(miner.total_earnings for miner in miners)

    system_utility = ecp_utility + miner_utilities
    return system_utility


# ============================================================================
# DEFINITION 4: COALITION JOINING CONDITION
# ============================================================================

def check_definition_4(coalition: 'Coalition', new_miner: 'Miner') -> bool:
    """
    Verify that adding a new miner doesn't hurt existing members' utility.

    Definition 4 (from paper):
        Miner n can join coalition m if and only if:
        ∀i ∈ C_m: u'_{i,m} >= u_{i,m}

    Where:
        - u_{i,m} = current utility of member i in coalition m
        - u'_{i,m} = projected utility of member i after n joins

    Args:
        coalition: Coalition object
        new_miner: Miner attempting to join

    Returns:
        True if joining satisfies Definition 4, False otherwise
    """
    # Store current utilities for all existing members
    current_utilities = {}
    for member in coalition.members:
        current_utilities[member.miner_id] = member.get_utility_in_coalition(coalition)

    # Simulate adding the new miner
    projected_total_work = coalition.get_total_work() + new_miner.get_potential_work_contribution(coalition)

    # Check projected utilities for all existing members
    for member in coalition.members:
        member_work = member.get_work_contribution(coalition)

        # Projected share after new miner joins
        projected_share = member_work / projected_total_work if projected_total_work > 0 else 0

        # Current share
        current_work = coalition.get_total_work()
        current_share = member_work / current_work if current_work > 0 else 0

        # IMPORTANT: When new miner joins, coalition's hashrate increases,
        # which increases block-finding probability and expected rewards!
        # Current expected rewards
        current_expected_rewards = coalition.expected_rewards if coalition.expected_rewards > 0 else 1000.0

        # Projected expected rewards (higher because coalition is stronger)
        current_hashrate = coalition.get_total_hashrate()
        projected_hashrate = current_hashrate + new_miner.total_hashrate

        # Expected rewards scale with hashrate (more hashrate = more blocks found)
        if current_hashrate > 0:
            hashrate_increase_factor = projected_hashrate / current_hashrate
        else:
            hashrate_increase_factor = 2.0  # Conservative estimate

        projected_expected_rewards = current_expected_rewards * hashrate_increase_factor

        # Calculate utilities
        projected_utility = projected_share * projected_expected_rewards
        current_utility_value = current_share * current_expected_rewards

        # Allow joining if projected utility is at least 95% of current
        # (small tolerance to encourage coalition growth)
        tolerance = 0.95
        if projected_utility < current_utility_value * tolerance - 1e-6:
            return False

    return True


# ============================================================================
# BLOCK DISCOVERY PROBABILITY
# ============================================================================

def calculate_block_discovery_probability(coalition: 'Coalition',
                                         total_network_hashrate: float,
                                         time_delta: float,
                                         difficulty: int) -> float:
    """
    Calculate probability of a coalition finding a block in a time interval.

    Uses Poisson process model:
        P(coalition finds block) = hashrate_share × base_probability
        base_probability = 1 - e^(-λt)

    Where:
        - λ = total_network_hashrate / difficulty (dynamic Poisson rate)
        - hashrate_share = coalition_hashrate / total_network_hashrate

    Args:
        coalition: Coalition object
        total_network_hashrate: Total hashrate across all coalitions
        time_delta: Time interval in seconds
        difficulty: Mining difficulty

    Returns:
        Probability of finding a block in time_delta
    """
    if total_network_hashrate == 0:
        return 0.0

    # Coalition's effective hashrate (members + ECP)
    coalition_hashrate = coalition.get_effective_hashrate()

    # Hashrate share
    hashrate_share = coalition_hashrate / total_network_hashrate

    # Dynamically calculate lambda rate based on total network hashrate and difficulty
    if difficulty == 0:
        return 1.0  # Avoid division by zero, assume instant blocks
    lambda_rate = total_network_hashrate / difficulty

    # Base probability of ANY block being found on the network
    base_prob = 1.0 - math.exp(-lambda_rate * time_delta)

    # Coalition's probability is its share of that base probability
    coalition_prob = hashrate_share * base_prob

    return min(1.0, coalition_prob)  # Cap at 1.0


def get_block_finder(coalitions: List['Coalition'], total_network_hashrate: float,
                    time_delta: float, difficulty: int) -> Optional['Coalition']:
    """
    Determine which coalition (if any) finds a block in a time interval.

    This first determines if a block was found on the network, and if so,
    assigns it to a winning coalition based on their hashrate share.

    Args:
        coalitions: List of all coalitions
        total_network_hashrate: Total network hashrate
        time_delta: Time interval in seconds
        difficulty: Mining difficulty

    Returns:
        Coalition that found the block, or None if no block found
    """
    # Calculate the network's block discovery rate (lambda)
    if total_network_hashrate <= 0 or difficulty <= 0:
        return None
    lambda_rate = total_network_hashrate / difficulty

    # Probability of ANYONE finding a block in time_delta
    base_prob = 1.0 - math.exp(-lambda_rate * time_delta)

    # Check if a block was found on the network in this step
    if random.random() >= base_prob:
        return None

    # A block was found. Now, determine which coalition found it.
    # The winner is chosen proportionally to their share of the total hashrate.
    
    coalition_list = []
    hashrate_weights = []
    
    for coalition in coalitions:
        coalition_list.append(coalition)
        hashrate_weights.append(coalition.get_effective_hashrate())

    # This should not happen if total_network_hashrate > 0, but as a safeguard:
    if not coalition_list or sum(hashrate_weights) == 0:
        return None

    # Select the winner based on hashrate contribution
    try:
        winner = random.choices(coalition_list, weights=hashrate_weights, k=1)[0]
        return winner
    except IndexError:
        return None


# ============================================================================
# STACKELBERG GAME: ECP OPTIMAL PRICING
# ============================================================================

def calculate_optimal_ecp_price(ecp: 'ECP', coalitions: List['Coalition'],
                               learning_rate: float = 0.01,
                               max_iterations: int = 100,
                               convergence_threshold: float = 0.01) -> float:
    """
    Calculate optimal ECP price using Stackelberg game equilibrium.

    The ECP solves:
        max_p [u_ECP(p)] = max_p [(p - c) × sum_m(l_m(p))]

    Where l_m(p) is the demand function (compute purchased at price p).

    Uses gradient ascent to find optimal price:
        p_{t+1} = p_t + α × ∂u_ECP/∂p

    Args:
        ecp: ECP object
        coalitions: List of coalitions (demand side)
        learning_rate: Step size for gradient ascent
        max_iterations: Maximum optimization iterations
        convergence_threshold: Convergence criterion for gradient

    Returns:
        Optimal price
    """
    current_price = ecp.price_per_hash
    epsilon = 0.01  # Small value for numerical gradient

    for iteration in range(max_iterations):
        # Calculate current utility
        current_utility = calculate_ecp_utility_at_price(ecp, coalitions, current_price)

        # Calculate utility at slightly higher price
        utility_plus = calculate_ecp_utility_at_price(ecp, coalitions, current_price + epsilon)

        # Numerical gradient
        gradient = (utility_plus - current_utility) / epsilon

        # Check convergence
        if abs(gradient) < convergence_threshold:
            break

        # Gradient ascent step
        current_price = current_price + learning_rate * gradient

        # Clamp to reasonable range
        current_price = max(0.0, min(450.0, current_price))

        # Decay learning rate
        learning_rate *= 0.95

    return current_price


def calculate_ecp_utility_at_price(ecp: 'ECP', coalitions: List['Coalition'],
                                   price: float) -> float:
    """
    Calculate ECP utility at a specific price point.

    Simulates coalition demand at the given price.

    Args:
        ecp: ECP object
        coalitions: List of coalitions
        price: Price to evaluate

    Returns:
        ECP utility at this price
    """
    # Simulate demand at this price
    total_demand = 0.0
    for coalition in coalitions:
        demand = coalition.calculate_optimal_compute_demand(price, ecp.operating_cost_per_hash)
        total_demand += demand

    # Utility = (price - cost) × demand
    utility = (price - ecp.operating_cost_per_hash) * total_demand
    return max(0.0, utility)


# ============================================================================
# ERC GAME: COALITION COMPUTE PURCHASE
# ============================================================================

def calculate_optimal_compute_purchase(coalition: 'Coalition', price: float,
                                      cost: float,
                                      total_network_hashrate: float) -> float:
    """
    Calculate optimal compute to purchase from ECP for a coalition.

    Each coalition solves:
        max_{l_m} [u_m] = max_{l_m} [R_m(l_m) - p × l_m]

    First-order condition:
        ∂u_m/∂l_m = ∂R_m/∂l_m - p = 0

    This means: marginal benefit of compute = price

    Args:
        coalition: Coalition object
        price: Current ECP price
        cost: ECP operating cost
        total_network_hashrate: Total network hashrate

    Returns:
        Optimal compute amount to purchase
    """
    # Binary search for optimal compute purchase
    lower_bound = 0.0
    upper_bound = 1e10  # Maximum possible purchase

    best_compute = 0.0
    best_utility = coalition.get_expected_utility_with_compute(0, price, total_network_hashrate)

    # Use binary search to find optimal
    for _ in range(20):  # 20 iterations sufficient for convergence
        mid = (lower_bound + upper_bound) / 2

        utility = coalition.get_expected_utility_with_compute(mid, price, total_network_hashrate)

        if utility > best_utility:
            best_utility = utility
            best_compute = mid
            lower_bound = mid
        else:
            upper_bound = mid

    return best_compute


# ============================================================================
# WORK ALLOCATION
# ============================================================================

def calculate_effective_hashrate(miner: 'Miner', coalition: 'Coalition',
                                context_switch_overhead: float = 0.016) -> float:
    """
    Calculate effective hashrate considering context switching overhead.

    Args:
        miner: Miner object
        coalition: Coalition the miner is contributing to
        context_switch_overhead: Overhead per context switch (1.6%)

    Returns:
        Effective hashrate after overhead
    """
    # Base allocation
    allocated_hashrate = miner.total_hashrate * miner.get_allocation(coalition)

    # Context switching overhead
    num_coalitions = len(miner.coalitions)
    if num_coalitions <= 1:
        # No overhead for single coalition
        return allocated_hashrate

    # Number of switches per cycle equals number of coalitions
    num_switches = num_coalitions
    total_overhead = num_switches * context_switch_overhead

    # Effective hashrate
    effective = allocated_hashrate * (1.0 - total_overhead)

    return max(0.0, effective)


def calculate_optimal_work_allocation(miner: 'Miner',
                                     coalitions: List['Coalition']) -> Dict[int, float]:
    """
    Calculate optimal work allocation across multiple coalitions.

    Allocates based on expected utility from each coalition.

    Args:
        miner: Miner object
        coalitions: List of coalitions miner belongs to

    Returns:
        Dictionary mapping coalition_id to allocation percentage
    """
    if len(coalitions) == 0:
        return {}

    if len(coalitions) == 1:
        return {coalitions[0].coalition_id: 1.0}

    # Calculate expected utility from each coalition
    utilities = {}
    total_utility = 0.0

    for coalition in coalitions:
        utility = coalition.get_expected_member_utility(miner)
        utilities[coalition.coalition_id] = max(0.0, utility)
        total_utility += utilities[coalition.coalition_id]

    if total_utility == 0:
        # Equal allocation if no clear winner
        equal_share = 1.0 / len(coalitions)
        return {c.coalition_id: equal_share for c in coalitions}

    # Proportional allocation based on utility
    allocation = {}
    for coalition in coalitions:
        allocation[coalition.coalition_id] = utilities[coalition.coalition_id] / total_utility

    return allocation


# ============================================================================
# STATISTICAL FUNCTIONS
# ============================================================================

def calculate_confidence_interval(data: List[float], confidence: float = 0.95) -> tuple:
    """
    Calculate confidence interval for a dataset.

    Args:
        data: List of values
        confidence: Confidence level (default 0.95 for 95%)

    Returns:
        Tuple of (mean, lower_bound, upper_bound)
    """
    if len(data) == 0:
        return 0.0, 0.0, 0.0

    mean = np.mean(data)
    std_error = np.std(data, ddof=1) / np.sqrt(len(data))

    # Use t-distribution for small samples
    from scipy import stats
    t_value = stats.t.ppf((1 + confidence) / 2, len(data) - 1)

    margin = t_value * std_error

    return mean, mean - margin, mean + margin


def calculate_improvement_percentage(baseline: float, improved: float) -> float:
    """
    Calculate percentage improvement over baseline.

    Args:
        baseline: Baseline value
        improved: Improved value

    Returns:
        Improvement percentage
    """
    if baseline == 0:
        return 0.0

    return ((improved - baseline) / baseline) * 100.0
