# Metadata Loop Fix

## Problem

The LLM was requesting the same metadata repeatedly in a loop:
1. User asks: "Show me all tables"
2. LLM requests: table names
3. User approves → Metadata submitted
4. LLM requests: table names again (LOOP!)

## Root Cause

The issue was in how we handled the "continuation" after metadata approval:

1. **Duplicate User Messages**: When re-querying after metadata approval, the same query was added to conversation history multiple times
2. **No Continuation Context**: The agent didn't understand it should continue with new metadata
3. **Metadata Not Visible**: Even though metadata was cached, the agent treated each request as a new query

## The Fix (3 Parts)

### 1. Skip Empty User Messages (`server/main.py`)

```python
# Only add user message if not empty (empty means continuation after metadata)
if request.query.strip():
    session_manager.add_message(
        db, conversation.id, "user", request.query
    )
```

**Why**: Prevents duplicate user messages when continuing after metadata approval.

### 2. Send Empty Query After Metadata (`client/src/components/MetadataApproval.tsx`)

```typescript
// Re-query with empty string to signal continuation
const response = await processQuery(databaseId, '', conversationId);
```

**Why**: Empty query signals "continue the conversation with new metadata" instead of "start a new query".

### 3. Handle Empty Query in Agent (`server/agent_openai.py`)

```python
if query.strip():
    user_message = f"User query: {query}"
else:
    # Empty query means: continue with the conversation using new metadata
    user_message = "Please continue processing the previous query with the updated metadata."
```

**Why**: Tells the LLM explicitly to continue with updated metadata instead of treating it as a new request.

## Flow After Fix

### Before (Broken)
```
1. User: "Show me all tables"
2. LLM: "I need table names" → requests tables
3. [User approves]
4. User: "Show me all tables" (duplicate!)
5. LLM: "I need table names" (LOOP - doesn't see cached metadata)
```

### After (Fixed)
```
1. User: "Show me all tables"
2. LLM: "I need table names" → requests tables
3. [User approves, metadata cached]
4. System: "Continue with updated metadata"
   - Metadata shown to LLM
   - Conversation history preserved
5. LLM: "Here's the SQL to show tables" → generates SQL ✅
```

## How It Works Now

1. **First Query**:
   - User submits question
   - LLM analyzes and requests metadata
   - Server saves: `User: "Show me all tables"`, `Assistant: "Need table names"`

2. **After Metadata Approval**:
   - Client fetches metadata from database
   - Client submits metadata to server cache
   - Client calls `/query` with `query=""` and `conversation_id`
   - Server sees empty query → doesn't add new user message
   - Agent sees empty query → adds continuation message
   - Agent gets conversation history + cached metadata
   - LLM sees: original question + previous request + NEW metadata
   - LLM continues logically (either more metadata or SQL)

3. **Multiple Metadata Requests**:
   - Process repeats until LLM has enough info
   - Each iteration adds to cached metadata
   - LLM sees cumulative metadata each time
   - Eventually generates SQL when satisfied

## Testing

Test with these queries to verify the fix:

### Simple (1 metadata request)
```
"Show me all tables"
→ Should request table names
→ Approve
→ Should generate SQL (not request again!)
```

### Medium (2-3 metadata requests)
```
"Show me the structure of the users table"
→ Should request table names
→ Approve
→ Should request schema for 'users'
→ Approve
→ Should generate SQL to describe table
```

### Complex (3+ metadata requests)
```
"Show me all orders with their customer names"
→ Should request table names
→ Approve
→ Should request schema for relevant tables
→ Approve
→ Should request relationships for JOIN
→ Approve
→ Should generate SQL with proper JOIN
```

## Debug Tips

If you still see loops:

1. **Check Server Logs** - Look for:
   ```
   INFO: LLM called function: get_table_names
   ```
   Should only appear once per metadata type per conversation

2. **Check Browser Console** - Look for:
   ```
   POST /metadata → 200 (metadata submitted)
   POST /query → 200 (continuation)
   ```

3. **Check Metadata Cache**:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://127.0.0.1:8000/cache/your-database-id
   ```
   Should show accumulated metadata

4. **Check Conversation History**:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://127.0.0.1:8000/conversations/CONVERSATION_ID
   ```
   Should NOT have duplicate user messages

## Files Changed

1. **`server/main.py`** (Line ~355):
   - Added check to skip empty queries

2. **`server/agent_openai.py`** (Line ~108):
   - Added logic to handle empty query as continuation

3. **`client/src/components/MetadataApproval.tsx`** (Line ~69):
   - Changed to send empty query for continuation

4. **`client/src/components/QueryInterface.tsx`** (Line ~144):
   - Pass `originalQuery` to MetadataApproval (for context)

## Expected Behavior

✅ **Correct**: Metadata requested once, approved, then LLM generates SQL
❌ **Wrong**: Metadata requested, approved, requested again (loop)

---

**Status**: Fixed! 🎉
**Date**: October 23, 2025
**Issue**: Metadata loop
**Root Cause**: Continuation not properly signaled to LLM
**Solution**: Empty query pattern with explicit continuation message
