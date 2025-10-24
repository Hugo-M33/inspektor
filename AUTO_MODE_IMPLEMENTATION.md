# Auto Mode Implementation

## Overview
Auto Mode is a new feature that automatically approves metadata read tool calls (get_table_names, get_table_schema, get_relationships) to speed up SQL query generation while preventing infinite loops with a configurable safety limit.

## Features

### 1. **Auto-Approval Toggle**
- Checkbox in the query interface header to enable/disable auto mode
- Visual indicator when auto mode is active

### 2. **Configurable Limit**
- Number input to set max auto-approvals (1-10, default: 5)
- Hard cap at 10 to prevent abuse
- Counter display showing current progress (e.g., "3/5")

### 3. **Visual Feedback**
- Green border around metadata approval component when auto-approving
- "(Auto-approving...)" label during automatic approval
- Warning message when limit is reached
- Counter badge showing progress

### 4. **Safety Features**
- Per-conversation counter (resets on new conversation or conversation switch)
- Manual override: users can disable auto mode or approve manually anytime
- Clear visual distinction when in auto mode
- Warning when approaching/reaching limit

## Implementation Details

### Frontend Changes

#### 1. QueryInterface.tsx ([client/src/components/QueryInterface.tsx](client/src/components/QueryInterface.tsx))
- **State Management**:
  - `autoMode`: boolean to track if auto mode is enabled
  - `maxAutoApprovals`: number (1-10) for the limit
  - `autoApprovalCount`: tracks how many auto-approvals in current conversation

- **Counter Reset Logic**:
  - Resets when conversation ID changes
  - Resets when creating new conversation

- **UI Controls**:
  - Checkbox toggle for auto mode
  - Number input for max limit (validated to stay between 1-10)
  - Counter display showing current/max approvals

#### 2. MetadataApproval.tsx ([client/src/components/MetadataApproval.tsx](client/src/components/MetadataApproval.tsx))
- **Auto-Approval Logic**:
  - `useEffect` hook automatically triggers approval when:
    - Auto mode is enabled
    - Current count < max limit
    - Not already processing

- **Props Added**:
  - `autoMode`: boolean
  - `maxAutoApprovals`: number
  - `currentAutoApprovalCount`: number

- **Visual Indicators**:
  - Green border when auto-approving
  - Progress counter below actions
  - Warning when limit reached

- **Callback Enhancement**:
  - `onApproved` now accepts `wasAutoApproved` boolean parameter
  - Parent component increments counter when auto-approved

#### 3. App.css ([client/src/App.css](client/src/App.css))
- **New CSS Classes**:
  - `.auto-mode-controls`: Container for auto mode UI
  - `.auto-mode-toggle`: Checkbox and label styling
  - `.auto-mode-settings`: Max limit input and counter
  - `.auto-approval-counter`: Counter badge styling

### Backend Changes

**None required!** The implementation is entirely client-side, which provides:
- Simpler architecture
- No database schema changes
- Better user control
- Easier to modify limits in the future

The backend continues to work as before - it processes metadata requests and returns responses without needing to know about auto-approval.

## Usage

### For Users

1. **Enable Auto Mode**:
   - Check the "Auto Mode" checkbox in the query interface header
   - Optionally adjust the max limit (default is 5)

2. **Ask a Question**:
   - Type your natural language query and submit
   - Watch as metadata requests are automatically approved
   - Counter shows progress (e.g., "2/5")

3. **Monitor Progress**:
   - Green border indicates auto-approval in progress
   - Counter increments with each auto-approval
   - Warning appears when limit is reached

4. **Manual Override**:
   - Uncheck "Auto Mode" to disable anytime
   - Manually approve/reject if limit is reached
   - Counter resets when starting a new conversation

### Best Practices

- **Start with default limit (5)**: Works well for most queries
- **Increase limit for complex databases**: Use 7-10 for databases with many tables/relationships
- **Disable for sensitive operations**: Turn off auto mode when you want to review each metadata request
- **Monitor the counter**: Keep an eye on progress to understand how many metadata calls are needed

## Technical Notes

### Why Client-Side?

The decision to implement auto mode entirely on the client side provides several benefits:

1. **No Server Changes**: Backend remains stateless and simple
2. **Better UX**: Instant feedback without server roundtrips
3. **User Control**: Settings stored in browser session
4. **Easier Testing**: No database migrations or API changes

### Counter Scoping

The auto-approval counter is conversation-scoped:
- **Resets on new conversation**: Prevents cumulative limits across different queries
- **Resets on conversation switch**: Each conversation gets its own limit
- **Persists during conversation**: Prevents infinite loops within a single query session

### Safety Mechanisms

1. **Hard Cap**: Maximum limit is 10, regardless of user input
2. **Input Validation**: Number input automatically clamps to 1-10 range
3. **Visual Warnings**: Clear indication when limit is reached
4. **Manual Escape Hatch**: Users can always disable auto mode or approve manually

## Future Enhancements

Potential improvements for future versions:

1. **Persistent Settings**: Save auto mode preferences to localStorage
2. **Per-Database Limits**: Different limits for different database types
3. **Smart Defaults**: Adjust default limit based on database complexity
4. **Analytics**: Track which queries benefit most from auto mode
5. **Whitelist/Blacklist**: Auto-approve only specific metadata types

## Testing Checklist

- [x] Toggle auto mode on/off
- [x] Adjust max limit (test 1, 5, 10, and out-of-range values)
- [x] Counter increments correctly
- [x] Counter resets on new conversation
- [x] Counter resets when switching conversations
- [x] Visual indicators appear correctly
- [x] Warning shows when limit reached
- [x] Manual approval works when auto mode disabled
- [x] Manual approval works when limit reached
- [ ] End-to-end test with real database query
- [ ] Test with multiple rapid metadata requests
- [ ] Verify no infinite loops occur

## Related Files

- [client/src/components/QueryInterface.tsx](client/src/components/QueryInterface.tsx) - Main interface with auto mode controls
- [client/src/components/MetadataApproval.tsx](client/src/components/MetadataApproval.tsx) - Auto-approval logic
- [client/src/App.css](client/src/App.css) - Styling for auto mode UI
