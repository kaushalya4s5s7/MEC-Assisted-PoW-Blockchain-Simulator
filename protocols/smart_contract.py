
import random
import logging

from simulation.config import (
    TRUST_OVERHEAD_FACTOR,
    THEFT_PROBABILITY,
    THEFT_AMOUNT
)

logger = logging.getLogger(__name__)

class SmartContractDistribution:
    """
    Simulates reward distribution with and without a smart contract.
    """

    def distribute_with_trust_overhead(self, reward: float, members: list) -> float:
        """
        Distributes reward with a trust-based model, which includes overhead and risk.

        Args:
            reward (float): The total reward to be distributed.
            members (list): The list of members to distribute the reward to.

        Returns:
            float: The adjusted reward after accounting for trust overhead.
        """
        # Apply a discount factor for the overhead of trust-based systems
        adjusted_reward = reward * (1 - TRUST_OVERHEAD_FACTOR)
        logger.debug(f"Applying {TRUST_OVERHEAD_FACTOR*100}% trust overhead. Reward reduced to {adjusted_reward:.2f}")

        # There is a probability of theft in a trust-based system
        if random.random() < THEFT_PROBABILITY:
            stolen_amount = adjusted_reward * THEFT_AMOUNT
            adjusted_reward -= stolen_amount
            logger.warning(f"Theft occurred! {THEFT_AMOUNT*100}% of the reward was stolen. Amount: {stolen_amount:.2f}")

        return adjusted_reward

    def distribute_with_smart_contract(self, reward: float, members: list) -> float:
        """
        Distributes reward using a smart contract, ensuring fair and full distribution.

        Args:
            reward (float): The total reward to be distributed.
            members (list): The list of members to distribute the reward to.

        Returns:
            float: The full reward.
        """
        # With a smart contract, distribution is fair and has no overhead
        logger.debug("Smart contract ensures fair distribution of the full reward.")
        return reward
