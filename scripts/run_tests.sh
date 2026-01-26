#!/bin/bash
# Test runner script for Manifest project
# Provides convenient commands for running different test suites

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Default values
TEST_TYPE="all"
VERBOSE=false
COVERAGE=false
MARKERS=""
DURATIONS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -m|--marker)
            MARKERS="$2"
            shift 2
            ;;
        -d|--durations)
            DURATIONS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -t, --type TYPE       Test type: all, unit, integration (default: all)"
            echo "  -v, --verbose         Verbose output"
            echo "  -c, --coverage        Generate coverage report"
            echo "  -m, --marker MARKER   Run tests with specific marker"
            echo "  -d, --durations       Show slowest tests"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 -t unit                    # Run unit tests only"
            echo "  $0 -t integration             # Run integration tests only"
            echo "  $0 -c                        # Run all tests with coverage"
            echo "  $0 -m 'not integration'       # Run all tests except integration"
            echo "  $0 -v -d                     # Verbose with durations"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="python -m pytest"

# Add test path based on type
case $TEST_TYPE in
    unit)
        PYTEST_CMD="$PYTEST_CMD tests/unit/"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD tests/integration/"
        ;;
    all)
        PYTEST_CMD="$PYTEST_CMD tests/"
        ;;
    *)
        echo "Unknown test type: $TEST_TYPE"
        echo "Use: all, unit, or integration"
        exit 1
        ;;
esac

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -q"
fi

# Add coverage
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src/manifest --cov-report=term-missing --cov-report=html"
fi

# Add markers
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m \"$MARKERS\""
fi

# Add durations
if [ "$DURATIONS" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --durations=10"
fi

# Run tests
echo "Running: $PYTEST_CMD"
echo ""
eval $PYTEST_CMD
