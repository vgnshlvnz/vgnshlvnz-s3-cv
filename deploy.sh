#!/bin/bash
#
# Deployment script for Portfolio and Job Tracker stacks
# Usage: ./deploy.sh [portfolio|job-tracker|all] [environment]
#

set -e  # Exit on error
set -u  # Error on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Install from: https://aws.amazon.com/cli/"
        exit 1
    fi

    # Check SAM CLI
    if ! command -v sam &> /dev/null; then
        log_error "SAM CLI not found. Install from: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run: aws configure"
        exit 1
    fi

    # Check jq (optional but recommended)
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found. Install for better output formatting: sudo apt install jq"
    fi

    log_success "All prerequisites met"
}

validate_template() {
    local template=$1
    log_info "Validating $template..."

    if sam validate --template "$template" --lint; then
        log_success "Template validation passed: $template"
        return 0
    else
        log_error "Template validation failed: $template"
        return 1
    fi
}

# ============================================================================
# Portfolio Deployment
# ============================================================================

deploy_portfolio() {
    local env=${1:-prod}

    echo ""
    echo "========================================"
    echo "  Deploying Portfolio Stack"
    echo "========================================"
    echo ""

    # Validate template
    validate_template "template-portfolio.yaml" || exit 1

    log_info "Building portfolio stack..."
    sam build --config-env portfolio

    log_info "Deploying portfolio stack..."
    if [ "$env" == "prod" ]; then
        sam deploy --config-env portfolio
    else
        sam deploy --config-env portfolio --no-confirm-changeset
    fi

    # Get outputs
    log_info "Fetching stack outputs..."
    STACK_NAME="vgnshlvnz-portfolio-stack"

    echo ""
    echo "========================================"
    echo "  Portfolio Deployment Complete"
    echo "========================================"
    echo ""

    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table 2>/dev/null || log_warning "Could not fetch stack outputs"

    echo ""
    log_success "Portfolio stack deployed successfully!"
}

# ============================================================================
# Job Tracker Deployment
# ============================================================================

deploy_job_tracker() {
    local env=${1:-prod}

    echo ""
    echo "========================================"
    echo "  Deploying Job Tracker Stack"
    echo "========================================"
    echo ""

    # Check if Lambda source directory exists
    if [ ! -d "./src" ]; then
        log_warning "Lambda source directory './src' not found"
        log_info "Creating ./src directory and moving final_lambda.py..."
        mkdir -p src
        if [ -f "final_lambda.py" ]; then
            cp final_lambda.py src/app.py
            log_success "Created src/app.py from final_lambda.py"
        else
            log_error "final_lambda.py not found. Cannot proceed."
            exit 1
        fi
    fi

    # Validate template
    validate_template "template-job-tracker.yaml" || exit 1

    log_info "Building job tracker stack..."
    sam build --config-env job-tracker

    log_info "Deploying job tracker stack..."
    case "$env" in
        prod)
            sam deploy --config-env job-tracker
            STACK_NAME="vgnshlvnz-job-tracker-stack"
            ;;
        dev)
            sam deploy --config-env dev-job-tracker
            STACK_NAME="vgnshlvnz-job-tracker-dev"
            ;;
        staging)
            sam deploy --config-env staging-job-tracker
            STACK_NAME="vgnshlvnz-job-tracker-staging"
            ;;
        *)
            log_error "Unknown environment: $env"
            exit 1
            ;;
    esac

    # Get outputs
    log_info "Fetching stack outputs..."

    echo ""
    echo "========================================"
    echo "  Job Tracker Deployment Complete"
    echo "========================================"
    echo ""

    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table 2>/dev/null || log_warning "Could not fetch stack outputs"

    echo ""
    log_success "Job tracker stack deployed successfully!"

    # Get API endpoint
    API_ENDPOINT=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
        --output text 2>/dev/null || echo "")

    if [ -n "$API_ENDPOINT" ]; then
        echo ""
        log_info "Testing API endpoint..."
        echo "  GET $API_ENDPOINT/applications"

        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_ENDPOINT/applications" || echo "000")

        if [ "$HTTP_CODE" == "200" ]; then
            log_success "API is responding correctly (HTTP $HTTP_CODE)"
        else
            log_warning "API returned HTTP $HTTP_CODE"
        fi
    fi
}

# ============================================================================
# Sync Portfolio Files to S3
# ============================================================================

sync_portfolio_files() {
    log_info "Syncing portfolio files to S3..."

    BUCKET_NAME="vgnshlvnz-portfolio"

    # Check if bucket exists
    if ! aws s3 ls "s3://$BUCKET_NAME" &> /dev/null; then
        log_error "Bucket $BUCKET_NAME not found. Deploy the stack first."
        exit 1
    fi

    # Sync files
    aws s3 sync . "s3://$BUCKET_NAME/" \
        --exclude ".git/*" \
        --exclude "*.md" \
        --exclude "template*.yaml" \
        --exclude "samconfig.toml" \
        --exclude "*.sh" \
        --exclude "*.py" \
        --exclude "src/*" \
        --exclude ".claude/*" \
        --exclude "*.json" \
        --delete

    log_success "Files synced to S3"

    # Invalidate CloudFront cache
    log_info "Invalidating CloudFront cache..."
    DIST_ID="E1XWXVYFO71217"

    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "$DIST_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text 2>/dev/null || echo "")

    if [ -n "$INVALIDATION_ID" ]; then
        log_success "CloudFront invalidation created: $INVALIDATION_ID"
        log_info "Changes will be live in 1-2 minutes"
    else
        log_warning "Could not create CloudFront invalidation"
    fi
}

# ============================================================================
# Main Script Logic
# ============================================================================

usage() {
    cat << EOF
Usage: $0 [COMMAND] [ENVIRONMENT]

Commands:
  portfolio       Deploy portfolio stack only
  job-tracker     Deploy job tracker stack only
  all             Deploy both stacks
  sync            Sync portfolio files to S3 and invalidate CloudFront
  validate        Validate all SAM templates
  help            Show this help message

Environments (for job-tracker only):
  prod            Production (default)
  dev             Development
  staging         Staging

Examples:
  $0 portfolio                  # Deploy portfolio to prod
  $0 job-tracker prod           # Deploy job tracker to prod
  $0 job-tracker dev            # Deploy job tracker to dev
  $0 all                        # Deploy both stacks
  $0 sync                       # Sync portfolio files to S3
  $0 validate                   # Validate templates only

EOF
}

main() {
    local command=${1:-help}
    local environment=${2:-prod}

    if [ "$command" == "help" ] || [ "$command" == "--help" ] || [ "$command" == "-h" ]; then
        usage
        exit 0
    fi

    echo ""
    echo "========================================"
    echo "  SAM Deployment Script"
    echo "========================================"
    echo "  Command: $command"
    echo "  Environment: $environment"
    echo "========================================"
    echo ""

    check_prerequisites

    case "$command" in
        portfolio)
            deploy_portfolio "$environment"
            ;;

        job-tracker)
            deploy_job_tracker "$environment"
            ;;

        all)
            deploy_portfolio "$environment"
            echo ""
            echo "--------------------------------------"
            echo ""
            deploy_job_tracker "$environment"
            ;;

        sync)
            sync_portfolio_files
            ;;

        validate)
            validate_template "template-portfolio.yaml"
            validate_template "template-job-tracker.yaml"
            log_success "All templates validated successfully"
            ;;

        *)
            log_error "Unknown command: $command"
            echo ""
            usage
            exit 1
            ;;
    esac

    echo ""
    echo "========================================"
    echo "  Deployment Complete!"
    echo "========================================"
    echo ""
}

# Run main function
main "$@"
