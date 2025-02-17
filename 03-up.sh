#!/usr/bin/env bash
# this_file: 03-up.sh

# Configuration
REPO_OWNER="twardoch"
REPOS=("twardown-py" "twardown-js" "twardown-docs" "twardown-org")
CI_WAIT_TIME=30 # seconds to wait for CI to start
DRY_RUN=false
SKIP_CI=false
LOG_FILE="update.log"
SINGLE_REPO=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
    --dry-run)
        DRY_RUN=true
        shift
        ;;
    --skip-ci)
        SKIP_CI=true
        shift
        ;;
    --owner=*)
        REPO_OWNER="${1#*=}"
        shift
        ;;
    --ci-wait=*)
        CI_WAIT_TIME="${1#*=}"
        shift
        ;;
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
        echo "Usage: $0 [--dry-run] [--skip-ci] [--owner=name] [--ci-wait=seconds] [--repo=name]"
        echo "  --repo=name: One of twardown-py, twardown-js, twardown-docs, twardown-org"
        exit 1
        ;;
    esac
done

set -e # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    local message=$1
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "$timestamp - $message" | tee -a "$LOG_FILE"
}

# Function to print section headers
print_header() {
    local message="=== $1 ==="
    log_message "\n${YELLOW}$message${NC}"
}

# Function to check if required files exist
check_files() {
    local repo=$1
    local missing=0

    # Ensure the repository directory exists
    if [ ! -d "$repo" ]; then
        log_message "${RED}Error: Repository directory $repo does not exist${NC}"
        return 1
    fi

    # Ensure it's a git repository
    if [ ! -d "$repo/.git" ] && [ ! -f "$repo/.git" ]; then
        log_message "${RED}Error: $repo is not a git repository${NC}"
        return 1
    fi

    # Check for required files
    for file in LOG.md README.md; do
        if [ ! -f "$repo/$file" ]; then
            log_message "${RED}Error: $repo/$file is missing${NC}"
            missing=1
        fi
    done

    if [ "$repo" = "." ] && [ ! -f "TODO.md" ]; then
        log_message "${RED}Error: TODO.md is missing in main repository${NC}"
        missing=1
    fi

    return $missing
}

# Function to check if a file has been modified
check_modified() {
    local file=$1
    if [ ! -f "$file" ]; then
        log_message "${RED}Error: File $file does not exist${NC}"
        return 1
    fi
    if git diff --quiet "$file"; then
        log_message "${YELLOW}No changes in $file${NC}"
        return 1
    else
        log_message "${GREEN}Changes detected in $file${NC}"
        return 0
    fi
}

# Function to check if CI is passing
check_ci_status() {
    local repo=$1
    local max_retries=3
    local retry_count=0

    if [ "$SKIP_CI" = true ]; then
        log_message "${YELLOW}Skipping CI check for $repo${NC}"
        return 0
    fi

    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        log_message "${RED}Error: GitHub CLI (gh) is not installed${NC}"
        return 1
    fi

    while [ $retry_count -lt $max_retries ]; do
        local status
        status=$(gh run list --repo "$REPO_OWNER/$repo" --limit 1 --json conclusion --jq '.[0].conclusion')

        if [ "$status" = "success" ]; then
            log_message "${GREEN}CI passing for $repo${NC}"
            return 0
        elif [ -z "$status" ]; then
            log_message "${YELLOW}No CI status available yet for $repo, waiting...${NC}"
            sleep "$CI_WAIT_TIME"
            retry_count=$((retry_count + 1))
        else
            log_message "${RED}CI not passing for $repo (status: $status)${NC}"
            return 1
        fi
    done

    log_message "${YELLOW}Warning: Could not get CI status for $repo after $max_retries attempts${NC}"
    return 0  # Don't fail the script if we can't get CI status
}

# Function to initialize/update submodules
init_submodules() {
    log_message "${YELLOW}Initializing/updating submodules...${NC}"
    git submodule update --init --recursive || {
        log_message "${RED}Error: Failed to initialize/update submodules${NC}"
        return 1
    }
    git submodule foreach git checkout main || {
        log_message "${RED}Error: Failed to checkout main branch in submodules${NC}"
        return 1
    }
    git submodule foreach git pull origin main || {
        log_message "${RED}Error: Failed to pull latest changes in submodules${NC}"
        return 1
    }
}

# Function to commit changes in a repository
commit_changes() {
    local repo_name=$1
    local log_file="$repo_name/LOG.md"
    local readme_file="$repo_name/README.md"
    local commit_msg=""
    local has_changes=0

    print_header "Updating $repo_name"

    # Check if required files exist
    check_files "$repo_name" || exit 1

    # Check if files have been modified
    if check_modified "$log_file"; then
        commit_msg="${commit_msg}Update LOG.md with recent changes"
        has_changes=1
    fi

    if check_modified "$readme_file"; then
        if [ -n "$commit_msg" ]; then
            commit_msg="${commit_msg}, "
        fi
        commit_msg="${commit_msg}Update README.md with project status"
        has_changes=1
    fi

    # If no changes, check if there are any untracked files
    if [ $has_changes -eq 0 ]; then
        if [ -n "$(git -C "$repo_name" status --porcelain)" ]; then
            commit_msg="Update repository files"
            has_changes=1
        else
            log_message "${YELLOW}No changes to commit in $repo_name${NC}"
            return 0
        fi
    fi

    if [ "$DRY_RUN" = true ]; then
        log_message "${YELLOW}DRY RUN: Would commit with message: $commit_msg${NC}"
        return 0
    fi

    # Add and commit changes
    log_message "${YELLOW}Committing changes in $repo_name${NC}"
    git -C "$repo_name" add .
    git -C "$repo_name" commit -m "$commit_msg" || true

    # Push changes
    log_message "${YELLOW}Pushing changes to $repo_name${NC}"
    git -C "$repo_name" push

    # Wait for CI to start and check status
    if [ "$SKIP_CI" = false ]; then
        log_message "${YELLOW}Waiting for CI to start...${NC}"
        sleep "$CI_WAIT_TIME"
        check_ci_status "$repo_name"
    fi
}

# Initialize log file
echo "=== Update Script Log - $(date) ===" >"$LOG_FILE"

print_header "Starting Update Process"
log_message "Configuration:"
log_message "- Repository Owner: $REPO_OWNER"
log_message "- CI Wait Time: $CI_WAIT_TIME seconds"
log_message "- Dry Run: $DRY_RUN"
log_message "- Skip CI: $SKIP_CI"
if [ -n "$SINGLE_REPO" ]; then
    log_message "- Single Repository: $SINGLE_REPO"
fi

# Initialize/update submodules
init_submodules

# Update main repository if selected or if no specific repo
if [ -z "$SINGLE_REPO" ] || [ "$SINGLE_REPO" = "twardown-org" ]; then
    log_message "\n${YELLOW}Updating main repository...${NC}"
    if check_files "." && { check_modified "LOG.md" || check_modified "README.md" || check_modified "TODO.md"; }; then
        if [ "$DRY_RUN" = false ]; then
            git add LOG.md README.md TODO.md
            git commit -m "Update documentation files"
            git push
        else
            log_message "${YELLOW}DRY RUN: Would commit documentation updates${NC}"
        fi
    fi
fi

# Update repositories
if [ -n "$SINGLE_REPO" ]; then
    if [ "$SINGLE_REPO" != "twardown-org" ]; then
        commit_changes "$SINGLE_REPO"
    fi
else
    for repo in "${REPOS[@]}"; do
        if [ "$repo" != "twardown-org" ]; then
            commit_changes "$repo"
        fi
    done
fi

# Update submodule references if no specific repo or if main repo
if [ -z "$SINGLE_REPO" ] || [ "$SINGLE_REPO" = "twardown-org" ]; then
    if [ "$DRY_RUN" = false ]; then
        print_header "Updating Submodule References"
        git add twardown-py twardown-js twardown-docs
        git commit -m "Update submodule references" || true
        git push
    else
        log_message "${YELLOW}DRY RUN: Would update submodule references${NC}"
    fi
fi

print_header "Update Complete"
log_message "${YELLOW}Please check CI status in GitHub Actions:${NC}"
if [ -n "$SINGLE_REPO" ]; then
    log_message "https://github.com/$REPO_OWNER/$SINGLE_REPO/actions"
else
    for repo in "${REPOS[@]}"; do
        log_message "https://github.com/$REPO_OWNER/$repo/actions"
    done
fi

# Final status check
if [ "$SKIP_CI" = false ] && [ "$DRY_RUN" = false ]; then
    print_header "Final CI Status"
    if [ -n "$SINGLE_REPO" ]; then
        check_ci_status "$SINGLE_REPO"
    else
        for repo in "${REPOS[@]}"; do
            check_ci_status "$repo"
        done
    fi
fi

log_message "\nUpdate process completed at $(date)"
log_message "Log file: $LOG_FILE"
