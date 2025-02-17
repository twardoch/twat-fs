#!/usr/bin/env bash
# this_file: 02-check.sh

set -e # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
SINGLE_REPO=""
while [[ $# -gt 0 ]]; do
    case $1 in
    --repo=*)
        SINGLE_REPO="${1#*=}"
        if [[ ! "$SINGLE_REPO" =~ ^(twardown-py|twardown-js|twardown-docs|twardown-org)$ ]]; then
            echo "Error: Invalid repository name. Must be one of: twardown-py, twardown-js, twardown-docs, twardown-org"
            exit 1
        fi
        shift
        ;;
    *)
        echo "Unknown option: $1"
        echo "Usage: $0 [--repo=name]"
        echo "  name: One of twardown-py, twardown-js, twardown-docs, twardown-org"
        exit 1
        ;;
    esac
done

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
}

# Function to check command existence
check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo -e "${RED}Error: $1 is required but not installed.${NC}"
        exit 1
    fi
}

# Check required commands
check_command tree
check_command python
check_command node
check_command npm
check_command gh

print_header "Project Structure"
if [ -n "$SINGLE_REPO" ]; then
    tree -a -I '.git|.venv|node_modules|__pycache__|*.pyc|dist|build|*.egg-info' "$SINGLE_REPO" >tree.txt
else
    tree -a -I '.git|.venv|node_modules|__pycache__|*.pyc|dist|build|*.egg-info' >tree.txt
fi
cat tree.txt

check_python_package() {
    cd twardown-py || exit 1
    print_header "Python Package Status"
    echo -e "${YELLOW}Python version:${NC}"
    python --version
    echo -e "${YELLOW}Running tests:${NC}"
    if [ -d ".venv" ]; then
        source .venv/bin/activate || exit 1
    else
        if ! command -v uv &>/dev/null; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
        fi
        uv venv
        source .venv/bin/activate || exit 1
    fi
    uv pip install -e ".[dev]"
    python -m pytest --cov=twardown_py tests/ || echo -e "${RED}Tests failed${NC}"
    echo -e "${YELLOW}Running type checks:${NC}"
    mypy src/twardown_py || echo -e "${RED}Type checks failed${NC}"
    echo -e "${YELLOW}Running linting:${NC}"
    ruff check . || echo -e "${RED}Linting failed${NC}"
    ruff format --check . || echo -e "${RED}Format check failed${NC}"
    cd ..
}

check_javascript_package() {
    cd twardown-js || exit 1
    print_header "JavaScript Package Status"
    echo -e "${YELLOW}Node.js version:${NC}"
    node --version
    echo -e "${YELLOW}npm version:${NC}"
    npm --version
    echo -e "${YELLOW}Installing dependencies:${NC}"
    npm install
    echo -e "${YELLOW}Running tests:${NC}"
    npm test || echo -e "${RED}Tests failed${NC}"
    echo -e "${YELLOW}Running linting:${NC}"
    npm run lint || echo -e "${RED}Linting failed${NC}"
    npm run format:check || echo -e "${RED}Format check failed${NC}"
    cd ..
}

check_documentation() {
    cd twardown-docs || exit 1
    print_header "Documentation Status"
    echo -e "${YELLOW}Installing dependencies:${NC}"
    npm install
    cd ..
}

check_ci_status() {
    print_header "CI Status"
    if [ -n "$SINGLE_REPO" ]; then
        echo -e "${YELLOW}Checking GitHub Actions status for $SINGLE_REPO:${NC}"
        gh run list --repo "twardoch/$SINGLE_REPO" --limit 1 || echo -e "${RED}Failed to fetch CI status for $SINGLE_REPO${NC}"
    else
        echo -e "${YELLOW}Checking GitHub Actions status:${NC}"
        for repo in twardown-{py,js,docs,org}; do
            echo -e "\n${YELLOW}$repo:${NC}"
            gh run list --repo "twardoch/$repo" --limit 1 || echo -e "${RED}Failed to fetch CI status for $repo${NC}"
        done
    fi
}

check_git_status() {
    print_header "Git Status"
    if [ -n "$SINGLE_REPO" ]; then
        echo -e "\n${YELLOW}${SINGLE_REPO} repository:${NC}"
        (cd "$SINGLE_REPO" && git status)
    else
        for repo in . twardown-{py,js,docs}; do
            echo -e "\n${YELLOW}${repo#.} repository:${NC}"
            (cd "$repo" && git status)
        done
    fi
}

check_package_versions() {
    print_header "Package Versions"
    if [ -n "$SINGLE_REPO" ]; then
        case "$SINGLE_REPO" in
        twardown-py)
            echo -e "${YELLOW}Python package version:${NC}"
            grep 'version = ' twardown-py/pyproject.toml
            ;;
        twardown-js)
            echo -e "${YELLOW}JavaScript package version:${NC}"
            grep '"version":' twardown-js/package.json
            ;;
        twardown-docs)
            echo -e "${YELLOW}Documentation version:${NC}"
            grep '"version":' twardown-docs/package.json
            ;;
        esac
    else
        echo -e "${YELLOW}Python package version:${NC}"
        grep 'version = ' twardown-py/pyproject.toml
        echo -e "${YELLOW}JavaScript package version:${NC}"
        grep '"version":' twardown-js/package.json
        echo -e "${YELLOW}Documentation version:${NC}"
        grep '"version":' twardown-docs/package.json
    fi
}

# Run checks based on repository selection
if [ -n "$SINGLE_REPO" ]; then
    case "$SINGLE_REPO" in
    twardown-py)
        check_python_package
        ;;
    twardown-js)
        check_javascript_package
        ;;
    twardown-docs)
        check_documentation
        ;;
    esac
    check_ci_status
    check_git_status
    check_package_versions
else
    check_python_package
    check_javascript_package
    check_documentation
    check_ci_status
    check_git_status
    check_package_versions
fi

print_header "Check Complete"
echo "A detailed project tree has been saved to tree.txt"
