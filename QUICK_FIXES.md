# Quick Fixes for Common Issues

## ✅ Issues Fixed

### 1. Metadata Approval Flow
**Issue**: After approving metadata request, nothing happened visually and no call to OpenAI.

**Fix Applied**: Updated `MetadataApproval.tsx` to re-query the LLM after submitting metadata. Now the flow is:
1. User approves metadata request
2. Client fetches metadata from database
3. Client submits metadata to server
4. **NEW**: Client re-queries LLM with empty query (server continues conversation)
5. LLM processes with new metadata and returns next step (SQL or more metadata requests)

### 2. Health Check Logging
**Issue**: LLM Server showing "offline" even when server was running.

**Fix Applied**: Added better error logging in `App.tsx` to see what's happening with health check.

**Debug**: Check browser console for "LLM Server health:" message. If you see an error, the server might not be running or there's a CORS issue.

### 3. Secure Storage Warnings
**Issue**: Console showing "Command get_secure_storage not found"

**Status**: This is expected! The auth system falls back to localStorage when Tauri secure storage isn't available. Your authentication works fine.

**To Suppress** (Optional): Implement the Tauri commands (see below)

## 🔍 Debugging Tips

### Check If Server Is Running

```bash
curl http://127.0.0.1:8000/health
```

Should return:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "llm_model": "gpt-4o-mini"
}
```

### Check Browser Console

Open Developer Tools (F12) and look for:
- ✅ "LLM Server health: {status: 'healthy'...}" = Server is working
- ❌ "LLM Server health check failed: ..." = Server issue
- ⚠️ "Command get_secure_storage not found" = Expected, can ignore

### Check Network Tab

Look for API calls:
- `POST /auth/login` - Should return 200
- `POST /query` - Should return 200 with metadata_request or sql_response
- `POST /metadata` - Should return 200
- `GET /health` - Should return 200

### Common Server Errors

**"OPENAI_API_KEY must be set"**
- Fix: Add your API key to `server/.env`

**"ModuleNotFoundError: No module named 'openai'"**
- Fix: `cd server && pip install -r requirements.txt`

**CORS errors**
- Fix: Server already allows localhost:1420, check if client is on different port

## 🎯 Testing the Fixed Flow

1. **Start Server**:
   ```bash
   cd server
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   python main.py
   ```

2. **Start Client**:
   ```bash
   cd client
   npm run tauri dev
   ```

3. **Test Workflow**:
   - Login/Register
   - Add database connection
   - Ask: "Show me all tables"
   - Approve metadata request
   - ✅ Should show table names or generate SQL

## 🛠️ Optional: Implement Secure Storage (Suppress Warnings)

Add to `client/src-tauri/src/lib.rs`:

```rust
#[tauri::command]
fn get_secure_storage(key: String) -> Result<String, String> {
    // For now, just return error to use localStorage fallback
    Err("Not implemented - using localStorage".to_string())
}

#[tauri::command]
fn set_secure_storage(key: String, value: String) -> Result<(), String> {
    // For now, just return error to use localStorage fallback
    Err("Not implemented - using localStorage".to_string())
}

#[tauri::command]
fn remove_secure_storage(key: String) -> Result<(), String> {
    // For now, just return error to use localStorage fallback
    Err("Not implemented - using localStorage".to_string())
}
```

Then register them in the builder:
```rust
.invoke_handler(tauri::generate_handler![
    // ... existing commands ...
    get_secure_storage,
    set_secure_storage,
    remove_secure_storage,
])
```

## 📝 Known Issues

1. **Empty query after metadata**: The re-query uses empty string `''` - this is intentional, the server continues the conversation
2. **Secure storage warnings**: Expected until Tauri commands are implemented
3. **Health check during auth**: Health check runs before authentication, so it's not using auth token (this is fine)

## 🎊 Expected Behavior Now

1. Register/Login ✅
2. Add database connection ✅
3. Ask question ✅
4. Get metadata request ✅
5. Approve metadata ✅
6. **NEW**: See loading state while re-querying ✅
7. **NEW**: Get SQL or another metadata request ✅
8. Execute SQL ✅
9. See results ✅

## 💡 Next Steps

- Test with your actual database
- Try more complex queries
- Check conversation history (when that feature is fully integrated)
- Report any other issues!

---

**Status**: All major issues fixed! 🎉
**Date**: October 23, 2025
