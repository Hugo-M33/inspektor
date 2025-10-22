# Inspektor Makefile
# Convenience commands for development and deployment

.PHONY: help dev dev-up dev-down dev-logs prod prod-up prod-down prod-logs build clean test pull-model

# Default target
help:
	@echo "Inspektor - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make dev-up       - Start dev containers in background"
	@echo "  make dev-down     - Stop dev containers"
	@echo "  make dev-logs     - View dev container logs"
	@echo "  make dev-shell    - Open shell in server container"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start production environment"
	@echo "  make prod-up      - Start prod containers in background"
	@echo "  make prod-down    - Stop prod containers"
	@echo "  make prod-logs    - View prod container logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make build        - Build server container"
	@echo "  make rebuild      - Rebuild server from scratch"
	@echo "  make clean        - Stop containers and remove volumes"
	@echo "  make pull-model   - Manually pull Mistral 7B model"
	@echo "  make status       - Show container status"
	@echo "  make health       - Check service health"
	@echo ""
	@echo "Monitoring:"
	@echo "  make stats        - Show container resource usage"
	@echo "  make top          - Show running processes in containers"
	@echo ""

# Development commands
dev:
	@echo "Starting development environment..."
	docker compose up

dev-up:
	@echo "Starting development containers in background..."
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@make health

dev-down:
	@echo "Stopping development containers..."
	docker compose down

dev-logs:
	docker compose logs -f

dev-shell:
	docker exec -it inspektor-server /bin/bash

# Production commands
prod:
	@echo "Starting production environment..."
	docker compose -f docker-compose.prod.yml up

prod-up:
	@echo "Starting production containers in background..."
	docker compose -f docker-compose.prod.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@make prod-health

prod-down:
	@echo "Stopping production containers..."
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

# Build commands
build:
	@echo "Building server container..."
	docker compose build inspektor-server

rebuild:
	@echo "Rebuilding server from scratch..."
	docker compose build --no-cache inspektor-server

# Maintenance commands
clean:
	@echo "WARNING: This will stop containers and remove volumes!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		echo "Cleaned up successfully"; \
	else \
		echo "Cancelled"; \
	fi

pull-model:
	@echo "Pulling Mistral 7B model..."
	docker exec -it inspektor-ollama ollama pull mistral:7b
	@echo "Listing available models:"
	docker exec -it inspektor-ollama ollama list

status:
	@echo "Container Status:"
	@docker compose ps
	@echo ""
	@echo "Network Status:"
	@docker network ls | grep inspektor

health:
	@echo "Checking Ollama health..."
	@curl -s http://localhost:11434/api/tags | grep -q "models" && echo "✓ Ollama is healthy" || echo "✗ Ollama is not responding"
	@echo "Checking Inspektor server health..."
	@curl -s http://localhost:8000/health | grep -q "healthy" && echo "✓ Server is healthy" || echo "✗ Server is not responding"

prod-health:
	@echo "Checking production services..."
	@docker compose -f docker-compose.prod.yml ps

# Monitoring commands
stats:
	docker stats inspektor-ollama inspektor-server

top:
	@echo "Ollama processes:"
	@docker top inspektor-ollama
	@echo ""
	@echo "Server processes:"
	@docker top inspektor-server

# Backup and restore
backup:
	@echo "Creating backup of Ollama models..."
	@mkdir -p backups
	docker run --rm -v inspektor_ollama_data:/data -v $$(pwd)/backups:/backup \
		alpine tar czf /backup/ollama-backup-$$(date +%Y%m%d-%H%M%S).tar.gz /data
	@echo "Backup created in ./backups/"

restore:
	@echo "Available backups:"
	@ls -lh backups/*.tar.gz
	@echo ""
	@read -p "Enter backup filename to restore: " backup; \
	docker run --rm -v inspektor_ollama_data:/data -v $$(pwd)/backups:/backup \
		alpine tar xzf /backup/$$backup -C /
	@echo "Restore complete"

# Testing
test-server:
	@echo "Testing server endpoints..."
	@curl -s http://localhost:8000/health || echo "Health check failed"
	@echo ""
	@curl -s http://localhost:11434/api/tags || echo "Ollama check failed"

test-query:
	@echo "Testing query endpoint..."
	@curl -X POST http://localhost:8000/query \
		-H "Content-Type: application/json" \
		-d '{"database_id": "test", "query": "test", "connection": {"db_type": "sqlite", "database": ":memory:"}}' \
		| python -m json.tool

# Ollama model management
list-models:
	docker exec -it inspektor-ollama ollama list

remove-model:
	@read -p "Enter model name to remove: " model; \
	docker exec -it inspektor-ollama ollama rm $$model

# Docker system cleanup
prune:
	@echo "Cleaning up Docker system..."
	docker system prune -f
	@echo "Cleanup complete"

prune-all:
	@echo "WARNING: This will remove all unused Docker resources!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker system prune -a -f; \
		echo "Deep cleanup complete"; \
	else \
		echo "Cancelled"; \
	fi
