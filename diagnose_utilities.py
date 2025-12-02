#!/usr/bin/env python3
"""
Quick diagnostic script to check why utilities are all zeros.
"""

import sys
from simulation.engine import SimulationEngine
from simulation.config import get_scenario_config, reset_random_seeds
from simulation.utils import calculate_ecp_utility, calculate_system_utility

def diagnose():
    print("=" * 70)
    print("UTILITY DIAGNOSTIC")
    print("=" * 70)

    # Run a single quick simulation
    reset_random_seeds()
    config = get_scenario_config('enhanced_j3')
    engine = SimulationEngine(config)

    print("\n1. Running single simulation...")
    result = engine.run(num_runs=1)

    print("\n2. Final Results:")
    print(f"   Scenario: {result.get('scenario')}")
    print(f"   Blocks found: {result.get('blocks_found')}")
    print(f"   Total rewards: {result.get('total_rewards'):.2f}")
    print(f"   ECP Utility (mean): {result.get('ecp_utility', {}).get('mean', 0):.2f}")
    print(f"   System Utility (mean): {result.get('system_utility', {}).get('mean', 0):.2f}")

    print("\n3. Checking metrics history...")
    if hasattr(engine, 'metrics_history'):
        print(f"   Metrics records: {len(engine.metrics_history)}")
        if len(engine.metrics_history) > 0:
            sample = engine.metrics_history[0]
            print(f"   Sample metric keys: {list(sample.keys())}")
            print(f"   Sample values:")
            for key, value in sample.items():
                print(f"     - {key}: {value}")

    print("\n4. Checking ECP state...")
    if engine.ecp:
        print(f"   ECP exists: Yes")
        print(f"   ECP price: {engine.ecp.price_per_hash}")
        print(f"   ECP total revenue: {engine.ecp.total_revenue}")
        print(f"   ECP total cost: {engine.ecp.total_cost}")

        # Calculate ECP utility manually
        ecp_utility = engine.ecp.total_revenue - engine.ecp.total_cost
        print(f"   ECP utility (manual calc): {ecp_utility:.2f}")
    else:
        print(f"   ECP exists: No")

    print("\n5. Checking Coalitions...")
    print(f"   Number of coalitions: {len(engine.coalitions)}")
    for coalition in engine.coalitions[:3]:  # Show first 3
        print(f"   Coalition {coalition.coalition_id}:")
        print(f"     - Members: {len(coalition.members)}")
        print(f"     - Blocks found: {coalition.blocks_found}")
        print(f"     - Total rewards: {coalition.total_rewards:.2f}")

    print("\n6. Checking Miners...")
    print(f"   Number of miners: {len(engine.miners)}")
    sample_miners = engine.miners[:3]
    for miner in sample_miners:
        print(f"   Miner {miner.miner_id}:")
        print(f"     - Coalitions: {len(miner.coalitions)}")
        print(f"     - Total earnings: {miner.total_earnings:.2f}")
        print(f"     - Current utility: {miner.current_utility:.2f}")

    print("\n7. Problem Analysis:")

    # Check if blocks were found
    if result.get('blocks_found', 0) == 0:
        print("   ⚠️  NO BLOCKS FOUND during simulation")
        print("       → This is why utilities are zero!")
        print("       → Simulation time too short (300s)")
        print("       → Need longer COLLECTION_PERIOD")
    elif result.get('blocks_found', 0) > 0:
        print(f"   ✓  Blocks found: {result.get('blocks_found')}")

        # Check if rewards were distributed
        if result.get('total_rewards', 0) > 0:
            print(f"   ✓  Rewards distributed: {result.get('total_rewards'):.2f}")

            # Check if utilities were calculated
            if result.get('ecp_utility', {}).get('mean', 0) == 0:
                print("   ⚠️  Utilities not calculated despite rewards!")
                print("       → Problem in calculate_ecp_utility()")
                print("       → Or utilities not being recorded in metrics")
        else:
            print("   ⚠️  No rewards distributed despite blocks found")

    print("\n" + "=" * 70)
    print("DIAGNOSIS COMPLETE")
    print("=" * 70)

    return result

if __name__ == "__main__":
    try:
        diagnose()
    except Exception as e:
        print(f"\nERROR during diagnosis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
