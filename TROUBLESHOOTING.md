# Troubleshooting Guide

Common issues and their solutions.

## Issue: "No drivers installed" when testing database connection

### Symptoms
```
thread 'tokio-runtime-worker' panicked at sqlx-core-0.8.6/src/any/driver.rs:142:10:
No drivers installed. Please see the documentation in `sqlx::any` for details.
```

### Cause
The `sqlx` crate is configured with individual driver features (`postgres`, `mysql`, `sqlite`) but is missing the `any` feature flag. The `Any` driver requires explicit compilation.

### Solution
Add the `"any"` feature to `sqlx` in `client/src-tauri/Cargo.toml`:

```toml
# Before
sqlx = { version = "0.8", features = ["runtime-tokio-rustls", "postgres", "mysql", "sqlite"] }

# After
sqlx = { version = "0.8", features = ["runtime-tokio-rustls", "postgres", "mysql", "sqlite", "any"] }
```

Then rebuild:
```bash
cd client
npm run tauri dev
```

The Rust code will recompile with the `Any` driver support.

## Issue: 422 Unprocessable Entity when sending queries

### Symptoms
```
POST /query HTTP/1.1" 422 Unprocessable Entity
```

Server logs show Pydantic validation error about missing fields.

### Cause
Type mismatch between TypeScript and Python:
- TypeScript `DatabaseCredentials` was missing the `schema` field
- Python `DatabaseConnection` model expects `schema: Optional[str]`
- When client sends credentials, Python validation fails

### Solution
Add the `schema` field to TypeScript types in `client/src/types/database.ts`:

```typescript
export interface DatabaseCredentials {
  id: string;
  name: string;
  db_type: DatabaseType;
  host?: string;
  port?: number;
  database: string;
  username?: string;
  password?: string;
  file_path?: string;
  schema?: string;  // ADD THIS LINE
}
```

No rebuild needed - TypeScript will recognize the new field.

## Issue: Cargo warnings about unused dependencies

### Symptoms
```
warning: `inspektor` (lib) generated 10 warnings
(run `cargo fix --lib -p inspektor` to apply 8 suggestions)
```

### Solution
Run the suggested fix command:
```bash
cd client/src-tauri
cargo fix --lib -p inspektor
```

This will automatically fix unused imports and other warnings.

## Issue: CORS errors when calling API

### Symptoms
```
Access to fetch at 'http://localhost:8000/query' from origin 'http://localhost:1420'
has been blocked by CORS policy
```

### Cause
FastAPI CORS middleware not configured for Tauri's origin.

### Solution
The server should already have CORS configured in `server/main_improved.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

If still having issues, check that:
1. Server is running on port 8000
2. Client is using the correct API URL in `client/src/services/llm-improved.ts`

## Issue: Ollama not responding

### Symptoms
```
LLM Server: offline
Connection refused to http://localhost:11434
```

### Cause
Ollama service is not running or not accessible.

### Solution

**For Docker setup:**
```bash
# Check if Ollama container is running
docker compose ps

# Check Ollama logs
docker compose logs ollama

# Restart Ollama
docker compose restart ollama
```

**For manual setup:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

## Issue: Model not found

### Symptoms
```
Error: model 'llama3.2:1b' not found
```

### Cause
The specified model hasn't been downloaded to Ollama.

### Solution

**For Docker setup:**
```bash
# Pull model manually
docker exec -it inspektor-ollama ollama pull llama3.2:1b

# Or restart to trigger automatic pull
docker compose down
docker compose up -d
```

**For manual setup:**
```bash
# Pull model
ollama pull llama3.2:1b

# Verify
ollama list
```

## Issue: Out of memory when using large models

### Symptoms
```
Container killed (OOM)
Process killed: Insufficient memory
```

### Cause
Model requires more RAM than available.

### Solution

**Option 1: Use smaller model**
```yaml
# In docker-compose.yml
OLLAMA_MODEL=llama3.2:1b  # Only 2GB RAM needed
```

**Option 2: Increase Docker memory**
```
Docker Desktop → Settings → Resources → Memory
Increase to at least 8GB
```

**Option 3: Use quantized model**
```bash
ollama pull mistral:7b-instruct-q4_0  # 4-bit quantized, smaller
```

## Issue: Slow query responses

### Symptoms
Queries take 30+ seconds to complete.

### Cause
- Model is running on CPU (GPU would be faster)
- Model is too large for your hardware
- Network latency to database

### Solution

**Option 1: Enable GPU (if available)**
Uncomment GPU section in `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

**Option 2: Use smaller model**
```yaml
OLLAMA_MODEL=llama3.2:1b  # Much faster inference
```

**Option 3: Tune Ollama performance**
```yaml
environment:
  - OLLAMA_NUM_PARALLEL=4      # Process requests in parallel
  - OLLAMA_FLASH_ATTENTION=1   # Enable flash attention
```

## Issue: Database connection times out

### Symptoms
```
Error: Connection timeout
Failed to connect to database
```

### Cause
- Database server is not running
- Firewall blocking connection
- Wrong credentials

### Solution

1. **Verify database is running:**
```bash
# PostgreSQL
pg_isready -h localhost -p 5432

# MySQL
mysqladmin ping -h localhost -P 3306
```

2. **Check credentials:**
- Verify username/password
- Check database name exists
- Ensure user has access permissions

3. **Test connection manually:**
```bash
# PostgreSQL
psql -h localhost -p 5432 -U username -d database

# MySQL
mysql -h localhost -P 3306 -u username -p database
```

## Issue: Port already in use

### Symptoms
```
Error: bind: address already in use
Port 8000 is already allocated
```

### Cause
Another service is using the same port.

### Solution

**Option 1: Stop conflicting service**
```bash
# Find what's using the port
lsof -i :8000

# Kill the process
kill <PID>
```

**Option 2: Change port**
Edit `docker-compose.yml`:
```yaml
ports:
  - "9000:8000"  # Use 9000 on host instead
```

Update client API URL in `client/src/services/llm-improved.ts`:
```typescript
const API_BASE_URL = 'http://127.0.0.1:9000';
```

## Issue: TypeScript type errors

### Symptoms
```
Property 'schema' does not exist on type 'DatabaseCredentials'
```

### Cause
TypeScript types are out of sync with code changes.

### Solution

1. **Restart TypeScript server:**
   - VS Code: `Cmd+Shift+P` → "TypeScript: Restart TS Server"

2. **Clear cache and rebuild:**
```bash
cd client
rm -rf node_modules/.vite
npm run dev
```

## Issue: Rust compilation errors

### Symptoms
```
error[E0277]: the trait bound `X: Y` is not satisfied
```

### Cause
Dependency version mismatch or missing features.

### Solution

1. **Clean build:**
```bash
cd client/src-tauri
cargo clean
cargo build
```

2. **Update dependencies:**
```bash
cargo update
```

3. **Check Cargo.toml for typos:**
Ensure all feature flags are correct.

## Getting More Help

If your issue isn't listed here:

1. **Check logs:**
   - Docker: `docker compose logs -f`
   - Tauri: Look in the console/terminal
   - Server: `python main_improved.py` output

2. **Enable debug mode:**
   ```bash
   # Rust
   RUST_BACKTRACE=1 npm run tauri dev

   # Python
   PYTHONVERBOSE=1 python main_improved.py
   ```

3. **Check versions:**
   ```bash
   docker --version
   node --version
   python --version
   rustc --version
   ```

4. **Review documentation:**
   - [README.md](README.md)
   - [DEPLOYMENT.md](DEPLOYMENT.md)
   - [MODEL_SELECTION.md](MODEL_SELECTION.md)

5. **Open an issue:**
   Include:
   - Error message
   - Steps to reproduce
   - Your environment (OS, Docker version, etc.)
   - Relevant logs
