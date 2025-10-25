#!/bin/bash

# Inspektor Production Deployment Script
# This script deploys the Inspektor backend to a VPS

set -e  # Exit on error

# Configuration
VPS_HOST="${VPS_HOST:-your-vps-hostname}"
VPS_USER="${VPS_USER:-your-username}"
VPS_PORT="${VPS_PORT:-22}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/inspektor}"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

    # Check if ssh is available
    if ! command -v ssh &> /dev/null; then
        log_error "ssh command not found. Please install OpenSSH."
        exit 1
    fi

    # Check if rsync is available
    if ! command -v rsync &> /dev/null; then
        log_error "rsync command not found. Please install rsync."
        exit 1
    fi

    # Check if .env.production exists
    if [ ! -f "server/.env.production" ]; then
        log_error "server/.env.production file not found. Please create it from .env.example"
        exit 1
    fi

    # Check if VPS_HOST is set
    if [ "$VPS_HOST" = "your-vps-hostname" ]; then
        log_error "Please set VPS_HOST environment variable or edit this script"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

test_ssh_connection() {
    log_info "Testing SSH connection to $VPS_USER@$VPS_HOST:$VPS_PORT..."

    if ssh -p "$VPS_PORT" -o ConnectTimeout=10 "$VPS_USER@$VPS_HOST" "echo 'Connection successful'" &> /dev/null; then
        log_success "SSH connection successful"
    else
        log_error "Failed to connect to VPS. Please check your SSH configuration."
        exit 1
    fi
}

create_remote_directory() {
    log_info "Creating deployment directory on VPS: $DEPLOY_PATH"

    ssh -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" "
        sudo mkdir -p $DEPLOY_PATH
        sudo chown -R $VPS_USER:$VPS_USER $DEPLOY_PATH
    "

    log_success "Remote directory created"
}

sync_files() {
    log_info "Syncing files to VPS..."

    # Sync server files
    rsync -avz --progress -e "ssh -p $VPS_PORT" \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='inspektor.db' \
        --exclude='*.log' \
        ./server/ "$VPS_USER@$VPS_HOST:$DEPLOY_PATH/server/"

    # Sync docker-compose file
    rsync -avz --progress -e "ssh -p $VPS_PORT" \
        "./$DOCKER_COMPOSE_FILE" "$VPS_USER@$VPS_HOST:$DEPLOY_PATH/docker-compose.yml"

    # Sync .env.production to .env on server
    rsync -avz --progress -e "ssh -p $VPS_PORT" \
        "./server/.env.production" "$VPS_USER@$VPS_HOST:$DEPLOY_PATH/server/.env"

    log_success "Files synced successfully"
}

build_and_start() {
    log_info "Building and starting Docker containers on VPS..."

    ssh -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" "
        cd $DEPLOY_PATH

        # Stop existing containers
        docker compose down || true

        # Build and start new containers
        docker compose build --no-cache inspektor-server
        docker compose up -d

        # Show status
        echo ''
        echo 'Container status:'
        docker compose ps
    "

    log_success "Docker containers started"
}

check_health() {
    log_info "Checking application health..."

    # Wait a few seconds for the app to start
    sleep 10

    ssh -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" "
        # Check if containers are running
        if docker compose -f $DEPLOY_PATH/docker-compose.yml ps | grep -q 'Up'; then
            echo 'Containers are running'

            # Test health endpoint
            if curl -f http://localhost:8090/health &> /dev/null; then
                echo 'Health check passed!'
                curl -s http://localhost:8090/health | python3 -m json.tool
            else
                echo 'Warning: Health check failed!'
                exit 1
            fi
        else
            echo 'Error: Containers are not running!'
            exit 1
        fi
    "

    if [ $? -eq 0 ]; then
        log_success "Health check passed"
    else
        log_error "Health check failed. Check logs with: ssh $VPS_USER@$VPS_HOST 'cd $DEPLOY_PATH && docker compose logs'"
        exit 1
    fi
}

show_logs() {
    log_info "Showing recent logs..."

    ssh -p "$VPS_PORT" "$VPS_USER@$VPS_HOST" "
        cd $DEPLOY_PATH
        docker compose logs --tail=50
    "
}

print_completion_message() {
    echo ""
    log_success "==================================="
    log_success "Deployment completed successfully!"
    log_success "==================================="
    echo ""
    log_info "Backend URL: https://inspektor.hmartin.dev"
    log_info "Health check: https://inspektor.hmartin.dev/health"
    echo ""
    log_info "Useful commands:"
    echo "  View logs:    ssh $VPS_USER@$VPS_HOST 'cd $DEPLOY_PATH && docker compose logs -f'"
    echo "  Restart:      ssh $VPS_USER@$VPS_HOST 'cd $DEPLOY_PATH && docker compose restart'"
    echo "  Stop:         ssh $VPS_USER@$VPS_HOST 'cd $DEPLOY_PATH && docker compose down'"
    echo "  Status:       ssh $VPS_USER@$VPS_HOST 'cd $DEPLOY_PATH && docker compose ps'"
    echo ""
}

# Main deployment flow
main() {
    echo ""
    log_info "=========================================="
    log_info "Inspektor Production Deployment"
    log_info "=========================================="
    echo ""

    check_prerequisites
    test_ssh_connection
    create_remote_directory
    sync_files
    build_and_start
    check_health
    show_logs
    print_completion_message
}

# Run main function
main
