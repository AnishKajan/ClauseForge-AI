#!/bin/bash

# LexiScan Release Management Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
RELEASE_TYPE=""
VERSION=""
DRY_RUN=false
SKIP_TESTS=false
GENERATE_CHANGELOG=true

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE                 Release type (major|minor|patch)"
    echo "  -v, --version VERSION           Specific version (e.g., 1.2.3)"
    echo "  --dry-run                       Show what would be done without executing"
    echo "  --skip-tests                    Skip running tests before release"
    echo "  --no-changelog                  Skip changelog generation"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -t patch                     Create a patch release (e.g., 1.0.0 -> 1.0.1)"
    echo "  $0 -t minor                     Create a minor release (e.g., 1.0.0 -> 1.1.0)"
    echo "  $0 -t major                     Create a major release (e.g., 1.0.0 -> 2.0.0)"
    echo "  $0 -v 1.2.3                     Create specific version 1.2.3"
    echo "  $0 -t patch --dry-run           Show what patch release would do"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            RELEASE_TYPE="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --no-changelog)
            GENERATE_CHANGELOG=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ -z "$RELEASE_TYPE" && -z "$VERSION" ]]; then
    print_error "Either release type (-t) or specific version (-v) is required"
    show_usage
    exit 1
fi

if [[ -n "$RELEASE_TYPE" && "$RELEASE_TYPE" != "major" && "$RELEASE_TYPE" != "minor" && "$RELEASE_TYPE" != "patch" ]]; then
    print_error "Release type must be major, minor, or patch"
    exit 1
fi

# Check if we're on main branch
check_branch() {
    local current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]]; then
        print_error "Releases must be created from the main branch. Current branch: $current_branch"
        exit 1
    fi
}

# Check if working directory is clean
check_working_directory() {
    if [[ -n $(git status --porcelain) ]]; then
        print_error "Working directory is not clean. Please commit or stash changes."
        git status --short
        exit 1
    fi
}

# Get the latest version from git tags
get_latest_version() {
    local latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    echo "${latest_tag#v}"  # Remove 'v' prefix
}

# Calculate next version based on release type
calculate_next_version() {
    local current_version="$1"
    local release_type="$2"
    
    # Parse current version
    local major=$(echo "$current_version" | cut -d. -f1)
    local minor=$(echo "$current_version" | cut -d. -f2)
    local patch=$(echo "$current_version" | cut -d. -f3)
    
    case "$release_type" in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "${major}.$((minor + 1)).0"
            ;;
        patch)
            echo "${major}.${minor}.$((patch + 1))"
            ;;
    esac
}

# Validate version format
validate_version() {
    local version="$1"
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format: $version. Expected format: X.Y.Z"
        exit 1
    fi
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        print_warning "Skipping tests"
        return
    fi
    
    print_status "Running tests before release..."
    
    # Backend tests
    if [[ -f "backend/requirements.txt" ]]; then
        print_status "Running backend tests..."
        cd backend
        python -m pytest --cov=. --cov-report=term-missing
        cd ..
    fi
    
    # Frontend tests
    if [[ -f "frontend/package.json" ]]; then
        print_status "Running frontend tests..."
        cd frontend
        npm test -- --coverage --watchAll=false
        cd ..
    fi
    
    print_success "All tests passed"
}

# Generate changelog
generate_changelog() {
    if [[ "$GENERATE_CHANGELOG" != "true" ]]; then
        print_warning "Skipping changelog generation"
        return
    fi
    
    print_status "Generating changelog..."
    
    local new_version="$1"
    local previous_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    local changelog_file="CHANGELOG.md"
    local temp_changelog=$(mktemp)
    
    # Create changelog header
    echo "# Changelog" > "$temp_changelog"
    echo "" >> "$temp_changelog"
    echo "All notable changes to this project will be documented in this file." >> "$temp_changelog"
    echo "" >> "$temp_changelog"
    echo "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)," >> "$temp_changelog"
    echo "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)." >> "$temp_changelog"
    echo "" >> "$temp_changelog"
    
    # Add new version entry
    echo "## [${new_version}] - $(date +%Y-%m-%d)" >> "$temp_changelog"
    echo "" >> "$temp_changelog"
    
    if [[ -n "$previous_tag" ]]; then
        # Get commits since last tag
        local commits=$(git log --pretty=format:"- %s" "${previous_tag}..HEAD" | grep -v "^- Merge\|^- Release\|^- Version bump" || true)
        
        if [[ -n "$commits" ]]; then
            echo "### Changed" >> "$temp_changelog"
            echo "$commits" >> "$temp_changelog"
            echo "" >> "$temp_changelog"
        else
            echo "### Changed" >> "$temp_changelog"
            echo "- Minor improvements and bug fixes" >> "$temp_changelog"
            echo "" >> "$temp_changelog"
        fi
    else
        echo "### Added" >> "$temp_changelog"
        echo "- Initial release of LexiScan AI Contract Analyzer" >> "$temp_changelog"
        echo "- Document upload and processing capabilities" >> "$temp_changelog"
        echo "- AI-powered contract analysis and Q&A" >> "$temp_changelog"
        echo "- Compliance checking and risk assessment" >> "$temp_changelog"
        echo "- Multi-tenant architecture with RBAC" >> "$temp_changelog"
        echo "- Stripe integration for billing and subscriptions" >> "$temp_changelog"
        echo "" >> "$temp_changelog"
    fi
    
    # Append existing changelog if it exists
    if [[ -f "$changelog_file" ]]; then
        # Skip the header from existing changelog
        tail -n +8 "$changelog_file" >> "$temp_changelog" 2>/dev/null || true
    fi
    
    # Replace the changelog file
    mv "$temp_changelog" "$changelog_file"
    
    print_success "Changelog updated"
}

# Update version in package files
update_version_files() {
    local new_version="$1"
    
    print_status "Updating version in package files..."
    
    # Update frontend package.json
    if [[ -f "frontend/package.json" ]]; then
        sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$new_version\"/" frontend/package.json
        rm frontend/package.json.bak
        print_status "Updated frontend/package.json"
    fi
    
    # Update backend version (if you have a version file)
    if [[ -f "backend/version.py" ]]; then
        echo "__version__ = \"$new_version\"" > backend/version.py
        print_status "Updated backend/version.py"
    else
        # Create version file if it doesn't exist
        echo "__version__ = \"$new_version\"" > backend/version.py
        print_status "Created backend/version.py"
    fi
    
    # Update Docker Compose version labels
    if [[ -f "docker-compose.yml" ]]; then
        sed -i.bak "s/version: \"[^\"]*\"/version: \"$new_version\"/" docker-compose.yml || true
        rm docker-compose.yml.bak 2>/dev/null || true
    fi
}

# Create git tag and commit
create_release_commit() {
    local new_version="$1"
    
    print_status "Creating release commit and tag..."
    
    # Add changed files
    git add CHANGELOG.md
    git add frontend/package.json 2>/dev/null || true
    git add backend/version.py
    git add docker-compose.yml 2>/dev/null || true
    
    # Create release commit
    git commit -m "Release v${new_version}

- Update version to ${new_version}
- Update changelog
- Prepare for release"
    
    # Create annotated tag
    git tag -a "v${new_version}" -m "Release v${new_version}

$(head -n 20 CHANGELOG.md | tail -n +9)"
    
    print_success "Created release commit and tag v${new_version}"
}

# Push release
push_release() {
    local new_version="$1"
    
    print_status "Pushing release to remote repository..."
    
    # Push commit and tag
    git push origin main
    git push origin "v${new_version}"
    
    print_success "Release v${new_version} pushed to remote repository"
}

# Create GitHub release (if gh CLI is available)
create_github_release() {
    local new_version="$1"
    
    if ! command -v gh &> /dev/null; then
        print_warning "GitHub CLI not found. Skipping GitHub release creation."
        print_status "You can manually create a release at: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\/[^/]*\).*/\1/' | sed 's/\.git$//')/releases/new?tag=v${new_version}"
        return
    fi
    
    print_status "Creating GitHub release..."
    
    # Extract release notes from changelog
    local release_notes=$(awk "/## \[${new_version}\]/,/## \[/{if(/## \[${new_version}\]/) next; if(/## \[/ && !/## \[${new_version}\]/) exit; print}" CHANGELOG.md | sed '/^$/d')
    
    # Create GitHub release
    gh release create "v${new_version}" \
        --title "Release v${new_version}" \
        --notes "$release_notes" \
        --latest
    
    print_success "GitHub release created: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\/[^/]*\).*/\1/' | sed 's/\.git$//')/releases/tag/v${new_version}"
}

# Main release function
main() {
    print_status "Starting release process..."
    
    # Pre-flight checks
    check_branch
    check_working_directory
    
    # Determine version
    local current_version=$(get_latest_version)
    local new_version
    
    if [[ -n "$VERSION" ]]; then
        new_version="$VERSION"
        validate_version "$new_version"
    else
        new_version=$(calculate_next_version "$current_version" "$RELEASE_TYPE")
    fi
    
    print_status "Current version: $current_version"
    print_status "New version: $new_version"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY RUN MODE - No changes will be made"
        print_status "Would create release v${new_version}"
        print_status "Would update changelog and version files"
        print_status "Would create git tag and push to remote"
        return
    fi
    
    # Confirm release
    echo -n "Create release v${new_version}? (y/N): "
    read -r confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        print_warning "Release cancelled"
        exit 0
    fi
    
    # Execute release steps
    run_tests
    generate_changelog "$new_version"
    update_version_files "$new_version"
    create_release_commit "$new_version"
    push_release "$new_version"
    create_github_release "$new_version"
    
    print_success "🚀 Release v${new_version} completed successfully!"
    print_status "The CI/CD pipeline will automatically deploy this release."
    print_status "Monitor the deployment at: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\/[^/]*\).*/\1/' | sed 's/\.git$//')/actions"
}

# Run main function
main