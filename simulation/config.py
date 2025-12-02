"""
Configuration parameters for the blockchain mining simulation.
All parameters are centralized here for easy modification.
"""

import random
import numpy as np

# Set random seeds for reproducibility
RANDOM_SEED = None # Use None for true randomness, or a number for deterministic runs
# The seed is now applied in the reset_random_seeds() function
# random.seed(RANDOM_SEED)
# np.random.seed(RANDOM_SEED)

# ============================================================================
# SIMULATION PARAMETERS
# ============================================================================

# Simulation timing
TIMESTEP = 1.0  # seconds (discrete time simulation)
WARMUP_PERIOD = 50  # seconds - coalition formation period (reduced for speed)
COLLECTION_PERIOD = 100  # seconds - actual data collection (reduced for speed)
TOTAL_SIMULATION_TIME = WARMUP_PERIOD + COLLECTION_PERIOD

# Number of simulation runs for statistical analysis
NUM_RUNS = 5  # Reduced for faster execution (use 500 for publication)
CONFIDENCE_LEVEL = 0.95  # 95% confidence intervals

# ============================================================================
# NETWORK PARAMETERS
# ============================================================================

# Number of miners in the network
N_MINERS = 20  # Can be varied in parameter sweeps (2-30)

# Maximum number of coalitions a miner can join
MAX_COALITIONS_J = 3  # Varies: 1, 2, 3, 5, 7, 10

# ============================================================================
# BLOCKCHAIN PARAMETERS
# ============================================================================

# Block reward and transactions
BLOCK_REWARD_B = 1000  # Fixed reward per block (normalized from 6.25 BTC)
TRANSACTIONS_PER_BLOCK_I = 10  # Number of transactions in each block
TOTAL_TRANSACTIONS = 1000  # Total available in network

# Transaction fee range (uniform distribution)
TRANSACTION_FEE_MIN = 0
TRANSACTION_FEE_MAX = 100

# Mining difficulty and block time
# DIFFICULTY must be much higher than network hashrate to avoid 100% block probability
# With ~1.2 GH/s network hashrate, target 10-15 blocks per 150s:
# Lambda = hashrate/difficulty should be ~0.08 per timestep
# Therefore: DIFFICULTY = 1.2e9 / 0.08 ≈ 15e9
DIFFICULTY = 15_000_000_000  # 15 billion - balanced for 10-15 blocks per 150s simulation
AVERAGE_BLOCK_TIME = 600  # seconds (10 minutes - reference only)
LAMBDA_BLOCK_RATE = 1.0 / AVERAGE_BLOCK_TIME  # Poisson process rate

# ============================================================================
# MINER PARAMETERS
# ============================================================================

# Hashrate distribution (varies across miners)
HASHRATE_DISTRIBUTION = "uniform"  # Options: "uniform", "normal", "exponential"
HASHRATE_MIN = 100e6  # 100 MH/s (mega-hashes per second)
HASHRATE_MAX = 500e6  # 500 MH/s

# Transaction collection rate (proportional to hashrate)
# Higher hashrate = more network connections = more tx collected
def get_transaction_collection_rate(hashrate):
    """Calculate transaction collection rate based on hashrate."""
    return int(hashrate / 1e6)  # 1 transaction per MH/s per second

# Stake deposit (for realism, doesn't affect simulation)
STAKE_AMOUNT = 0.5  # BTC

# Work allocation parameters
CONTEXT_SWITCH_OVERHEAD = 0.016  # 1.6% overhead per context switch
SWITCH_TIME_MS = 40  # milliseconds per context switch
CYCLE_TIME_MS = 1000  # milliseconds per work cycle

# ============================================================================
# ECP (EDGE COMPUTING PROVIDER) PARAMETERS
# ============================================================================

# Capacity
CAPACITY_UNIT = "hashes_per_second"
ECP_MAX_CAPACITY_L = 10e9  # 10 GH/s (giga-hashes per second)

# Pricing
ECP_OPERATING_COST_C = 0.5  # Operating cost per unit (as per paper)
ECP_INITIAL_PRICE = 200  # Initial price per unit
ECP_PRICE_MIN = 0
ECP_PRICE_MAX = 450

# Stackelberg game parameters for ECP pricing optimization
STACKELBERG_LEARNING_RATE = 0.01
STACKELBERG_MAX_ITERATIONS = 100
STACKELBERG_CONVERGENCE_THRESHOLD = 0.01
STACKELBERG_STEP_DECAY = 0.95

# Overlap optimization threshold
OVERLAP_THRESHOLD = 0.3  # 30% shared members required for optimization
OVERLAP_SAVINGS_FACTOR = 0.25  # 25% cost reduction from optimization

# ============================================================================
# OCF GAME PARAMETERS
# ============================================================================

# Coalition formation game
OCF_MAX_ITERATIONS = 20  # Maximum iterations for convergence (reduced for speed)
OCF_CONVERGENCE_EPSILON = 0.01  # Utility improvement threshold
OCF_UPDATE_FREQUENCY = 10  # seconds between coalition formation updates

# Strategy selection
ATOMIC_STRATEGIES = ["STAY", "MERGE", "SPLIT", "LEAVE"]

# ============================================================================
# INNOVATION 1: BLOOM FILTER PARAMETERS
# ============================================================================

BLOOM_FILTER_ENABLED = True  # Toggle Bloom filter optimization
BLOOM_FILTER_SIZE = 50000  # bits
BLOOM_NUM_HASH_FUNCTIONS = 7
BLOOM_FALSE_POSITIVE_RATE = 0.01  # 1%

# Bandwidth calculation
TRANSACTION_SIZE = 250  # bytes per transaction
BLOOM_FILTER_OVERHEAD = BLOOM_FILTER_SIZE / 8  # Convert bits to bytes

# Expected bandwidth savings
BLOOM_FILTER_SAVINGS_EXPECTED = 0.93  # 93% reduction

# ============================================================================
# INNOVATION 2: SMART CONTRACT PARAMETERS
# ============================================================================

SMART_CONTRACT_ENABLED = True  # Toggle smart contract usage

# Trust overhead without smart contracts
TRUST_OVERHEAD_FACTOR = 0.07  # 7% utility discount due to trust concerns
THEFT_PROBABILITY = 0.01  # 1% chance per epoch of coalition head theft
THEFT_AMOUNT = 0.20  # Coalition head steals 20% of rewards

# ============================================================================
# INNOVATION 3: ECP OPTIMIZATION PARAMETERS
# ============================================================================

ECP_OPTIMIZATION_ENABLED = True  # Toggle ECP overlapping work optimization

# Cost savings from coordinating overlapping work
ECP_OPTIMIZATION_SAVINGS = 0.25  # 25% reduction in operating costs

# ============================================================================
# INNOVATION 4: FAST RESULT DELIVERY PARAMETERS
# ============================================================================

FAST_DELIVERY_ENABLED = True  # Toggle dual-channel delivery

# Latency distributions (in milliseconds)
WEBSOCKET_LATENCY_MEAN = 10.0
WEBSOCKET_LATENCY_STD = 3.0

UDP_LATENCY_MEAN = 2.0
UDP_LATENCY_STD = 0.5
UDP_PACKET_LOSS_RATE = 0.02  # 2% packet loss

# Expected improvement
LATENCY_REDUCTION_EXPECTED = 0.80  # 80% reduction (10ms -> 2ms)

# ============================================================================
# INNOVATION 5: ZERO-KNOWLEDGE PROOF PARAMETERS
# ============================================================================

ZK_PROOF_ENABLED = True  # Toggle ZK proof usage

# Hesitancy factor without ZK proofs
ZK_HESITANCY_FACTOR = 0.30  # 30% less likely to join additional coalitions

# ZK proof overhead (small computational cost)
ZK_PROOF_VERIFICATION_TIME = 0.001  # seconds

# ============================================================================
# UTILITY CALCULATION PARAMETERS
# ============================================================================

# Definition 4: Coalition joining condition
# A miner can join a coalition only if existing members don't lose utility
DEFINITION_4_ENABLED = True

# Utility calculation components
UTILITY_DISCOUNT_RATE = 0.0  # No discounting (immediate rewards)

# ============================================================================
# METRICS AND LOGGING
# ============================================================================

# Metric recording frequency
METRIC_RECORDING_INTERVAL = 10  # seconds

# Logging levels
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True
LOG_FILE = "results/simulation.log"

# Progress bar
SHOW_PROGRESS_BAR = True

# ============================================================================
# PARAMETER SWEEP CONFIGURATIONS
# ============================================================================

# Sweep 1: ECP Price
SWEEP_PRICE_RANGE = list(range(0, 451, 25))  # 0 to 450 in steps of 25

# Sweep 2: Number of Miners
SWEEP_MINERS_RANGE = list(range(2, 31, 2))  # 2 to 30 in steps of 2

# Sweep 3: Transactions per Block
SWEEP_TRANSACTIONS_RANGE = list(range(5, 16, 1))  # 5 to 15 in steps of 1

# Sweep 4: Block Reward
SWEEP_BLOCK_REWARD_RANGE = list(range(500, 2001, 100))  # 500 to 2000 in steps of 100

# Sweep 5: Maximum Coalitions (for enhanced architecture only)
SWEEP_MAX_COALITIONS_RANGE = [3, 5, 7, 10]

# ============================================================================
# VALIDATION TARGETS (from paper)
# ============================================================================

# Expected improvements vs Non-cooperative baseline
EXPECTED_IMPROVEMENTS = {
    "J=1_vs_noncoop": {
        "ecp_utility": 0.3267,  # 32.67% increase
        "system_utility": 0.1809,  # 18.09% increase
    },
    "J=3_vs_noncoop": {
        "ecp_utility": 0.4152,  # 41.52% increase
        "system_utility": 0.3335,  # 33.35% increase
    },
    "enhanced_vs_noncoop": {
        "ecp_utility": 0.50,  # Target: 50%+ increase
        "system_utility": 0.45,  # Target: 45%+ increase (125-130% of baseline)
    }
}

# Validation tolerance
VALIDATION_TOLERANCE = 0.05  # 5% margin of error

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

# Figure settings
FIGURE_DPI = 300  # High quality for publication
FIGURE_FORMAT = "pdf"  # Options: "pdf", "png", "svg"
FIGURE_DIR = "figures/"

# Results export
RESULTS_DIR = "results/"
EXPORT_FORMAT = "csv"  # Options: "csv", "json", "both"

# Graph style
PLOT_STYLE = "seaborn-v0_8-darkgrid"
COLOR_PALETTE = "Set2"

# ============================================================================
# SCENARIO CONFIGURATIONS
# ============================================================================

SCENARIOS = {
    "non_cooperative": {
        "name": "Non-Cooperative",
        "max_coalitions": 0,
        "ecp_enabled": False,
        "bloom_filter": False,
        "smart_contract": False,
        "ecp_optimization": False,
        "fast_delivery": False,
        "zk_proof": False,
        "description": "Baseline: Each miner works alone"
    },
    "single_coalition": {
        "name": "Single Coalition (J=1)",
        "max_coalitions": 1,
        "ecp_enabled": True,
        "bloom_filter": False,
        "smart_contract": False,
        "ecp_optimization": False,
        "fast_delivery": False,
        "zk_proof": False,
        "description": "Standard mining pool model"
    },
    "multi_coalition_j2": {
        "name": "Multi-Coalition (J=2)",
        "max_coalitions": 2,
        "ecp_enabled": True,
        "bloom_filter": False,
        "smart_contract": False,
        "ecp_optimization": False,
        "fast_delivery": False,
        "zk_proof": False,
        "description": "Naive multi-coalition (2 coalitions per miner)"
    },
    "multi_coalition_j3_naive": {
        "name": "Multi-Coalition (J=3 Naive)",
        "max_coalitions": 3,
        "ecp_enabled": True,
        "bloom_filter": False,
        "smart_contract": False,
        "ecp_optimization": False,
        "fast_delivery": False,
        "zk_proof": False,
        "description": "Naive multi-coalition (3 coalitions per miner)"
    },
    "enhanced_j3": {
        "name": "Enhanced Architecture (J=3)",
        "max_coalitions": 3,
        "ecp_enabled": True,
        "bloom_filter": True,
        "smart_contract": True,
        "ecp_optimization": True,
        "fast_delivery": True,
        "zk_proof": True,
        "description": "Full enhanced architecture with all innovations"
    },
    "enhanced_j5": {
        "name": "Enhanced Architecture (J=5)",
        "max_coalitions": 5,
        "ecp_enabled": True,
        "bloom_filter": True,
        "smart_contract": True,
        "ecp_optimization": True,
        "fast_delivery": True,
        "zk_proof": True,
        "description": "Enhanced architecture with 5 coalitions per miner"
    },
    "enhanced_j7": {
        "name": "Enhanced Architecture (J=7)",
        "max_coalitions": 7,
        "ecp_enabled": True,
        "bloom_filter": True,
        "smart_contract": True,
        "ecp_optimization": True,
        "fast_delivery": True,
        "zk_proof": True,
        "description": "Enhanced architecture with 7 coalitions per miner"
    }
}

# Default scenario for testing
DEFAULT_SCENARIO = "multi_coalition_j3_naive"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_scenario_config(scenario_name):
    """Get configuration for a specific scenario."""
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    return SCENARIOS[scenario_name]

def reset_random_seeds():
    """Reset random seeds for reproducibility if RANDOM_SEED is set."""
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)
        np.random.seed(RANDOM_SEED)

def get_hashrate_sample():
    """Sample a hashrate value based on configured distribution."""
    if HASHRATE_DISTRIBUTION == "uniform":
        return random.uniform(HASHRATE_MIN, HASHRATE_MAX)
    elif HASHRATE_DISTRIBUTION == "normal":
        mean = (HASHRATE_MIN + HASHRATE_MAX) / 2
        std = (HASHRATE_MAX - HASHRATE_MIN) / 6  # 99.7% within range
        return np.clip(random.gauss(mean, std), HASHRATE_MIN, HASHRATE_MAX)
    elif HASHRATE_DISTRIBUTION == "exponential":
        return np.clip(random.expovariate(1.0 / HASHRATE_MIN), HASHRATE_MIN, HASHRATE_MAX)
    else:
        raise ValueError(f"Unknown distribution: {HASHRATE_DISTRIBUTION}")

def get_transaction_fee_sample():
    """Sample a transaction fee value."""
    return random.uniform(TRANSACTION_FEE_MIN, TRANSACTION_FEE_MAX)
