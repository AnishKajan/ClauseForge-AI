#!/bin/bash

# LexiScan Prerequisites Verification Script
# This script checks if all prerequisites are properly installed and configured

# set -e  # Don't exit on first error, we want to check everything

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

check_version() {
    local cmd="$1"
    local version_cmd="$2"
    local min_version="$3"
    local current_version
    
    if check_command "$cmd"; then
        current_version=$($version_cmd 2>/dev/null | head -n1)
        print_success "$cmd is installed: $current_version"
        return 0
    else
        print_error "$cmd is not installed (minimum required: $min_version)"
        return 1
    fi
}

echo -e "${BLUE}"
echo "================================================================================"
echo "                    LexiScan Prerequisites Verification                        "
echo "================================================================================"
echo -e "${NC}"

# Check runtime requirements
print_header "Runtime Requirements"

# Python 3.11+
if check_command python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -ge 11 ]]; then
        print_success "Python $PYTHON_VERSION (✓ >= 3.11)"
    else
        print_error "Python $PYTHON_VERSION (✗ requires >= 3.11)"
    fi
else
    print_error "Python 3 is not installed"
fi

# Node.js 20+
if check_command node; then
    NODE_VERSION=$(node --version 2>&1 | sed 's/v//')
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
    
    if [[ $NODE_MAJOR -ge 20 ]]; then
        print_success "Node.js v$NODE_VERSION (✓ >= 20)"
    else
        print_warning "Node.js v$NODE_VERSION (⚠ requires >= 20)"
        echo "  To upgrade: nvm install 20 && nvm use 20"
    fi
else
    print_error "Node.js is not installed"
fi

# npm
if check_command npm; then
    NPM_VERSION=$(npm --version 2>&1)
    print_success "npm $NPM_VERSION"
else
    print_error "npm is not installed"
fi

# Docker
if check_command docker; then
    DOCKER_VERSION=$(docker --version 2>&1 | cut -d' ' -f3 | sed 's/,//')
    print_success "Docker $DOCKER_VERSION"
    
    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        print_success "Docker daemon is running"
    else
        print_warning "Docker daemon is not running"
    fi
else
    print_error "Docker is not installed"
fi

# Docker Compose
if check_command docker-compose || docker compose version &> /dev/null; then
    if check_command docker-compose; then
        COMPOSE_VERSION=$(docker-compose --version 2>&1 | cut -d' ' -f3 | sed 's/,//')
        print_success "Docker Compose $COMPOSE_VERSION"
    else
        COMPOSE_VERSION=$(docker compose version --short 2>&1)
        print_success "Docker Compose $COMPOSE_VERSION (plugin)"
    fi
else
    print_error "Docker Compose is not installed"
fi

# Check optional tools
print_header "Optional Development Tools"

# Git
check_version "git" "git --version" "2.0" || true

# AWS CLI
if check_command aws; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
    print_success "AWS CLI $AWS_VERSION"
    
    # Check AWS credentials
    if aws sts get-caller-identity &> /dev/null; then
        print_success "AWS credentials are configured"
    else
        print_warning "AWS credentials not configured (run 'aws configure')"
    fi
else
    print_warning "AWS CLI not installed (optional for local development)"
fi

# Check environment configuration
print_header "Environment Configuration"

if [[ -f ".env" ]]; then
    print_success ".env file exists"
    
    # Check for required environment variables
    required_vars=(
        "DATABASE_URL"
        "JWT_SECRET"
        "NEXTAUTH_SECRET"
    )
    
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env && ! grep -q "^${var}=$" .env && ! grep -q "^${var}=your_" .env; then
            print_success "$var is configured"
        else
            print_warning "$var needs to be configured in .env"
        fi
    done
else
    print_warning ".env file not found (copy from .env.example)"
fi

if [[ -f ".env.example" ]]; then
    print_success ".env.example template exists"
else
    print_error ".env.example template missing"
fi

# Check project structure
print_header "Project Structure"

required_files=(
    "SETUP.md"
    ".env.example"
    "aws-setup/iam-policies.json"
    "aws-setup/setup-aws-resources.sh"
    "stripe-setup/webhook-config.md"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        print_success "$file exists"
    else
        print_error "$file is missing"
    fi
done

# Check API key placeholders (if .env exists)
if [[ -f ".env" ]]; then
    print_header "API Keys Configuration Status"
    
    api_keys=(
        "ANTHROPIC_API_KEY:sk-ant-"
        "OPENAI_API_KEY:sk-"
        "STRIPE_SECRET_KEY:sk_"
        "STRIPE_PUBLISHABLE_KEY:pk_"
    )
    
    for key_info in "${api_keys[@]}"; do
        key_name=$(echo $key_info | cut -d':' -f1)
        key_prefix=$(echo $key_info | cut -d':' -f2)
        
        if grep -q "^${key_name}=" .env; then
            key_value=$(grep "^${key_name}=" .env | cut -d'=' -f2)
            if [[ $key_value == *"$key_prefix"* ]] && [[ ${#key_value} -gt 20 ]]; then
                print_success "$key_name appears to be configured"
            else
                print_warning "$key_name needs to be configured with actual API key"
            fi
        else
            print_warning "$key_name not found in .env file"
        fi
    done
fi

# Summary
print_header "Verification Summary"

echo -e "Results:"
echo -e "  ${GREEN}✓ Passed: $PASSED${NC}"
echo -e "  ${YELLOW}⚠ Warnings: $WARNINGS${NC}"
echo -e "  ${RED}✗ Failed: $FAILED${NC}"

if [[ $FAILED -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All critical prerequisites are met!${NC}"
    if [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}⚠ Please address the warnings above for optimal setup.${NC}"
    fi
    echo -e "\n${BLUE}Next steps:${NC}"
    echo "1. Address any warnings above"
    echo "2. Configure API keys in .env file"
    echo "3. Run AWS setup script: ./aws-setup/setup-aws-resources.sh"
    echo "4. Configure Stripe webhooks using stripe-setup/webhook-config.md"
    echo "5. Proceed to Task 1: Set up project structure"
else
    echo -e "\n${RED}❌ Some prerequisites are missing. Please install them before proceeding.${NC}"
    echo -e "\nRefer to SETUP.md for detailed installation instructions."
fi

echo -e "\n${BLUE}For detailed setup instructions, see: SETUP.md${NC}"

exit $FAILED