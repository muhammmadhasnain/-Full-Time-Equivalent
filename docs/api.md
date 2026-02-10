# API Documentation: AI Employee Foundation

## Management API

### Vault Operations

#### GET /vault/stats
**Description**: Retrieve vault statistics and system health metrics

**Request**:
- Method: GET
- Path: `/vault/stats`
- Headers: None required
- Parameters: None

**Response**:
```
{
  "total_actions": 12,
  "pending_approvals": 3,
  "processed_today": 8,
  "system_health": "operational",
  "last_updated": "2026-02-06T10:30:00Z",
  "watchers_active": true,
  "claude_connected": true
}
```

**Status Codes**:
- 200: Success
- 500: Internal server error

#### GET /vault/actions/pending
**Description**: Retrieve list of pending actions

**Request**:
- Method: GET
- Path: `/vault/actions/pending`
- Headers: None required
- Parameters: None

**Response**:
```
{
  "actions": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "type": "meeting_request",
      "priority": "medium",
      "created_at": "2026-02-06T09:00:00Z",
      "source": "gmail"
    }
  ]
}
```

**Status Codes**:
- 200: Success
- 500: Internal server error

### Watcher Control

#### POST /watcher/{source}/start
**Description**: Start a specific watcher service

**Path Parameters**:
- `source`: Watcher source (e.g., "gmail", "filesystem")

**Request**:
- Method: POST
- Path: `/watcher/{source}/start`
- Headers: None required
- Body: None

**Response**:
```
{
  "status": "started",
  "source": "gmail",
  "timestamp": "2026-02-06T10:30:00Z"
}
```

**Status Codes**:
- 200: Success
- 400: Invalid source
- 500: Internal server error

#### POST /watcher/{source}/stop
**Description**: Stop a specific watcher service

**Path Parameters**:
- `source`: Watcher source (e.g., "gmail", "filesystem")

**Request**:
- Method: POST
- Path: `/watcher/{source}/stop`
- Headers: None required
- Body: None

**Response**:
```
{
  "status": "stopped",
  "source": "gmail",
  "timestamp": "2026-02-06T10:30:00Z"
}
```

**Status Codes**:
- 200: Success
- 400: Invalid source
- 500: Internal server error

### Claude Integration

#### POST /claude/process-action
**Description**: Submit an action for Claude processing

**Request**:
- Method: POST
- Path: `/claude/process-action`
- Headers:
  - Content-Type: application/json
- Body:
```
{
  "action_id": "123e4567-e89b-12d3-a456-426614174000",
  "action_content": {
    // Action file content as JSON
  }
}
```

**Response**:
```
{
  "plan_id": "123e4567-e89b-12d3-a456-426614174001",
  "status": "created",
  "timestamp": "2026-02-06T10:30:00Z"
}
```

**Status Codes**:
- 200: Success
- 400: Invalid action content
- 500: Internal server error

### Approval Workflow

#### POST /approvals/{action_id}/approve
**Description**: Approve an action for execution

**Path Parameters**:
- `action_id`: ID of the action to approve

**Request**:
- Method: POST
- Path: `/approvals/{action_id}/approve`
- Headers: None required
- Body: None

**Response**:
```
{
  "action_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "approved",
  "execution_scheduled": true,
  "timestamp": "2026-02-06T10:30:00Z"
}
```

**Status Codes**:
- 200: Success
- 404: Action not found
- 500: Internal server error

## CLI Commands

### Vault Commands
- `vault init`: Initialize the Obsidian vault structure
- `vault check`: Check vault integrity
- `vault pending-actions`: View pending actions
- `vault stats`: View system statistics

### Watcher Commands
- `watch start`: Start the watcher service
- `watch stop`: Stop the watcher service
- `config gmail`: Configure Gmail integration

### System Commands
- `start`: Start the orchestrator with all services