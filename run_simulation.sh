#!/bin/bash

###############################################################################
# Multi-Coalition Blockchain Mining Simulation - Sequential Execution Script
###############################################################################
#
# This script runs the complete blockchain mining simulation in sequential steps:
# 1. Environment validation
# 2. Scenario execution (quick or full)
# 3. Parameter sweeps (full mode only)
# 4. Visualization and export
#
# Usage:
#   ./run_simulation.sh [options]
#
# Options:
#   --quick          Run a minimal set of scenarios for a quick validation.
#   --baseline-only  Run only baseline scenarios (full mode)
#   --enhanced-only  Run only enhanced scenarios (full mode)
#   --no-viz         Skip visualization generation
#   --help           Show this help message
#
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
QUICK_MODE=false
BASELINE_ONLY=false
ENHANCED_ONLY=false
NO_VIZ=false
RUNS=500

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            RUNS=5
            shift
            ;;
        --baseline-only)
            BASELINE_ONLY=true
            shift
            ;;
        --enhanced-only)
            ENHANCED_ONLY=true
            shift
            ;;
        --no-viz)
            NO_VIZ=true
            shift
            ;;
        --help)
            head -n 30 "$0" | grep "^#" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print header
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Multi-Coalition Blockchain Mining Simulation                ║"
echo "║  Sequential Execution Script                                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Print configuration
echo -e "${YELLOW}Configuration:${NC}"
echo "  - Quick mode: $QUICK_MODE"
echo "  - Number of runs: $RUNS"
echo "  - Baseline only: $BASELINE_ONLY"
echo "  - Enhanced only: $ENHANCED_ONLY"
echo "  - Skip visualization: $NO_VIZ"
echo ""

###############################################################################
# Step 1: Environment Validation
###############################################################################

echo -e "${BLUE}Step 1: Validating environment...${NC}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo -e "${YELLOW}Warning: Virtual environment not found. Please run setup.${NC}"
fi

# Check if dependencies are installed
echo "Checking dependencies..."
if ! python -c "import numpy, scipy, pandas, matplotlib, seaborn" 2>/dev/null; then
    echo -e "${RED}Error: Dependencies not installed. Please run 'pip install -r requirements.txt'${NC}"
    exit 1
fi
echo -e "${GREEN}✓ All dependencies installed${NC}"

# Create output directories
echo "Creating output directories..."
mkdir -p results figures
echo -e "${GREEN}✓ Output directories created${NC}"

echo ""

###############################################################################
# Step 2: Scenario Execution
###############################################################################

if [ "$QUICK_MODE" = true ]; then
    # Quick mode: Run all scenarios required for the comparison graph, but with minimal runs.
    echo -e "${BLUE}Step 2: Running scenarios for comparison graph (Quick Mode)...${NC}"

    echo -e "${YELLOW}[2.1] Running Non-Cooperative...${NC}"
    python main.py --scenario=non_cooperative --runs=$RUNS --output=results/non_cooperative.csv
    
    echo -e "${YELLOW}[2.2] Running Single Coalition (J=1)...${NC}"
    python main.py --scenario=single_coalition --runs=$RUNS --output=results/single_coalition.csv

    echo -e "${YELLOW}[2.3] Running Multi-Coalition (J=3 Naive)...${NC}"
    python main.py --scenario=multi_coalition_j3_naive --runs=$RUNS --output=results/multi_coalition_j3_naive.csv

    echo -e "${YELLOW}[2.4] Running Enhanced (J=3)...${NC}"
    python main.py --scenario=enhanced_j3 --runs=$RUNS --output=results/enhanced_j3.csv

    echo -e "${YELLOW}[2.5] Running Enhanced (J=5)...${NC}"
    python main.py --scenario=enhanced_j5 --runs=$RUNS --output=results/enhanced_j5.csv

    echo -e "${YELLOW}[2.6] Running Enhanced (J=7)...${NC}"
    python main.py --scenario=enhanced_j7 --runs=$RUNS --output=results/enhanced_j7.csv

    echo -e "${GREEN}✓ All scenarios for graph completed.${NC}"
    echo -e "${YELLOW}Skipping parameter sweeps and validation in Quick Mode.${NC}"
    echo ""

else
    # Full mode: Run all scenarios and sweeps

    # Step 2.1: Baseline Scenarios
    if [ "$ENHANCED_ONLY" = false ]; then
        echo -e "${BLUE}Step 2: Running baseline scenarios (Paper replication)...${NC}"
        python main.py --scenario=non_cooperative --runs=$RUNS --output=results/non_cooperative.csv
        python main.py --scenario=single_coalition --runs=$RUNS --output=results/single_coalition.csv
        python main.py --scenario=multi_coalition_j2 --runs=$RUNS --output=results/multi_coalition_j2.csv
        python main.py --scenario=multi_coalition_j3_naive --runs=$RUNS --output=results/multi_coalition_j3_naive.csv
        echo -e "${GREEN}✓✓ All baseline scenarios completed${NC}"
        echo ""
    fi

    # Step 2.2: Enhanced Scenarios
    if [ "$BASELINE_ONLY" = false ]; then
        echo -e "${BLUE}Step 3: Running enhanced scenarios (With innovations)...${NC}"
        python main.py --scenario=enhanced_j3 --runs=$RUNS --output=results/enhanced_j3.csv
        python main.py --scenario=enhanced_j5 --runs=$RUNS --output=results/enhanced_j5.csv
        python main.py --scenario=enhanced_j7 --runs=$RUNS --output=results/enhanced_j7.csv
        echo -e "${GREEN}✓✓ All enhanced scenarios completed${NC}"
        echo ""
    fi

    # Step 2.3: Parameter Sweeps
    echo -e "${BLUE}Step 4: Running parameter sweeps...${NC}"
    python main.py --sweep=price --range=0,450,25 --runs=$((RUNS/5)) --output=results/sweep_price.csv
    python main.py --sweep=miners --range=2,30,2 --runs=$((RUNS/5)) --output=results/sweep_miners.csv
    python main.py --sweep=transactions --range=5,15,1 --runs=$((RUNS/5)) --output=results/sweep_transactions.csv
    python main.py --sweep=block_reward --range=500,2000,100 --runs=$((RUNS/5)) --output=results/sweep_block_reward.csv
    echo -e "${GREEN}✓✓ All parameter sweeps completed${NC}"
    echo ""

    # Step 2.4: Validation
    echo -e "${BLUE}Step 5: Validating results against paper...${NC}"
    python main.py --validate --tolerance=0.05
    echo -e "${GREEN}✓ Validation completed${NC}"
    echo ""
fi


###############################################################################
# Step 3: Visualization Generation & Reporting
###############################################################################

# These steps run in both full and quick mode, operating on generated results.

if [ "$NO_VIZ" = false ]; then
    echo -e "${BLUE}Step 6: Generating visualizations...${NC}"
    # The --visualize flag without a specific --figure number generates all figures.
    python main.py --visualize --output-dir=figures/
    echo -e "${GREEN}✓ Visualizations generated in figures/ directory${NC}"
    echo ""
fi

echo -e "${BLUE}Step 7: Exporting results summary...${NC}"
python main.py --export --format=csv --output=results/summary_statistics.csv
echo -e "${GREEN}✓ Results exported${NC}"
echo ""

echo -e "${BLUE}Step 8: Generating simulation report...${NC}"
# Generate a simplified report
cat > results/SIMULATION_REPORT.txt << EOF
╔═══════════════════════════════════════════════════════════════╗
║  Multi-Coalition Blockchain Mining Simulation - Final Report  ║
╚═══════════════════════════════════════════════════════════════╝

Execution Date: $(date)
Configuration: $RUNS runs per scenario
Quick Mode: $QUICK_MODE

This report summarizes the results from the simulation run. For detailed
metrics, please see the CSV files in the 'results/' directory.

Key Figures:
- See the 'figures/' directory for generated plots.

EOF
cat results/SIMULATION_REPORT.txt
echo -e "${GREEN}✓ Report generated: results/SIMULATION_REPORT.txt${NC}"
echo ""


###############################################################################
# Completion
###############################################################################

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                  SIMULATION COMPLETED!                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "Total execution time: $SECONDS seconds"
echo ""
echo "Results summary:"
echo "  - Results directory: results/"
echo "  - Figures directory: figures/"
echo "  - Summary report: results/SIMULATION_REPORT.txt"
echo ""

# Deactivate virtual environment
deactivate