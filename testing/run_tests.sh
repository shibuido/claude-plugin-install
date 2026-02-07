#!/usr/bin/env bash
set -euo pipefail

# run_tests.sh -- Docker-based E2E test runner for claude-plugin-install
#
# Builds a Docker image with the tool and test infrastructure,
# then runs each test in an ephemeral container.
#
# Usage:
#   ./testing/run_tests.sh              # run all tests
#   ./testing/run_tests.sh 01-help      # run a specific test
#   ./testing/run_tests.sh list         # list available tests
#   ./testing/run_tests.sh cleanup      # remove Docker image
#   ./testing/run_tests.sh --help       # show usage

# --- Configuration ---
DOCKER_PREFIX="${DOCKER_PREFIX:-cpi-test}"
IMAGE_NAME="${DOCKER_PREFIX}-image"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBOSE="${VERBOSE:-0}"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# --- Functions ---

show_help() {
    cat <<'EOF'
Usage: ./testing/run_tests.sh [OPTIONS] [TEST_NAME...]

Run Docker-based E2E tests for claude-plugin-install.
Automatically builds the Docker image before running tests.

Options:
  --help, -h, help          Show this help message
  --list, list,
  --list-tests, list-tests  List available tests
  --cleanup, cleanup        Remove the Docker test image
  -v, --verbose             Show Docker build output and extra diagnostics

Arguments:
  TEST_NAME                 Run specific test(s) by name (e.g., 01-help 05-install-local)
                           If no test names given, runs all tests.

Examples:
  ./testing/run_tests.sh                    # run all tests
  ./testing/run_tests.sh 01-help            # run one test
  ./testing/run_tests.sh 01-help 05-install-local  # run multiple tests
  ./testing/run_tests.sh list               # list available tests
  ./testing/run_tests.sh cleanup            # remove Docker image
  ./testing/run_tests.sh -v                 # verbose: show build output

Environment:
  DOCKER_PREFIX   Prefix for Docker artifacts (default: cpi-test)
                  Image will be named: ${DOCKER_PREFIX}-image
  VERBOSE         Set to 1 for verbose output (same as -v)
EOF
}

# Discover and list all tests from testing/tests/*/test.sh
list_tests() {
    echo -e "${CYAN}Available tests:${RESET}"
    local count=0
    for test_dir in "$PROJECT_ROOT"/testing/tests/*/; do
        local test_name
        test_name="$(basename "$test_dir")"
        if [[ -f "$test_dir/test.sh" ]]; then
            echo "  $test_name"
            ((count++)) || true
        fi
    done
    echo ""
    echo "Total: $count tests"
}

# Build the Docker test image from the project root
# Suppresses output unless VERBOSE=1 or build fails
build_image() {
    echo -e "${CYAN}Building test image...${RESET}"
    local build_log
    build_log=$(mktemp)
    if [[ "$VERBOSE" == "1" ]]; then
        docker build \
            -t "$IMAGE_NAME" \
            -f "$PROJECT_ROOT/testing/Dockerfile" \
            "$PROJECT_ROOT" 2>&1 | tee "$build_log"
        local build_exit=${PIPESTATUS[0]}
    else
        docker build \
            -t "$IMAGE_NAME" \
            -f "$PROJECT_ROOT/testing/Dockerfile" \
            "$PROJECT_ROOT" > "$build_log" 2>&1
        local build_exit=$?
    fi
    if [[ $build_exit -ne 0 ]]; then
        echo -e "${RED}Docker build failed:${RESET}"
        cat "$build_log"
        rm -f "$build_log"
        exit 1
    fi
    rm -f "$build_log"
    echo -e "${GREEN}Image ready: ${IMAGE_NAME}${RESET}"
}

# Run a single test in an ephemeral container
# Arguments: test_name
# Returns: 0 if test passed, 1 if failed
run_test() {
    local test_name="$1"
    local test_script="/workspace/testing/tests/${test_name}/test.sh"

    # Verify test exists locally before trying to run
    if [[ ! -f "$PROJECT_ROOT/testing/tests/${test_name}/test.sh" ]]; then
        echo -e "  ${RED}FAIL${RESET}: Test '${test_name}' not found"
        return 1
    fi

    echo -e "${CYAN}--- ${test_name} ---${RESET}"

    local output
    local exit_code=0
    output=$(docker run --rm "$IMAGE_NAME" "$test_script" 2>&1) || exit_code=$?

    echo "$output"

    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}>>> PASS: ${test_name}${RESET}"
        return 0
    else
        echo -e "${RED}>>> FAIL: ${test_name} (exit code: ${exit_code})${RESET}"
        return 1
    fi
}

# Run all tests sequentially, track pass/fail counts, print summary
run_all_tests() {
    local total=0
    local passed=0
    local failed=0
    local failed_names=()

    for test_dir in "$PROJECT_ROOT"/testing/tests/*/; do
        local test_name
        test_name="$(basename "$test_dir")"
        if [[ ! -f "$test_dir/test.sh" ]]; then
            continue
        fi
        ((total++)) || true
        echo ""
        if run_test "$test_name"; then
            ((passed++)) || true
        else
            ((failed++)) || true
            failed_names+=("$test_name")
        fi
    done

    # --- Summary ---
    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}  TEST SUMMARY${RESET}"
    echo -e "${BOLD}═══════════════════════════════════════════════${RESET}"
    echo -e "  Total:  ${total}"
    echo -e "  ${GREEN}Passed: ${passed}${RESET}"
    echo -e "  ${RED}Failed: ${failed}${RESET}"

    if [[ ${#failed_names[@]} -gt 0 ]]; then
        echo ""
        echo -e "${RED}  Failed tests:${RESET}"
        for name in "${failed_names[@]}"; do
            echo -e "    ${RED}- ${name}${RESET}"
        done
    fi

    echo -e "${BOLD}═══════════════════════════════════════════════${RESET}"

    [[ $failed -eq 0 ]] && return 0 || return 1
}

# Remove Docker image
cleanup() {
    echo -e "${YELLOW}Cleaning up Docker artifacts...${RESET}"
    if docker image inspect "$IMAGE_NAME" &>/dev/null; then
        docker rmi "$IMAGE_NAME"
        echo -e "${GREEN}Removed image: ${IMAGE_NAME}${RESET}"
    else
        echo "  Image '${IMAGE_NAME}' not found, nothing to clean."
    fi
}

# --- Pre-flight check ---
check_project_root() {
    if [[ ! -f "$PROJECT_ROOT/claude-plugin-install" ]]; then
        echo -e "${RED}ERROR: claude-plugin-install not found in project root: ${PROJECT_ROOT}${RESET}" >&2
        echo "  This script must be run from the project root or via testing/run_tests.sh" >&2
        exit 1
    fi
    if [[ ! -d "$PROJECT_ROOT/testing/tests" ]]; then
        echo -e "${RED}ERROR: testing/tests directory not found in: ${PROJECT_ROOT}${RESET}" >&2
        exit 1
    fi
}

# --- Main ---
check_project_root

# Parse arguments: separate flags from test names
test_names=()
action=""

for arg in "$@"; do
    case "$arg" in
        --help|-h|help)
            show_help
            exit 0
            ;;
        --list|list|--list-tests|list-tests)
            list_tests
            exit 0
            ;;
        --cleanup|cleanup)
            cleanup
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=1
            ;;
        *)
            test_names+=("$arg")
            ;;
    esac
done

# Auto-build image, then run tests
build_image

if [[ ${#test_names[@]} -eq 0 ]]; then
    # No specific tests — run all
    run_all_tests
    exit $?
else
    # Run specific tests
    total=0
    passed=0
    failed=0
    failed_names=()

    for test_name in "${test_names[@]}"; do
        ((total++)) || true
        echo ""
        if run_test "$test_name"; then
            ((passed++)) || true
        else
            ((failed++)) || true
            failed_names+=("$test_name")
        fi
    done

    echo ""
    echo -e "${BOLD}═══════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}  TEST SUMMARY${RESET}"
    echo -e "${BOLD}═══════════════════════════════════════════════${RESET}"
    echo -e "  Total:  ${total}"
    echo -e "  ${GREEN}Passed: ${passed}${RESET}"
    echo -e "  ${RED}Failed: ${failed}${RESET}"

    if [[ ${#failed_names[@]} -gt 0 ]]; then
        echo ""
        echo -e "${RED}  Failed tests:${RESET}"
        for name in "${failed_names[@]}"; do
            echo -e "    ${RED}- ${name}${RESET}"
        done
    fi

    echo -e "${BOLD}═══════════════════════════════════════════════${RESET}"
    [[ $failed -eq 0 ]] && exit 0 || exit 1
fi
