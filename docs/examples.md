# Example flows

## Standard project creation flow

```python
from pm_mcp.server import mcp

# create_project
# generate_project_plan
# create_task
# recommend_assignee
# assign_task
# analyze_project_risks
```

## Example AI conversation

User: "We need to build and launch a restaurant delivery website in 14 days."

Tool sequence:

1. create_project
2. generate_project_plan
3. list_team_members
4. recommend_assignee
5. assign_task
6. analyze_schedule
7. analyze_project_risks

## Example dry-run assignment

```python
result = await auto_assign_project(project_id=10, dry_run=True)
```

The response should include the proposed assignments without modifying the project.

## Example standup generation

```python
result = await generate_standup(project_id=1)
```

This returns per-member updates extracted from actual task data.
