# Tools

## Project tools

### create_project
- Purpose: create a project
- Type: WRITE
- Input: name, description, priority, start_date, due_date, owner_id
- Output: project object and metadata

### get_project
- Purpose: retrieve complete project data
- Type: READ

### list_projects
- Purpose: list projects with optional filters
- Type: READ

### update_project
- Purpose: update project fields
- Type: WRITE

### delete_project
- Purpose: permanently delete a project
- Type: DESTRUCTIVE

## Task tools

### create_task
- Purpose: create a task within a project
- Type: WRITE

### get_task
- Purpose: retrieve a task
- Type: READ

### list_tasks
- Purpose: list tasks with optional filters
- Type: READ

### update_task
- Purpose: modify task fields
- Type: WRITE

### delete_task
- Purpose: permanently delete a task
- Type: DESTRUCTIVE

### complete_task
- Purpose: mark a task as complete
- Type: WRITE

### create_subtask
- Purpose: create child tasks
- Type: WRITE

## Team tools

### list_team_members
- Purpose: list available team members
- Type: READ

### get_team_member
- Purpose: fetch one member
- Type: READ

### get_member_skills
- Purpose: return available skills
- Type: READ

### get_member_workload
- Purpose: return workload metrics for a member
- Type: READ

### get_team_workload
- Purpose: summarize team capacity and utilization
- Type: READ

## Assignment tools

### recommend_assignee
- Purpose: deterministic recommendation engine
- Type: READ

### assign_task
- Purpose: assign a task to a team member
- Type: WRITE

### auto_assign_project
- Purpose: suggest assignments for all project tasks
- Type: WRITE, supports dry_run

## Planning tools

### generate_project_plan
- Purpose: create a structured project plan
- Type: READ/PLANNING

### recommend_project_roles
- Purpose: recommend role coverage based on team members
- Type: READ

### generate_subtasks
- Purpose: break a task into implementation steps
- Type: READ/PLANNING

## Analysis tools

### analyze_dependencies
- Purpose: check blockers and dependency chains
- Type: READ

### analyze_project_risks
- Purpose: inspect project-level delivery risk
- Type: READ

### analyze_team_workload
- Purpose: identify over- and under-utilization
- Type: READ

### rebalance_project_workload
- Purpose: propose or apply workload rebalancing
- Type: WRITE, supports dry_run

### analyze_schedule
- Purpose: assess schedule feasibility
- Type: READ

### detect_duplicate_tasks
- Purpose: detect likely duplicate tasks
- Type: READ

## Reporting tools

### generate_project_report
- Purpose: summarize project health
- Type: READ

### generate_team_report
- Purpose: summarize member workload and assignment load
- Type: READ

### generate_standup
- Purpose: provide team standup updates from task data
- Type: READ
