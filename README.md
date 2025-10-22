# Inspektor

Inspektor is a Tauri-based desktop application that lets users interact with their database using natural language queries, powered by an LLM workflow with Python, FastAPI, LangChain, and Ollama/Mistral 7B.

![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Tech Stack

- **Frontend**: React + TypeScript (via Tauri)
- **Backend**: Rust (Tauri)
- **LLM Server**: Python + FastAPI + LangChain + Ollama/Mistral 7B
- **Database Support**: PostgreSQL, MySQL, SQLite
- **Storage**: Secure local credential storage via Tauri

## Features

✅ **Secure DB Access**: Users enter database credentials, test connections, and store them encrypted locally.

✅ **Natural Language Queries**: Ask questions about your business data naturally (e.g., "Show me all users who signed up last month").

✅ **Interactive LLM Workflow**:
- LLM determines what metadata it needs
- Requests table names, schemas, and relationships iteratively
- User approves each metadata request
- Constructs the final SQL query based on gathered information

✅ **Metadata Caching**: LLM caches database metadata to avoid repeated requests. Cache expires after 60 minutes by default.

✅ **Error Handling**: If a SQL query fails, the LLM receives the error and attempts to fix it automatically.

✅ **Client-Only DB Interaction**: All database queries are executed client-side; the server only processes metadata and LLM reasoning.

✅ **Query Results Export**: Export results to CSV or JSON format.

✅ **Safety Features**:
- SQL injection prevention
- Destructive operation blocking (no DROP, DELETE, etc.)
- Read-only query enforcement

## How It Works

1. User inputs database credentials and tests connection
2. User asks a business question in natural language
3. LLM interacts with the client iteratively to gather metadata
4. LLM generates SQL query with explanation
5. User reviews and approves SQL execution
6. Query is executed on the client; results are displayed
7. Metadata cache is maintained on the server for future queries

## Security

🔒 DB credentials are stored encrypted locally in Tauri storage

🔒 No direct LLM access to the database; all queries are executed client-side

🔒 Cached metadata contains schema info only, never user data

🔒 Read-only queries enforced with validation

## Prerequisites

### For Docker (Easiest)
- **Docker Desktop** 20.10+ ([install](https://www.docker.com/products/docker-desktop))
- **8GB RAM** (for development with Llama 3.2 1B)
- **10GB disk space**

### For Manual Setup
- **Node.js** 18+ and npm
- **Rust** 1.70+ and Cargo
- **Python** 3.10+
- **Ollama** with your chosen model
- **8GB+ RAM** (16GB for Mistral 7B)

### Installing Ollama (Manual Setup Only)

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Or on macOS with Homebrew
brew install ollama

# Pull a model (choose based on your needs)
ollama pull llama3.2:1b    # Fast, small (1GB) - development
ollama pull mistral:7b      # Slower, better (4GB) - production

# Start Ollama server (it runs on http://localhost:11434 by default)
ollama serve
```

See [MODEL_SELECTION.md](MODEL_SELECTION.md) for detailed model comparison.

## Installation

You can run Inspektor in two ways:

### Option 1: Docker (Recommended) 🐳

**Easiest way to get started!** Docker handles Ollama, LLM model, and the server automatically.

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd inspektor

# 2. Start everything with Docker Compose
docker compose up -d

# Or use the Makefile
make dev-up

# 3. Wait for Llama 3.2 1B to download (first time only, ~1GB)
# Check status with:
make health
```

That's it! The server will be running at `http://localhost:8000`.

**Note:** Development uses `llama3.2:1b` (fast, small). For production, use `mistral:7b` (see [MODEL_SELECTION.md](MODEL_SELECTION.md)).

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed Docker deployment guide.

### Option 2: Manual Setup

For development or if you prefer manual control:

#### 1. Clone the repository

```bash
git clone <your-repo-url>
cd inspektor
```

#### 2. Set up the Python LLM Server

```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start the server
python main.py
```

The server will start on `http://127.0.0.1:8000`. API docs: `http://127.0.0.1:8000/docs`.

**Note:** Use `main.py` (not `main_improved.py`). See [IMPROVEMENTS.md](IMPROVEMENTS.md) for why.

#### 3. Set up the Tauri Client

```bash
cd client

# Install dependencies
npm install

# Start the development server
npm run tauri dev
```

The Tauri app will launch with hot reload enabled.

## Development

### Running in Development Mode

You'll need to run both the Python server and the Tauri client:

**Terminal 1 - Python Server:**
```bash
cd server
source venv/bin/activate
python main.py
```

**Terminal 2 - Tauri Client:**
```bash
cd client
npm run tauri dev
```

### Building for Production

```bash
cd client
npm run tauri build
```

This will create platform-specific installers in `client/src-tauri/target/release/bundle/`.

## Usage

### 1. Add a Database Connection

1. Launch Inspektor
2. Click "New Connection"
3. Fill in your database credentials:
   - **PostgreSQL**: host, port (5432), database name, username, password
   - **MySQL**: host, port (3306), database name, username, password
   - **SQLite**: file path to database
4. Click "Test" to verify the connection
5. Click "Save Connection"

### 2. Query Your Database

1. Select a connection from the list
2. Enter a natural language question (e.g., "Show me all users created in the last 7 days")
3. The LLM will request metadata as needed - approve each request
4. Review the generated SQL query
5. Execute the query to see results
6. Export results to CSV or JSON if needed

### Example Queries

- "Show me all tables in this database"
- "What are the top 10 most expensive products?"
- "Find all orders placed in the last month with a total over $1000"
- "Count the number of users by country"
- "Show me the schema for the users table"

## Project Structure

```
inspektor/
├── client/                  # Tauri + React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API services (Tauri + LLM)
│   │   ├── types/          # TypeScript types
│   │   └── App.tsx         # Main app component
│   ├── src-tauri/          # Rust backend
│   │   └── src/
│   │       ├── db/         # Database modules
│   │       └── lib.rs      # Main Tauri setup
│   └── package.json
│
└── server/                 # Python FastAPI LLM server
    ├── main.py            # FastAPI app
    ├── agent.py           # LangChain SQL agent
    ├── cache.py           # Metadata cache
    ├── requirements.txt
    └── README.md
```

## Configuration

### Python Server (.env)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
HOST=127.0.0.1
PORT=8000
```

### Supported Databases

- **PostgreSQL** 9.6+
- **MySQL** 5.7+
- **SQLite** 3.x

## Troubleshooting

### LLM Server Offline

If you see "LLM Server: offline" in the app:
- Ensure Ollama is running: `ollama serve`
- Check that the Python server is running: `python server/main.py`
- Verify the server URL in the browser: `http://localhost:8000/health`

### Database Connection Failed

- Verify your credentials are correct
- Ensure the database server is running and accessible
- Check firewall rules for database ports
- For SQLite, ensure the file path is correct and readable

### Build Errors

If you encounter build errors with Rust dependencies:
```bash
cd client/src-tauri
cargo clean
cargo build
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Tauri](https://tauri.app/)
- LLM integration via [LangChain](https://www.langchain.com/)
- Powered by [Ollama](https://ollama.com/) and Mistral 7B
