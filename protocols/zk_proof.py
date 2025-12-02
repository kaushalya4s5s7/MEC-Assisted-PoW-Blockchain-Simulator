
import logging
from typing import TYPE_CHECKING

from simulation.config import ZK_HESITANCY_FACTOR, ZK_PROOF_VERIFICATION_TIME

if TYPE_CHECKING:
    from entities.miner import Miner
    from entities.coalition import Coalition

logger = logging.getLogger(__name__)

class ZKProofProtocol:
    """
    Simulates the impact of Zero-Knowledge Proofs on coalition joining willingness.
    """

    def calculate_join_willingness(self, miner: 'Miner', coalition: 'Coalition', using_zk: bool) -> float:
        """
        Calculates a miner's willingness to join a coalition, adjusted by ZK proofs.

        If a miner is already in other coalitions, they might be hesitant to join
        another one without privacy guarantees (like ZK proofs).

        Args:
            miner (Miner): The miner considering joining.
            coalition (Coalition): The coalition being considered.
            using_zk (bool): Whether ZK proofs are being used in the protocol.

        Returns:
            float: The adjusted utility gain, representing the miner's willingness.
        """
        # This function might need to be adapted based on the actual utility calculation
        # in the simulation. For now, we'll use a placeholder.
        base_utility_gain = miner.evaluate_coalition_utility(coalition)

        # A miner already in one or more coalitions may be hesitant to join another
        # without the privacy assurances of ZK-proofs.
        if not using_zk and len(miner.coalitions) > 0:
            hesitancy_reduction = base_utility_gain * ZK_HESITANCY_FACTOR
            adjusted_utility = base_utility_gain - hesitancy_reduction
            logger.debug(
                f"Miner {miner.id} is hesitant. Utility reduced by {ZK_HESITANCY_FACTOR*100}% "
                f"to {adjusted_utility:.4f} due to lack of ZK-proof."
            )
            return adjusted_utility
        
        if using_zk:
            logger.debug(f"ZK-proof removes privacy concerns for Miner {miner.id}. No utility reduction.")

        return base_utility_gain

    def verify_proof_time(self) -> float:
        """
        Returns the computational overhead for verifying a ZK proof.

        Returns:
            float: The time in seconds for verification.
        """
        return ZK_PROOF_VERIFICATION_TIME
