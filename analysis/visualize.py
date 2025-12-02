import logging
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import ast
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class Visualizer:
    """
    Generates publication-quality figures from simulation results.
    """

    def __init__(self, output_dir: str = "figures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set plot style
        plt.style.use('seaborn-v0_8-darkgrid')
        self.palette = sns.color_palette('Set2')
        
        # Set font sizes
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['legend.fontsize'] = 10

    def _save_plot(self, fig, filename: str):
        """Saves a plot to the output directory."""
        path = self.output_dir / filename
        fig.savefig(path, dpi=300, format='pdf', bbox_inches='tight')
        logger.info(f"Figure saved to {path}")
        plt.close(fig)

    def plot_performance_vs_price(self, results_dict: Dict[str, Any], output_file: str = "fig1_performance_vs_price.pdf"):
        """
        Plot performance metrics across different scenarios.

        Since we don't have price sweep data, we show scenario comparison instead.
        """
        if not results_dict:
            logger.warning("plot_performance_vs_price: No data provided")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_title("Performance Comparison (No Data)")
            self._save_plot(fig, output_file)
            return

        # Extract metrics from scenarios
        scenarios = []
        ecp_utilities = []
        system_utilities = []

        for scenario_name, scenario_data in results_dict.items():
            # Skip non-cooperative for ECP utility comparison
            if 'non_cooperative' in scenario_name.lower():
                continue

            if isinstance(scenario_data, pd.DataFrame):
                if 'ecp_utility' in scenario_data.columns and not scenario_data.empty:
                    ecp_val = scenario_data['ecp_utility'].iloc[0]
                    sys_val = scenario_data['system_utility'].iloc[0]

                    if isinstance(ecp_val, str):
                        ecp_dict = eval(ecp_val)
                        sys_dict = eval(sys_val)
                        ecp_utilities.append(ecp_dict.get('mean', 0.0))
                        system_utilities.append(sys_dict.get('mean', 0.0))
                        scenarios.append(scenario_name.replace('_', ' ').title())

        if not scenarios:
            logger.warning("No valid scenario data found")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_title("Performance Comparison (No Data)")
            self._save_plot(fig, output_file)
            return

        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: ECP Utility
        x_pos = range(len(scenarios))
        colors = ['orange', 'yellow', 'lightgreen', 'green', 'darkgreen'][:len(scenarios)]
        bars1 = ax1.bar(x_pos, ecp_utilities, color=colors, alpha=0.7, edgecolor='black')

        for bar, util in zip(bars1, ecp_utilities):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{util:.0f}',
                    ha='center', va='bottom', fontsize=9)

        ax1.set_xlabel('Scenario', fontsize=11)
        ax1.set_ylabel('ECP Utility', fontsize=11)
        ax1.set_title('ECP Utility by Scenario', fontsize=12, fontweight='bold')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y')

        # Plot 2: System Utility
        bars2 = ax2.bar(x_pos, system_utilities, color=colors, alpha=0.7, edgecolor='black')

        for bar, util in zip(bars2, system_utilities):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{util:.0f}',
                    ha='center', va='bottom', fontsize=9)

        ax2.set_xlabel('Scenario', fontsize=11)
        ax2.set_ylabel('System Utility', fontsize=11)
        ax2.set_title('System Utility by Scenario', fontsize=12, fontweight='bold')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        self._save_plot(fig, output_file)
        logger.info(f"Performance comparison plot saved to {output_file}")

    def plot_performance_vs_miners(self, results_dict: Dict[str, Any], output_file: str = "fig2_performance_vs_miners.pdf"):
        """
        Plot coalition size and block discovery metrics.

        Since we don't have miner count sweep data, we show coalition formation patterns.
        """
        if not results_dict:
            logger.warning("plot_performance_vs_miners: No data provided")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_title("Coalition Analysis (No Data)")
            self._save_plot(fig, output_file)
            return

        # Extract metrics
        scenarios = []
        coalition_sizes = []
        blocks_found = []

        for scenario_name, scenario_data in results_dict.items():
            if isinstance(scenario_data, pd.DataFrame):
                if not scenario_data.empty:
                    coal_val = scenario_data['avg_coalition_size'].iloc[0]
                    blocks_val = scenario_data['blocks_found'].iloc[0]

                    if isinstance(coal_val, str):
                        coal_dict = eval(coal_val)
                        coalition_sizes.append(coal_dict.get('mean', 0.0))
                    else:
                        coalition_sizes.append(float(coal_val))

                    blocks_found.append(float(blocks_val))
                    scenarios.append(scenario_name.replace('_', ' ').title())

        if not scenarios:
            logger.warning("No valid scenario data found")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_title("Coalition Analysis (No Data)")
            self._save_plot(fig, output_file)
            return

        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: Coalition Sizes
        x_pos = range(len(scenarios))
        colors_map = {
            'Non Cooperative': 'red',
            'Single Coalition': 'orange',
            'Multi Coalition J3 Naive': 'yellow',
            'Enhanced J3': 'lightgreen',
            'Enhanced J5': 'green',
            'Enhanced J7': 'darkgreen'
        }
        colors = [colors_map.get(s, 'blue') for s in scenarios]

        bars1 = ax1.bar(x_pos, coalition_sizes, color=colors, alpha=0.7, edgecolor='black')

        for bar, size in zip(bars1, coalition_sizes):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{size:.1f}',
                    ha='center', va='bottom', fontsize=9)

        ax1.set_xlabel('Scenario', fontsize=11)
        ax1.set_ylabel('Average Coalition Size', fontsize=11)
        ax1.set_title('Coalition Formation Patterns', fontsize=12, fontweight='bold')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y')

        # Plot 2: Blocks Found
        bars2 = ax2.bar(x_pos, blocks_found, color=colors, alpha=0.7, edgecolor='black')

        for bar, blocks in zip(bars2, blocks_found):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{blocks:.1f}',
                    ha='center', va='bottom', fontsize=9)

        ax2.set_xlabel('Scenario', fontsize=11)
        ax2.set_ylabel('Blocks Found', fontsize=11)
        ax2.set_title('Block Discovery Performance', fontsize=12, fontweight='bold')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        self._save_plot(fig, output_file)
        logger.info(f"Coalition analysis plot saved to {output_file}")

    def plot_bandwidth_efficiency(self, results_dict: Dict[str, Any], output_file: str = "fig3_bandwidth_efficiency.pdf"):
        """
        Plot bandwidth efficiency comparison across scenarios.

        Shows bandwidth consumption for naive (without Bloom filters) vs
        optimized (with Bloom filters) approaches.

        Args:
            results_dict: Dictionary with scenario results containing bandwidth_kb data
            output_file: Output filename for the plot
        """
        if not results_dict:
            logger.warning("plot_bandwidth_efficiency: No data provided")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_title("Bandwidth Efficiency (No Data)")
            ax.set_xlabel("Scenario")
            ax.set_ylabel("Bandwidth (KB/s)")
            self._save_plot(fig, output_file)
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        # Extract bandwidth data from scenarios
        scenarios = []
        bandwidths = []
        colors = []

        # Map scenarios to J values and colors
        scenario_mapping = {
            'Non-Cooperative': (0, 'red'),
            'Single Coalition (J=1)': (1, 'orange'),
            'Multi-Coalition (J=3 Naive)': (3, 'yellow'),
            'Enhanced (J=3)': (3, 'lightgreen'),
            'Enhanced (J=5)': (5, 'green'),
            'Enhanced (J=7)': (7, 'darkgreen'),
        }

        for scenario_name, scenario_data in results_dict.items():
            bandwidth_mean = None

            # Handle both DataFrame (loaded from CSV) and dict (direct results)
            if isinstance(scenario_data, pd.DataFrame):
                # Data loaded from CSV
                if 'avg_bandwidth_kb' in scenario_data.columns and not scenario_data.empty:
                    bw_value = scenario_data['avg_bandwidth_kb'].iloc[0]
                    if isinstance(bw_value, str):
                        # Parse string representation of dict
                        bw_dict = eval(bw_value)
                        bandwidth_mean = bw_dict.get('mean', 0.0)
                    else:
                        bandwidth_mean = float(bw_value)
            elif isinstance(scenario_data, dict) and 'avg_bandwidth_kb' in scenario_data:
                # Direct results dict
                bw_data = scenario_data['avg_bandwidth_kb']
                if isinstance(bw_data, dict):
                    bandwidth_mean = bw_data.get('mean', 0.0)
                else:
                    bandwidth_mean = float(bw_data)

            if bandwidth_mean is not None and bandwidth_mean > 0:
                scenarios.append(scenario_name)
                bandwidths.append(bandwidth_mean)

                # Assign color based on scenario type
                if scenario_name in scenario_mapping:
                    _, color = scenario_mapping[scenario_name]
                    colors.append(color)
                else:
                    colors.append('blue')

        if not scenarios:
            logger.warning("No bandwidth data found in results")
            ax.set_title("Bandwidth Efficiency (No Data)")
            ax.set_xlabel("Scenario")
            ax.set_ylabel("Bandwidth (KB/s)")
            self._save_plot(fig, output_file)
            return

        # Create bar plot
        x_pos = range(len(scenarios))
        bars = ax.bar(x_pos, bandwidths, color=colors, alpha=0.7, edgecolor='black')

        # Add value labels on bars
        for i, (bar, bandwidth) in enumerate(zip(bars, bandwidths)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{bandwidth:.1f}',
                   ha='center', va='bottom', fontsize=9)

        ax.set_xlabel('Scenario', fontsize=12)
        ax.set_ylabel('Bandwidth Consumption (KB/s)', fontsize=12)
        ax.set_title('Bandwidth Efficiency: Naive vs Bloom Filter Optimization', fontsize=14, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(scenarios, rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')

        # Add legend explaining colors
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='red', alpha=0.7, label='Non-Cooperative'),
            Patch(facecolor='orange', alpha=0.7, label='Baseline (J=1)'),
            Patch(facecolor='yellow', alpha=0.7, label='Naive Multi-Coalition'),
            Patch(facecolor='lightgreen', alpha=0.7, label='Enhanced (Bloom Filter)'),
            Patch(facecolor='green', alpha=0.7, label='Enhanced J=5'),
            Patch(facecolor='darkgreen', alpha=0.7, label='Enhanced J=7'),
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=9)

        plt.tight_layout()
        self._save_plot(fig, output_file)
        logger.info(f"Bandwidth efficiency plot saved to {output_file}")

    def plot_ecp_cost_savings(self, results_dict: Dict[str, Any], output_file: str = "fig4_ecp_cost_savings.pdf"):
        """
        Plot ECP utility and nonce length comparison.

        Shows ECP demand and efficiency across scenarios.
        """
        if not results_dict:
            logger.warning("plot_ecp_cost_savings: No data provided")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_title("ECP Analysis (No Data)")
            self._save_plot(fig, output_file)
            return

        # Extract ECP metrics
        scenarios = []
        ecp_utilities = []
        nonce_lengths = []

        for scenario_name, scenario_data in results_dict.items():
            # Skip non-cooperative (no ECP)
            if 'non_cooperative' in scenario_name.lower():
                continue

            if isinstance(scenario_data, pd.DataFrame):
                if not scenario_data.empty:
                    ecp_val = scenario_data['ecp_utility'].iloc[0]
                    nonce_val = scenario_data['avg_nonce_length'].iloc[0]

                    if isinstance(ecp_val, str):
                        ecp_dict = eval(ecp_val)
                        nonce_dict = eval(nonce_val)
                        ecp_utilities.append(ecp_dict.get('mean', 0.0))
                        nonce_lengths.append(nonce_dict.get('mean', 0.0))
                        scenarios.append(scenario_name.replace('_', ' ').title())

        if not scenarios:
            logger.warning("No valid ECP data found")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_title("ECP Analysis (No Data)")
            self._save_plot(fig, output_file)
            return

        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: ECP Utility
        x_pos = range(len(scenarios))
        colors = ['orange', 'yellow', 'lightgreen', 'green', 'darkgreen'][:len(scenarios)]

        bars1 = ax1.bar(x_pos, ecp_utilities, color=colors, alpha=0.7, edgecolor='black')

        for bar, util in zip(bars1, ecp_utilities):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{util:.0f}',
                    ha='center', va='bottom', fontsize=9)

        ax1.set_xlabel('Scenario', fontsize=11)
        ax1.set_ylabel('ECP Utility', fontsize=11)
        ax1.set_title('ECP Revenue by Scenario', fontsize=12, fontweight='bold')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y')

        # Plot 2: Nonce Length (ECP Demand)
        bars2 = ax2.bar(x_pos, nonce_lengths, color=colors, alpha=0.7, edgecolor='black')

        for bar, nonce in zip(bars2, nonce_lengths):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{nonce:.0f}',
                    ha='center', va='bottom', fontsize=9)

        ax2.set_xlabel('Scenario', fontsize=11)
        ax2.set_ylabel('ECP Compute Demand (Nonce Length)', fontsize=11)
        ax2.set_title('ECP Compute Usage by Scenario', fontsize=12, fontweight='bold')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')

        # Add annotation about constant values
        fig.text(0.5, 0.02, 'Note: ECP utility and demand are currently constant across scenarios (see analysis for details)',
                ha='center', fontsize=9, style='italic', color='gray')

        plt.tight_layout(rect=[0, 0.03, 1, 1])
        self._save_plot(fig, output_file)
        logger.info(f"ECP analysis plot saved to {output_file}")

    def plot_latency_comparison(self, latency_data: Dict[str, List[float]], output_file: str = "fig5_latency_comparison.pdf"):
        """
        Generates a box plot comparing latency distributions.

        Args:
            latency_data (Dict[str, List[float]]): Dict with keys like 'WebSocket only',
                                                   'Dual-channel' and lists of latencies as values.
        """
        fig, ax = plt.subplots(figsize=(8, 6))

        # Filter out infinities and NaNs from all series
        cleaned_data = {}
        for key, values in latency_data.items():
            cleaned_values = [v for v in values if not (v == float('inf') or v == float('-inf') or pd.isna(v))]
            if cleaned_values:  # Only include if we have data
                cleaned_data[key] = cleaned_values

        # Create DataFrame in long format for seaborn (handles unequal lengths)
        data_list = []
        for protocol, latencies in cleaned_data.items():
            for latency in latencies:
                data_list.append({'Protocol': protocol, 'Latency (ms)': latency})

        df = pd.DataFrame(data_list)

        sns.boxplot(data=df, x='Protocol', y='Latency (ms)', ax=ax, palette=self.palette)

        ax.set_title("Latency Comparison for Result Delivery")
        ax.set_ylabel("Latency (ms)")

        # Calculate and show improvement
        if 'WebSocket only' in cleaned_data and 'Dual-channel' in cleaned_data:
            median_ws = pd.Series(cleaned_data['WebSocket only']).median()
            median_dual = pd.Series(cleaned_data['Dual-channel']).median()
            improvement = ((median_ws - median_dual) / median_ws) * 100
            ax.text(0.5, 0.95, f'{improvement:.0f}% latency improvement',
                   ha='center', va='top', transform=ax.transAxes,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        self._save_plot(fig, output_file)

    def plot_system_comparison(self, all_results: Dict[str, Any], output_file: str = "fig6_system_comparison.pdf"):
        """
        Generates a bar chart with error bars comparing system utility across scenarios.

        Args:
            all_results (Dict[str, Any]): Dictionary of results for all scenarios.
                                           Values can be dicts or pandas DataFrames.
        """
        labels = []
        means = []
        error_margins = []

        for scenario, results in all_results.items():
            utility_data = None
            if isinstance(results, pd.DataFrame):
                # Data is from a loaded CSV
                if 'system_utility' in results.columns and not results.empty:
                    utility_str = results['system_utility'].iloc[0]
                    try:
                        utility_data = ast.literal_eval(utility_str)
                    except (ValueError, SyntaxError):
                        logger.warning(f"Could not parse utility data for {scenario}: {utility_str}")
                        continue
            elif isinstance(results, dict):
                # Data is from a direct simulation run
                utility_data = results.get('system_utility')

            if utility_data and isinstance(utility_data, dict) and 'mean' in utility_data:
                labels.append(scenario)
                means.append(utility_data['mean'])
                # Handle cases where CI might not be present in all dicts
                ci_lower = utility_data.get('ci_lower', utility_data['mean'])
                # Fallback for older format that might not have ci_95
                if 'ci_95' in utility_data and isinstance(utility_data['ci_95'], tuple) and len(utility_data['ci_95']) > 0:
                    ci_lower = utility_data['ci_95'][0]

                error = utility_data['mean'] - ci_lower
                error_margins.append(error)

        if not labels:
            logger.warning("Not enough data to plot system comparison. No valid system_utility columns found in results.")
            # Create an empty plot to avoid crashing
            fig, ax = plt.subplots(figsize=(10, 7))
            ax.set_title("System Utility Comparison Across Scenarios (No Data)")
            ax.text(0.5, 0.5, "No data available to generate this plot.", ha='center', va='center')
            self._save_plot(fig, output_file)
            return

        fig, ax = plt.subplots(figsize=(10, 7))
        x = range(len(labels))
        
        ax.bar(x, means, yerr=error_margins, capsize=5, color=self.palette[0], ecolor='gray')
        
        ax.set_title("System Utility Comparison Across Scenarios")
        ax.set_ylabel("System Utility")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
        
        # Add improvement percentages above bars
        baseline_mean = means[0] if means else 0
        for i, mean in enumerate(means):
            if i > 0 and baseline_mean > 0:
                improvement = ((mean - baseline_mean) / baseline_mean) * 100
                ax.text(i, mean + error_margins[i] * 1.1, f'+{improvement:.1f}%', ha='center', color='green')

        self._save_plot(fig, output_file)


    def generate_all_figures(self, results_data: Dict[str, Any]):
        """
        Calls all plotting methods to generate all defined figures.

        Args:
            results_data (Dict[str, Any]): A dictionary containing all necessary data
                                            for all plots.
        """
        logger.info("Generating all figures...")
        
        # These calls assume `results_data` is structured correctly.
        # This will likely need to be adapted once the data structure is finalized.
        self.plot_performance_vs_price(results_data.get('price_sweep'), "fig1_performance_vs_price.pdf")
        self.plot_performance_vs_miners(results_data.get('miners_sweep'), "fig2_performance_vs_miners.pdf")
        self.plot_bandwidth_efficiency(results_data.get('bandwidth_data'), "fig3_bandwidth_efficiency.pdf")
        self.plot_ecp_cost_savings(results_data.get('cost_savings_data'), "fig4_ecp_cost_savings.pdf")
        self.plot_latency_comparison(results_data.get('latency_data'), "fig5_latency_comparison.pdf")
        self.plot_system_comparison(results_data.get('all_scenarios'), "fig6_system_comparison.pdf")
        
        logger.info("All figures generated.")