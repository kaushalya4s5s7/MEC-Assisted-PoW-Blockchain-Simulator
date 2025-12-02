
import random
import logging
import statistics

from simulation.config import (
    WEBSOCKET_LATENCY_MEAN,
    WEBSOCKET_LATENCY_STD,
    UDP_LATENCY_MEAN,
    UDP_LATENCY_STD,
    UDP_PACKET_LOSS_RATE
)

logger = logging.getLogger(__name__)

class ResultDelivery:
    """
    Simulates and compares different result delivery protocols.
    """

    def websocket_latency(self) -> float:
        """
        Simulates latency for a WebSocket-only delivery.

        Returns:
            float: The simulated latency in milliseconds.
        """
        return random.gauss(WEBSOCKET_LATENCY_MEAN, WEBSOCKET_LATENCY_STD)

    def udp_latency(self) -> float:
        """
        Simulates latency for a UDP-only delivery, accounting for packet loss.

        Returns:
            float: The simulated latency in milliseconds, or float('inf') for packet loss.
        """
        if random.random() < UDP_PACKET_LOSS_RATE:
            logger.debug(f"UDP packet lost (loss rate: {UDP_PACKET_LOSS_RATE})")
            return float('inf')
        return random.gauss(UDP_LATENCY_MEAN, UDP_LATENCY_STD)

    def dual_channel_latency(self) -> float:
        """
        Simulates latency for a dual-channel (UDP + WebSocket) delivery.

        Returns:
            float: The minimum latency from either UDP or WebSocket.
        """
        udp = self.udp_latency()
        websocket = self.websocket_latency()
        latency = min(udp, websocket)
        
        if latency == float('inf'):
            logger.warning("Both UDP and WebSocket failed, which is highly unlikely.")
        
        return latency

    def calculate_latency_reduction(self, num_samples: int = 1000) -> float:
        """
        Calculates the percentage improvement of dual-channel delivery over WebSocket-only.

        Args:
            num_samples (int): The number of simulations to run for the comparison.

        Returns:
            float: The percentage reduction in average latency.
        """
        websocket_latencies = [self.websocket_latency() for _ in range(num_samples)]
        dual_channel_latencies = [self.dual_channel_latency() for _ in range(num_samples)]

        # Filter out any potential infinite values if all simulations fail
        valid_ws = [lat for lat in websocket_latencies if lat != float('inf')]
        valid_dual = [lat for lat in dual_channel_latencies if lat != float('inf')]

        if not valid_ws or not valid_dual:
            logger.error("Could not calculate latency reduction due to simulation failures.")
            return 0.0

        avg_websocket_latency = statistics.mean(valid_ws)
        avg_dual_channel_latency = statistics.mean(valid_dual)

        logger.info(f"Average WebSocket latency: {avg_websocket_latency:.2f}ms")
        logger.info(f"Average dual-channel latency: {avg_dual_channel_latency:.2f}ms")

        if avg_websocket_latency == 0:
            return float('inf') # Avoid division by zero

        improvement = ((avg_websocket_latency - avg_dual_channel_latency) / avg_websocket_latency) * 100
        logger.info(f"Latency improvement with dual-channel: {improvement:.2f}%")
        
        return improvement
