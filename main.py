#!/usr/bin/env python3
"""
Main entry point for the Multi-Coalition Blockchain Mining Simulator.

This CLI tool runs simulations, generates visualizations, and exports results.
"""

import sys
import argparse
import logging
import os
import glob
import pandas as pd
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

from simulation.config import (
    SCENARIOS, NUM_RUNS, LOG_LEVEL, LOG_FILE,
    get_scenario_config, reset_random_seeds
)


def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL)

    # Create results directory if it doesn't exist
    Path("results").mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, mode='w'), # Overwrite log file each run
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


def run_scenario(scenario_name, runs=NUM_RUNS, output=None):
    """
    Run a specific scenario.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Running scenario: {scenario_name} ({runs} runs)")

    from simulation.engine import SimulationEngine
    from analysis.export import ResultsExporter
    
    reset_random_seeds()
    
    config = get_scenario_config(scenario_name)
    engine = SimulationEngine(config)
    results = engine.run(num_runs=runs)

    if output:
        exporter = ResultsExporter()
        exporter.export_to_csv(results, output)
        logger.info(f"Results for {scenario_name} saved to: {output}")

    logger.info(f"Scenario {scenario_name} completed.")
    return results


def run_sweep(parameter, range_spec, runs=NUM_RUNS//10, output=None):
    """
    Run parameter sweep.
    """
    logger = logging.getLogger(__name__)
    from simulation import sweeps
    from analysis.export import ResultsExporter

    try:
        start, end, step = map(float, range_spec.split(','))
        param_range = range(int(start), int(end), int(step))
        logger.info(f"Parameter sweep: {parameter} from {start} to {end} with step {step}")
    except ValueError as e:
        logger.error(f"Invalid range specification: {e}")
        return None

    sweep_functions = {
        'price': sweeps.sweep_ecp_price,
        'miners': sweeps.sweep_num_miners,
        'transactions': sweeps.sweep_transactions_per_block,
        'block_reward': sweeps.sweep_block_reward
    }

    if parameter not in sweep_functions:
        logger.error(f"Unknown sweep parameter: {parameter}")
        return None

    # For sweeps, 'enhanced_j3' is a good default scenario
    results = sweep_functions[parameter]('enhanced_j3', param_range, runs)

    if output:
        exporter = ResultsExporter()
        exporter.export_to_csv(results, output)
        logger.info(f"Sweep results saved to: {output}")

    return results


def load_results_from_disk(results_dir="results/"):
    """
    Load all scenario .csv results from the results directory.
    """
    logger = logging.getLogger(__name__)
    results = {}
    logger.info(f"Loading results from disk: {results_dir}")
    search_path = os.path.join(results_dir, "*.csv")
    
    for filepath in glob.glob(search_path):
        filename = os.path.basename(filepath)
        if not filename.startswith("summary"):
            scenario_name = filename.replace(".csv", "")
            try:
                results[scenario_name] = pd.read_csv(filepath)
                logger.debug(f"Loaded {filename}")
            except Exception as e:
                logger.error(f"Could not load or parse {filename}: {e}")
    return results


def validate_results(tolerance=0.05):
    """
    Validate simulation results against paper benchmarks.
    """
    logger = logging.getLogger(__name__)
    from analysis.statistics import StatisticsAnalyzer
    from simulation.config import EXPECTED_IMPROVEMENTS

    logger.info("Loading data for validation...")
    baseline_results = load_results_from_disk()

    analyzer = StatisticsAnalyzer()
    validation_report = analyzer.validate_against_paper(
        baseline_results,
        EXPECTED_IMPROVEMENTS,
        tolerance
    )

    print("\n" + "="*25 + " VALIDATION REPORT " + "="*25)
    for scenario, report in validation_report.items():
        if not report: continue
        status = "✓ PASS" if report.get('passed') else "✗ FAIL"
        print(f"{scenario:<30} | Status: {status}")
        print(f"  - Expected Utility: {report.get('expected'):.4f}")
        print(f"  - Actual Utility:   {report.get('actual'):.4f}")
        print(f"  - Difference:       {report.get('difference'):.2f}%\n")
    print("="*70)

    return validation_report


def generate_visualizations(figure_num=None, output_dir="figures/"):
    """
    Generate publication-quality visualizations from saved results.
    """
    logger = logging.getLogger(__name__)
    from analysis.visualize import Visualizer
    from protocols.result_delivery import ResultDelivery

    logger.info("Gathering data for visualizations by loading from disk...")
    all_scenarios_results = load_results_from_disk()

    if not all_scenarios_results:
        logger.error("No result files found in 'results/' directory. Cannot generate visualizations.")
        return {"status": "failed", "reason": "No data"}

    # Data for latency plot (this is self-contained and doesn't need prior results)
    rd = ResultDelivery()
    latency_data = {
        'WebSocket only': [rd.websocket_latency() for _ in range(200)],
        'UDP only': [rd.udp_latency() for _ in range(200)],
        'Dual-channel': [rd.dual_channel_latency() for _ in range(200)]
    }
    latency_data['UDP only'] = [l for l in latency_data['UDP only'] if l != float('inf')]

    results_for_viz = {
        "all_scenarios": all_scenarios_results,
        "latency_data": latency_data,
        "price_sweep": all_scenarios_results.get("sweep_price"),
        "miners_sweep": all_scenarios_results.get("sweep_miners"),
    }
    
    viz = Visualizer(output_dir=output_dir)
    
    if figure_num:
        plot_map = {
            1: (viz.plot_performance_vs_price, all_scenarios_results),  # Use scenario data instead of sweep
            2: (viz.plot_performance_vs_miners, all_scenarios_results),  # Use scenario data instead of sweep
            3: (viz.plot_bandwidth_efficiency, all_scenarios_results),
            4: (viz.plot_ecp_cost_savings, all_scenarios_results),
            5: (viz.plot_latency_comparison, latency_data),
            6: (viz.plot_system_comparison, all_scenarios_results)
        }
        if figure_num in plot_map and plot_map[figure_num][1] is not None:
            plot_func, data = plot_map[figure_num]
            plot_func(data)
        elif figure_num in plot_map:
             logger.warning(f"Cannot generate figure {figure_num}, data is missing. Run a full simulation to generate sweep data.")
        else:
            logger.error(f"Figure {figure_num} is not a valid figure number (1-6).")
    else:
        # In the refactored code, we pass the loaded data to the visualizer
        viz.generate_all_figures(results_for_viz)

    logger.info("Visualization generation process completed.")
    return {"status": "completed"}


def export_results(format_type="csv", output=None, improvements=False):
    """
    Export simulation results from saved files.
    """
    logger = logging.getLogger(__name__)
    from analysis.export import ResultsExporter

    logger.info("Gathering data for export by loading from disk...")
    all_results = load_results_from_disk()

    if not all_results:
        logger.error("No result files found in 'results/' directory. Cannot generate export.")
        return {"status": "failed", "reason": "No data"}

    exporter = ResultsExporter()

    if improvements:
        baseline_main = all_results.get('multi_coalition_j3_naive')
        enhanced_main = all_results.get('enhanced_j3')
        if baseline_main is not None and enhanced_main is not None:
            exporter.create_improvement_table(baseline_main, enhanced_main)
    else:
        exporter.create_summary_table(all_results)
        
        if output:
            if format_type in ['csv', 'both']:
                # The summary is already created, this part might be redundant
                # or intended for a different format. Re-saving summary.
                exporter.export_to_csv(all_results, output.replace(".json", ".csv"))
            if format_type in ['json', 'both']:
                exporter.export_to_json(all_results, output.replace(".csv", ".json"))

    logger.info("Export process completed.")
    return {"status": "completed"}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Multi-Coalition Blockchain Mining Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run specific scenario
  python main.py --scenario=enhanced_j3 --runs=500 --output=results/enhanced_j3.csv

  # Run parameter sweep
  python main.py --sweep=price --range=0,450,25 --output=results/price_sweep.csv

  # Generate all visualizations
  python main.py --visualize

  # Generate a specific figure
  python main.py --visualize --figure=6

  # Validate results
  python main.py --validate

  # Export a summary of all scenarios
  python main.py --export --output=results/summary.csv

  # Export an improvement comparison table
  python main.py --export --improvements
        """
    )

    # Scenario execution
    parser.add_argument('--scenario', type=str, choices=list(SCENARIOS.keys()),
                       help='Run specific scenario')
    parser.add_argument('--runs', type=int, default=NUM_RUNS,
                       help=f'Number of simulation runs (default: {NUM_RUNS})')

    # Parameter sweeps
    parser.add_argument('--sweep', type=str,
                       choices=['price', 'miners', 'transactions', 'block_reward'],
                       help='Run parameter sweep')
    parser.add_argument('--range', type=str,
                       help='Range for sweep: start,end,step')

    # Validation
    parser.add_argument('--validate', action='store_true',
                       help='Validate results against paper')
    parser.add_argument('--tolerance', type=float, default=0.05,
                       help='Validation tolerance (default: 0.05)')

    # Visualization
    parser.add_argument('--visualize', action='store_true',
                       help='Generate visualizations')
    parser.add_argument('--figure', type=int,
                       help='Specific figure to generate (1-6)')

    # Export
    parser.add_argument('--export', action='store_true',
                       help='Export results')
    parser.add_argument('--format', type=str, default='csv',
                       choices=['csv', 'json', 'both'],
                       help='Export format for raw data')
    parser.add_argument('--improvements', action='store_true',
                       help='Export an improvement analysis table instead of a summary')

    # Output
    parser.add_argument('--output', type=str,
                       help='Output file path for scenarios, sweeps, or raw exports')
    parser.add_argument('--output-dir', type=str, default='figures/',
                       help='Output directory for figures')

    # Logging
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    logger.info("="*70)
    logger.info("Multi-Coalition Blockchain Mining Simulator")
    logger.info("="*70)

    try:
        if args.scenario:
            run_scenario(args.scenario, args.runs, args.output)

        elif args.sweep:
            if not args.range:
                logger.error("--range required for parameter sweep")
                return 1
            run_sweep(args.sweep, args.range, args.runs, args.output)

        elif args.validate:
            validate_results(args.tolerance)

        elif args.visualize:
            generate_visualizations(args.figure, args.output_dir)

        elif args.export:
            export_results(args.format, args.output, args.improvements)

        else:
            parser.print_help()
            logger.info("No operation specified. Showing help.")

        logger.info("="*70)
        logger.info("Execution completed successfully")
        logger.info("="*70)
        return 0

    except KeyboardInterrupt:
        logger.warning("\nExecution interrupted by user.")
        return 130
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
