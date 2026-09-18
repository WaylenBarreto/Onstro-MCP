# C# ASP.NET Core API Contract

This document defines the minimum endpoints required for the Python MCP server to communicate with the PM platform.

## Base URL

- PM_API_BASE_URL is configured in environment settings.
- Example: http://localhost:5000/api

## Project endpoints

### POST /api/projects
Request body:

```json
{
  "name": "Restaurant Delivery Website",
  "description": "Build launch-ready website",
  "priority": "HIGH",
  "startDate": "2026-09-20",
  "dueDate": "2026-10-04",
  "ownerId": 1
}
```

Response body:

```json
{
  "id": 1,
  "name": "Restaurant Delivery Website",
  "description": "Build launch-ready website",
  "status": "ACTIVE",
  "priority": "HIGH",
  "ownerId": 1,
  "startDate": "2026-09-20",
  "dueDate": "2026-10-04",
  "createdAt": "2026-09-18T10:00:00Z",
  "updatedAt": "2026-09-18T10:00:00Z"
}
```

### GET /api/projects
Response:

```json
[
  {
    "id": 1,
    "name": "Restaurant Delivery Website",
    "status": "ACTIVE"
  }
]
```

### GET /api/projects/{projectId}
Response:

```json
{
  "id": 1,
  "name": "Restaurant Delivery Website",
  "status": "ACTIVE",
  "priority": "HIGH",
  "ownerId": 1
}
```

### PATCH /api/projects/{projectId}
Request body:

```json
{
  "name": "Updated project name",
  "status": "ON_HOLD"
}
```

### DELETE /api/projects/{projectId}
Response:

```json
{
  "success": true
}
```

## Task endpoints

### POST /api/tasks
Request body:

```json
{
  "projectId": 1,
  "title": "Payment integration",
  "description": "Implement checkout flow",
  "priority": "HIGH",
  "estimatedHours": 16,
  "dueDate": "2026-09-28",
  "assigneeId": 5,
  "parentTaskId": null,
  "dependencies": []
}
```

### GET /api/tasks
Response:

```json
[
  {
    "id": 10,
    "projectId": 1,
    "title": "Payment integration",
    "status": "TODO",
    "priority": "HIGH"
  }
]
```

### GET /api/tasks/{taskId}
Response:

```json
{
  "id": 10,
  "projectId": 1,
  "title": "Payment integration",
  "status": "TODO",
  "priority": "HIGH"
}
```

### PATCH /api/tasks/{taskId}
Request body:

```json
{
  "status": "IN_PROGRESS",
  "assigneeId": 2
}
```

### POST /api/tasks/{taskId}/complete
Response:

```json
{
  "id": 10,
  "status": "DONE"
}
```

### POST /api/tasks/{taskId}/assign
Request body:

```json
{
  "memberId": 2
}
```

### DELETE /api/tasks/{taskId}
Response:

```json
{
  "success": true
}
```

## Team endpoints

### GET /api/team/members
Response:

```json
[
  {
    "id": 1,
    "name": "Alice",
    "role": "Project Manager",
    "skills": ["planning", "risk", "communication"],
    "availability": 0.8,
    "maxWeeklyHours": 40,
    "currentWorkload": 18
  }
]
```

### GET /api/team/members/{memberId}
Response:

```json
{
  "id": 1,
  "name": "Alice",
  "role": "Project Manager",
  "skills": ["planning", "risk"],
  "availability": 0.8,
  "maxWeeklyHours": 40,
  "currentWorkload": 18
}
```

### GET /api/team/members/{memberId}/workload
Response:

```json
{
  "memberId": 1,
  "assignedHours": 22,
  "maximumHours": 40,
  "utilizationPercentage": 55,
  "activeTaskCount": 3,
  "overdueTaskCount": 1
}
```

### GET /api/team/workload
Response:

```json
{
  "members": [
    {
      "memberId": 1,
      "name": "Alice",
      "assignedHours": 22,
      "maximumHours": 40,
      "utilizationPercentage": 55,
      "activeTaskCount": 3,
      "overdueTaskCount": 1
    }
  ]
}
```

## Error responses

Error responses should follow a consistent JSON format:

```json
{
  "message": "Project 123 was not found.",
  "error": "PROJECT_NOT_FOUND"
}
```

## Notes

- The server validates input locally before calling the API.
- Production behavior should still preserve a clean separation between Python and the C# application.
- Only the configured base URL should be used; no raw database access should occur in the Python layer.
