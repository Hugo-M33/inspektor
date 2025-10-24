# Inspektor v2.0 - Setup Guide

## 🎉 Migration Complete: Ollama → OpenAI + Authentication

This guide will help you set up and run the new version of Inspektor with OpenAI API integration and user authentication.

## 📋 Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **Rust** 1.70+ (for Tauri)
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- **PostgreSQL** (production) or **SQLite** (development)

## 🚀 Quick Start (Development)

### 1. Server Setup

```bash
cd server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your OpenAI API key
# nano .env or use your preferred editor
```

**Important**: Update your `.env` file with:
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./inspektor.db
JWT_SECRET_KEY=change-this-to-a-long-random-string-in-production
```

### 2. Start the Server

```bash
# Make sure you're in the server directory with venv activated
python main.py
```

The server will start on `http://127.0.0.1:8000`

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 3. Client Setup

Open a new terminal:

```bash
cd client

# Install dependencies (if not already done)
npm install

# Start Tauri development server
npm run tauri dev
```

The Tauri app will launch automatically.

## 🔐 First Time Usage

1. **Register**: When the app launches, you'll see a registration screen
   - Enter your email and password (min 8 characters)
   - Click "Register"

2. **Login**: After registration (or on subsequent launches)
   - Enter your email and password
   - Click "Login"

3. **Add Database Connection**: Same as before
   - Click "New Connection"
   - Fill in your database credentials
   - Test and save

4. **Start Querying**: Ask natural language questions!

## 📁 Project Structure

### New Files (v2.0)

**Server (Python):**
- `server/main.py` - FastAPI app with authentication endpoints
- `server/database.py` - SQLAlchemy models for users, conversations, messages
- `server/auth.py` - JWT authentication and password hashing
- `server/llm_interface.py` - OpenAI API wrapper
- `server/agent_openai.py` - New OpenAI-based agent with function calling
- `server/session_manager.py` - Conversation and metadata persistence
- `server/tools.py` - OpenAI function calling tool definitions

**Client (TypeScript/React):**
- `client/src/services/auth.ts` - Authentication service
- `client/src/services/conversations.ts` - Conversation management
- `client/src/components/Login.tsx` - Login component
- `client/src/components/Register.tsx` - Registration component
- `client/src/components/ConversationHistory.tsx` - Conversation history viewer

### Old Files (Moved to `old/` folder)

- `old/agent_ollama.py` - Original Ollama-based agent
- `old/agent_improved_ollama.py` - Improved Ollama agent
- `old/main_ollama.py` - Original FastAPI server
- `old/main_improved_ollama.py` - Improved server
- `old/cache_inmemory.py` - In-memory cache (replaced with DB persistence)

## 🔧 Configuration

### Environment Variables

**Server (.env):**
```env
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini  # or gpt-4, gpt-3.5-turbo

# Database (SQLite for dev, PostgreSQL for prod)
DATABASE_URL=sqlite:///./inspektor.db
# DATABASE_URL=postgresql://user:password@localhost:5432/inspektor

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=720  # 30 days

# Metadata Cache
METADATA_TTL_HOURS=24

# Server
HOST=127.0.0.1
PORT=8000

# Logging
SQL_ECHO=false
```

### Database Setup (Production)

For production with PostgreSQL:

```bash
# Create database
createdb inspektor

# Update .env
DATABASE_URL=postgresql://user:password@localhost:5432/inspektor

# The server will automatically create tables on startup
python main.py
```

## 🎯 Key Features

### ✅ What's New in v2.0

1. **OpenAI Integration**
   - Uses GPT-4o-mini (faster, more accurate than local models)
   - Native function calling for metadata requests
   - Automatic retry logic and error handling

2. **User Authentication**
   - Secure JWT-based authentication
   - Password hashing with bcrypt
   - Session management

3. **Conversation Persistence**
   - All conversations saved to database
   - Sync across devices (if using shared DB)
   - Conversation history viewer

4. **Improved Metadata Handling**
   - Database-backed metadata cache
   - Per-user metadata isolation
   - Automatic expiration (24 hours default)

5. **Better UX**
   - Login/register flow
   - User email display in header
   - Logout functionality
   - Loading states

## 🐛 Troubleshooting

### Server won't start

**Error**: `openai.OpenAIError: The api_key client option must be set`
- **Fix**: Add your OpenAI API key to `.env`

**Error**: `ModuleNotFoundError: No module named 'openai'`
- **Fix**: Activate venv and run `pip install -r requirements.txt`

### Can't login/register

**Error**: `401 Unauthorized` or `Session expired`
- **Fix**: Check that the server is running and `DATABASE_URL` is correctly set
- Try deleting `inspektor.db` and restarting the server (development only)

### LLM Server Offline

- Check that `python main.py` is running
- Verify `http://127.0.0.1:8000/health` returns status "healthy"
- Check console logs for errors

### Authentication not persisting (Tauri)

The auth service tries to use Tauri secure storage. If that fails, it falls back to localStorage.

To implement secure storage in Tauri, add these commands to `client/src-tauri/src/lib.rs`:
```rust
#[tauri::command]
fn get_secure_storage(key: String) -> Result<String, String> {
    // Implement secure storage retrieval
    Err("Not implemented".to_string())
}

#[tauri::command]
fn set_secure_storage(key: String, value: String) -> Result<(), String> {
    // Implement secure storage saving
    Err("Not implemented".to_string())
}

#[tauri::command]
fn remove_secure_storage(key: String) -> Result<(), String> {
    // Implement secure storage deletion
    Err("Not implemented".to_string())
}
```

## 📊 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/logout` - Logout user
- `GET /auth/me` - Get current user info

### Queries
- `POST /query` - Process natural language query (requires auth)
- `POST /metadata` - Submit metadata from client (requires auth)
- `POST /error-feedback` - Send SQL error for correction (requires auth)

### Conversations
- `GET /conversations` - List user's conversations (requires auth)
- `GET /conversations/{id}` - Get conversation details (requires auth)
- `DELETE /conversations/{id}` - Delete conversation (requires auth)

### Utility
- `GET /health` - Health check
- `GET /stats` - Get LLM token usage stats (requires auth)
- `DELETE /cache/{database_id}` - Clear metadata cache (requires auth)

## 🔐 Security Notes

1. **JWT Secret**: Change `JWT_SECRET_KEY` in production to a long random string
2. **HTTPS**: Use HTTPS in production (configure reverse proxy)
3. **Database**: Use PostgreSQL in production with proper authentication
4. **API Keys**: Keep OpenAI API key secure, never commit to git
5. **CORS**: Update `allow_origins` in `main.py` for production domains

## 📈 Performance

- **Response Time**: ~1-3s (OpenAI API latency)
- **Token Usage**: ~500-2000 tokens per query (GPT-4o-mini)
- **Cost**: ~$0.001-0.005 per query with GPT-4o-mini
- **Database**: SQLite supports ~100k conversations easily

## 🚢 Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production deployment instructions (to be updated).

## 💡 Tips

1. **Cost Optimization**: Use GPT-4o-mini for cost efficiency
2. **Caching**: Metadata is cached for 24 hours by default
3. **Conversations**: You can manually delete old conversations to save space
4. **Token Tracking**: Check `/stats` endpoint to monitor OpenAI usage

## 📚 Next Steps

- Check out the updated [README.md](README.md) for full feature list
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- Explore the conversation history feature
- Try asking complex multi-table queries

## 🎊 Enjoy Inspektor v2.0!

If you encounter any issues, please check the troubleshooting section above or open an issue on GitHub.
