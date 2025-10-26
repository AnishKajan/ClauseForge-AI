#!/bin/bash

# Changelog Generation Script for LexiScan
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
OUTPUT_FILE="CHANGELOG.md"
FROM_TAG=""
TO_TAG="HEAD"
FORMAT="markdown"
INCLUDE_UNRELEASED=true

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
    echo "  -f, --from TAG                  Start from this tag (default: latest tag)"
    echo "  -t, --to TAG                    End at this tag (default: HEAD)"
    echo "  -o, --output FILE               Output file (default: CHANGELOG.md)"
    echo "  --format FORMAT                 Output format (markdown|json) (default: markdown)"
    echo "  --no-unreleased                 Skip unreleased changes"
    echo "  -h, --help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                              Generate full changelog"
    echo "  $0 -f v1.0.0 -t v1.1.0          Generate changelog between versions"
    echo "  $0 --format json                Generate JSON changelog"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--from)
            FROM_TAG="$2"
            shift 2
            ;;
        -t|--to)
            TO_TAG="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --no-unreleased)
            INCLUDE_UNRELEASED=false
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

# Get the latest tag if FROM_TAG is not specified
if [[ -z "$FROM_TAG" ]]; then
    FROM_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
    if [[ -z "$FROM_TAG" ]]; then
        print_warning "No tags found, using initial commit"
        FROM_TAG=$(git rev-list --max-parents=0 HEAD)
    fi
fi

# Function to categorize commits
categorize_commit() {
    local commit_message="$1"
    local commit_type=""
    
    # Extract conventional commit type
    if [[ "$commit_message" =~ ^(feat|feature)(\(.+\))?!?: ]]; then
        commit_type="Added"
    elif [[ "$commit_message" =~ ^(fix|bugfix)(\(.+\))?!?: ]]; then
        commit_type="Fixed"
    elif [[ "$commit_message" =~ ^(docs|doc)(\(.+\))?!?: ]]; then
        commit_type="Documentation"
    elif [[ "$commit_message" =~ ^(style)(\(.+\))?!?: ]]; then
        commit_type="Style"
    elif [[ "$commit_message" =~ ^(refactor)(\(.+\))?!?: ]]; then
        commit_type="Changed"
    elif [[ "$commit_message" =~ ^(perf|performance)(\(.+\))?!?: ]]; then
        commit_type="Performance"
    elif [[ "$commit_message" =~ ^(test)(\(.+\))?!?: ]]; then
        commit_type="Tests"
    elif [[ "$commit_message" =~ ^(build|ci|chore)(\(.+\))?!?: ]]; then
        commit_type="Build"
    elif [[ "$commit_message" =~ ^(revert)(\(.+\))?!?: ]]; then
        commit_type="Reverted"
    elif [[ "$commit_message" =~ BREAKING[[:space:]]CHANGE ]]; then
        commit_type="Breaking"
    else
        commit_type="Changed"
    fi
    
    echo "$commit_type"
}

# Function to clean commit message
clean_commit_message() {
    local message="$1"
    
    # Remove conventional commit prefix
    message=$(echo "$message" | sed -E 's/^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?: //')
    
    # Capitalize first letter
    message=$(echo "$message" | sed 's/^./\U&/')
    
    echo "$message"
}

# Function to get commits between tags
get_commits() {
    local from="$1"
    local to="$2"
    
    if [[ "$from" == "$to" ]]; then
        return
    fi
    
    # Get commits with format: hash|date|author|subject
    git log --pretty=format:"%H|%ci|%an|%s" "${from}..${to}" --reverse
}

# Function to get all tags with dates
get_tags_with_dates() {
    git for-each-ref --sort=-creatordate --format='%(refname:short)|%(creatordate:short)' refs/tags
}

# Function to generate markdown changelog
generate_markdown_changelog() {
    local temp_file=$(mktemp)
    
    # Write header
    cat > "$temp_file" << 'EOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

EOF
    
    # Add unreleased changes if requested
    if [[ "$INCLUDE_UNRELEASED" == "true" && "$TO_TAG" == "HEAD" ]]; then
        local latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
        if [[ -n "$latest_tag" ]]; then
            local unreleased_commits=$(get_commits "$latest_tag" "HEAD")
            if [[ -n "$unreleased_commits" ]]; then
                echo "" >> "$temp_file"
                echo "## [Unreleased]" >> "$temp_file"
                echo "" >> "$temp_file"
                
                # Group commits by category
                declare -A categories
                while IFS='|' read -r hash date author subject; do
                    if [[ -n "$subject" && ! "$subject" =~ ^(Merge|Release|Version bump) ]]; then
                        local category=$(categorize_commit "$subject")
                        local clean_message=$(clean_commit_message "$subject")
                        categories["$category"]+="- $clean_message"$'\n'
                    fi
                done <<< "$unreleased_commits"
                
                # Write categories in order
                for category in "Breaking" "Added" "Changed" "Fixed" "Performance" "Security" "Deprecated" "Removed" "Documentation" "Tests" "Build"; do
                    if [[ -n "${categories[$category]}" ]]; then
                        echo "### $category" >> "$temp_file"
                        echo "" >> "$temp_file"
                        echo -n "${categories[$category]}" >> "$temp_file"
                        echo "" >> "$temp_file"
                    fi
                done
            fi
        fi
    fi
    
    # Get all tags and generate changelog for each
    local tags_with_dates=$(get_tags_with_dates)
    local previous_tag=""
    
    while IFS='|' read -r tag date; do
        if [[ -n "$tag" ]]; then
            # Skip if we're filtering by specific tags
            if [[ -n "$FROM_TAG" && "$FROM_TAG" != "$tag" && -z "$previous_tag" ]]; then
                previous_tag="$tag"
                continue
            fi
            
            if [[ -n "$TO_TAG" && "$TO_TAG" != "HEAD" && "$TO_TAG" != "$tag" ]]; then
                if [[ "$previous_tag" == "$TO_TAG" ]]; then
                    break
                fi
                previous_tag="$tag"
                continue
            fi
            
            echo "" >> "$temp_file"
            echo "## [$tag] - $date" >> "$temp_file"
            echo "" >> "$temp_file"
            
            # Get commits for this tag
            local tag_commits=""
            if [[ -n "$previous_tag" ]]; then
                tag_commits=$(get_commits "$previous_tag" "$tag")
            else
                # First tag, get all commits up to this tag
                tag_commits=$(git log --pretty=format:"%H|%ci|%an|%s" "$tag" --reverse)
            fi
            
            if [[ -n "$tag_commits" ]]; then
                # Group commits by category
                declare -A tag_categories
                while IFS='|' read -r hash date author subject; do
                    if [[ -n "$subject" && ! "$subject" =~ ^(Merge|Release|Version bump) ]]; then
                        local category=$(categorize_commit "$subject")
                        local clean_message=$(clean_commit_message "$subject")
                        tag_categories["$category"]+="- $clean_message"$'\n'
                    fi
                done <<< "$tag_commits"
                
                # Write categories in order
                for category in "Breaking" "Added" "Changed" "Fixed" "Performance" "Security" "Deprecated" "Removed" "Documentation" "Tests" "Build"; do
                    if [[ -n "${tag_categories[$category]}" ]]; then
                        echo "### $category" >> "$temp_file"
                        echo "" >> "$temp_file"
                        echo -n "${tag_categories[$category]}" >> "$temp_file"
                        echo "" >> "$temp_file"
                    fi
                done
            else
                echo "### Changed" >> "$temp_file"
                echo "" >> "$temp_file"
                echo "- Initial release" >> "$temp_file"
                echo "" >> "$temp_file"
            fi
            
            previous_tag="$tag"
            
            # Stop if we've reached the TO_TAG
            if [[ "$TO_TAG" != "HEAD" && "$TO_TAG" == "$tag" ]]; then
                break
            fi
        fi
    done <<< "$tags_with_dates"
    
    # Move temp file to output
    mv "$temp_file" "$OUTPUT_FILE"
}

# Function to generate JSON changelog
generate_json_changelog() {
    local temp_file=$(mktemp)
    
    echo "{" > "$temp_file"
    echo '  "changelog": {' >> "$temp_file"
    echo '    "format": "1.0.0",' >> "$temp_file"
    echo '    "generator": "LexiScan Changelog Generator",' >> "$temp_file"
    echo '    "generated_at": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",' >> "$temp_file"
    echo '    "releases": [' >> "$temp_file"
    
    local first_release=true
    
    # Add unreleased if requested
    if [[ "$INCLUDE_UNRELEASED" == "true" && "$TO_TAG" == "HEAD" ]]; then
        local latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
        if [[ -n "$latest_tag" ]]; then
            local unreleased_commits=$(get_commits "$latest_tag" "HEAD")
            if [[ -n "$unreleased_commits" ]]; then
                if [[ "$first_release" != "true" ]]; then
                    echo "," >> "$temp_file"
                fi
                
                echo '      {' >> "$temp_file"
                echo '        "version": "unreleased",' >> "$temp_file"
                echo '        "date": null,' >> "$temp_file"
                echo '        "changes": {' >> "$temp_file"
                
                # Process commits
                declare -A categories
                while IFS='|' read -r hash date author subject; do
                    if [[ -n "$subject" && ! "$subject" =~ ^(Merge|Release|Version bump) ]]; then
                        local category=$(categorize_commit "$subject")
                        local clean_message=$(clean_commit_message "$subject")
                        categories["$category"]+="\"$clean_message\","$'\n'
                    fi
                done <<< "$unreleased_commits"
                
                local first_category=true
                for category in "breaking" "added" "changed" "fixed" "performance" "security" "deprecated" "removed" "documentation" "tests" "build"; do
                    local cap_category=$(echo "$category" | sed 's/.*/\L&/; s/[a-z]/\u&/')
                    if [[ -n "${categories[$cap_category]}" ]]; then
                        if [[ "$first_category" != "true" ]]; then
                            echo "," >> "$temp_file"
                        fi
                        echo "          \"$category\": [" >> "$temp_file"
                        echo -n "${categories[$cap_category]}" | sed 's/,$//; s/^/            /; s/$//' >> "$temp_file"
                        echo "" >> "$temp_file"
                        echo "          ]" >> "$temp_file"
                        first_category=false
                    fi
                done
                
                echo '        }' >> "$temp_file"
                echo '      }' >> "$temp_file"
                first_release=false
            fi
        fi
    fi
    
    # Process tags
    local tags_with_dates=$(get_tags_with_dates)
    local previous_tag=""
    
    while IFS='|' read -r tag date; do
        if [[ -n "$tag" ]]; then
            if [[ "$first_release" != "true" ]]; then
                echo "," >> "$temp_file"
            fi
            
            echo '      {' >> "$temp_file"
            echo "        \"version\": \"$tag\"," >> "$temp_file"
            echo "        \"date\": \"$date\"," >> "$temp_file"
            echo '        "changes": {' >> "$temp_file"
            
            # Get commits for this tag
            local tag_commits=""
            if [[ -n "$previous_tag" ]]; then
                tag_commits=$(get_commits "$previous_tag" "$tag")
            fi
            
            if [[ -n "$tag_commits" ]]; then
                # Process commits similar to unreleased
                declare -A tag_categories
                while IFS='|' read -r hash date author subject; do
                    if [[ -n "$subject" && ! "$subject" =~ ^(Merge|Release|Version bump) ]]; then
                        local category=$(categorize_commit "$subject")
                        local clean_message=$(clean_commit_message "$subject")
                        tag_categories["$category"]+="\"$clean_message\","$'\n'
                    fi
                done <<< "$tag_commits"
                
                local first_category=true
                for category in "breaking" "added" "changed" "fixed" "performance" "security" "deprecated" "removed" "documentation" "tests" "build"; do
                    local cap_category=$(echo "$category" | sed 's/.*/\L&/; s/[a-z]/\u&/')
                    if [[ -n "${tag_categories[$cap_category]}" ]]; then
                        if [[ "$first_category" != "true" ]]; then
                            echo "," >> "$temp_file"
                        fi
                        echo "          \"$category\": [" >> "$temp_file"
                        echo -n "${tag_categories[$cap_category]}" | sed 's/,$//; s/^/            /; s/$//' >> "$temp_file"
                        echo "" >> "$temp_file"
                        echo "          ]" >> "$temp_file"
                        first_category=false
                    fi
                done
            else
                echo '          "added": [' >> "$temp_file"
                echo '            "Initial release"' >> "$temp_file"
                echo '          ]' >> "$temp_file"
            fi
            
            echo '        }' >> "$temp_file"
            echo '      }' >> "$temp_file"
            
            first_release=false
            previous_tag="$tag"
        fi
    done <<< "$tags_with_dates"
    
    echo '    ]' >> "$temp_file"
    echo '  }' >> "$temp_file"
    echo '}' >> "$temp_file"
    
    # Move temp file to output
    mv "$temp_file" "$OUTPUT_FILE"
}

# Main function
main() {
    print_status "Generating changelog..."
    print_status "From: ${FROM_TAG:-'beginning'}"
    print_status "To: $TO_TAG"
    print_status "Format: $FORMAT"
    print_status "Output: $OUTPUT_FILE"
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi
    
    # Generate changelog based on format
    case "$FORMAT" in
        markdown)
            generate_markdown_changelog
            ;;
        json)
            generate_json_changelog
            ;;
        *)
            print_error "Unsupported format: $FORMAT"
            exit 1
            ;;
    esac
    
    print_success "Changelog generated: $OUTPUT_FILE"
}

# Run main function
main