# Contributing to Inspektor

Thank you for your interest in contributing to Inspektor! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Node.js 18+
- Rust 1.70+
- Python 3.10+
- Ollama with Mistral 7B model

### Quick Start

1. Fork and clone the repository
2. Install Ollama and pull Mistral 7B: `ollama pull mistral:7b`
3. Run the development script: `./start-dev.sh`

Or manually:

```bash
# Terminal 1 - Python Server
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py

# Terminal 2 - Tauri Client
cd client
npm install
npm run tauri dev
```

## Project Structure

### Backend (Rust/Tauri)

Located in `client/src-tauri/src/`:

- `db/types.rs` - Database type definitions
- `db/credentials.rs` - Credential storage and management
- `db/connection.rs` - Database connection handling
- `db/query.rs` - Query execution with safety validation
- `db/metadata.rs` - Schema introspection
- `lib.rs` - Main Tauri setup

### Frontend (React/TypeScript)

Located in `client/src/`:

- `components/` - React UI components
- `services/` - API integration (Tauri commands & LLM server)
- `types/` - TypeScript type definitions

### LLM Server (Python/FastAPI)

Located in `server/`:

- `main.py` - FastAPI application and endpoints
- `agent.py` - LangChain SQL generation agent
- `cache.py` - Metadata caching system

## Code Style

### Rust

- Follow standard Rust formatting with `cargo fmt`
- Run `cargo clippy` before committing
- Add documentation comments for public APIs

### TypeScript/React

- Use functional components with hooks
- Prefer TypeScript strict mode
- Use meaningful variable names
- Add JSDoc comments for complex functions

### Python

- Follow PEP 8 style guide
- Use type hints
- Add docstrings for functions and classes
- Use `black` for formatting

## Testing

### Rust Tests

```bash
cd client/src-tauri
cargo test
```

### Python Tests

```bash
cd server
pytest
```

### Manual Testing Checklist

- [ ] Connection management (add, test, delete)
- [ ] Natural language query processing
- [ ] Metadata approval workflow
- [ ] SQL execution and results display
- [ ] Error handling and retry
- [ ] Export to CSV/JSON

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Test thoroughly
4. Update documentation if needed
5. Commit with clear, descriptive messages
6. Push to your fork
7. Create a pull request

### Commit Message Format

```
type(scope): brief description

Detailed explanation if needed
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(query): add support for LIMIT clause in queries
fix(credentials): resolve encryption issue on Windows
docs(readme): update installation instructions
```

## Areas for Contribution

### High Priority

- [ ] Persistent credential storage (use Tauri's keychain)
- [ ] Support for more database types (SQL Server, Oracle)
- [ ] Query history with search and replay
- [ ] Improved error messages from LLM
- [ ] Unit and integration tests
- [ ] Performance optimizations for large result sets

### Feature Ideas

- [ ] Dark mode support
- [ ] Multiple LLM model support (not just Mistral)
- [ ] Query templates/favorites
- [ ] Database schema visualization
- [ ] Query performance metrics
- [ ] Multi-database queries (JOIN across databases)
- [ ] Export query history
- [ ] Cloud LLM support (OpenAI, Anthropic)

### Documentation

- [ ] Video tutorial
- [ ] More example queries
- [ ] Architecture diagrams
- [ ] API documentation
- [ ] Troubleshooting guide expansion

## Security

If you discover a security vulnerability, please email [your-email] instead of using the issue tracker.

## Questions?

Feel free to open an issue with the `question` label or start a discussion.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
