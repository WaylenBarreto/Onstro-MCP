document.addEventListener('DOMContentLoaded', () => {
    fetchInitialData();
});

async function fetchInitialData() {
    try {
        const [membersRes, projectsRes] = await Promise.all([
            fetch('/api/members'),
            fetch('/api/projects')
        ]);
        
        const membersData = await membersRes.json();
        const projectsData = await projectsRes.json();

        renderSidebar('members-list', membersData.members, 'member');
        renderSidebar('projects-list', projectsData.projects, 'project');
    } catch (error) {
        console.error('Error fetching initial data:', error);
    }
}

function renderSidebar(elementId, items, type) {
    const list = document.getElementById(elementId);
    list.innerHTML = '';
    
    items.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item.name;
        li.dataset.id = item.id;
        li.addEventListener('click', () => {
            document.querySelectorAll('.nav-list li').forEach(el => el.classList.remove('active'));
            li.classList.add('active');
            
            if (type === 'member') {
                loadMemberInsights(item.id);
            } else {
                loadProjectInsights(item.id);
            }
        });
        list.appendChild(li);
    });
}

function showState(stateId) {
    document.querySelectorAll('.empty-state, .insights-view').forEach(el => {
        el.classList.remove('visible');
    });
    document.getElementById(stateId).classList.add('visible');
}

let currentProjectId = null;

async function loadMemberInsights(id) {
    showState('loading-state');
    try {
        const response = await fetch(`/api/insights/member/${id}`);
        const data = await response.json();
        
        if (!data.success) throw new Error(data.message);
        
        const { member, insights, pending_tasks, recent_activity } = data;
        
        // Header
        document.getElementById('m-name').textContent = member.name;
        document.getElementById('m-role').textContent = member.role || 'Team Member';
        document.getElementById('m-avatar').textContent = member.name.charAt(0);
        document.getElementById('view-title').textContent = `${member.name}'s Dashboard`;

        // Flagged Status
        const flagBadge = document.getElementById('m-flag-badge');
        const flagReason = document.getElementById('m-flag-reason');
        if (member.flagged) {
            flagBadge.style.display = 'inline-block';
            flagReason.style.display = 'block';
            flagReason.textContent = `⚠️ Flagged: ${member.flag_reason}`;
        } else {
            flagBadge.style.display = 'none';
            flagReason.style.display = 'none';
        }

        // Stats
        document.getElementById('m-hours-worked').textContent = `${insights.hours_worked || 0.0} hrs`;
        document.getElementById('m-completion').textContent = `${insights.completion_rate}%`;
        document.getElementById('m-completed').textContent = insights.completed_tasks_count;
        document.getElementById('m-pending').textContent = insights.pending_tasks_count;
        document.getElementById('m-overdue').textContent = insights.overdue_tasks_count;
        
        // Recent Activity
        const activityList = document.getElementById('m-recent-activity');
        activityList.innerHTML = '';
        if (recent_activity.length === 0) {
            activityList.innerHTML = '<li>No recent activity found.</li>';
        }
        recent_activity.forEach(task => {
            activityList.innerHTML += `
                <li>
                    <div class="task-title">${task.title} <span style="font-size: 0.7em; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.1); margin-left: 6px;">${task.status}</span></div>
                    <div class="task-meta">Updated: ${new Date(task.updated_at).toLocaleDateString()}</div>
                </li>
            `;
        });

        // Pending Tasks
        const pendingList = document.getElementById('m-pending-tasks');
        pendingList.innerHTML = '';
        if (pending_tasks.length === 0) {
            pendingList.innerHTML = '<li>No pending tasks.</li>';
        }
        pending_tasks.forEach(task => {
            const isOverdue = task.due_date && new Date(task.due_date) < new Date();
            pendingList.innerHTML += `
                <li>
                    <div class="task-title" style="${isOverdue ? 'color: var(--accent-red);' : ''}">${task.title}</div>
                    <div class="task-meta">Priority: ${task.priority} | Due: ${task.due_date || 'None'}</div>
                </li>
            `;
        });

        showState('member-insights');
    } catch (error) {
        console.error(error);
        alert('Failed to load member insights');
        showState('welcome-state');
    }
}

function downloadTeamCSV() {
    window.location.href = '/api/reports/team/csv';
}

function downloadProjectCSV() {
    if (currentProjectId) {
        window.location.href = `/api/reports/project/${currentProjectId}/csv`;
    } else {
        window.location.href = '/api/reports/team/csv';
    }
}

async function loadProjectInsights(id) {
    currentProjectId = id;
    showState('loading-state');
    try {
        const response = await fetch(`/api/insights/project/${id}`);
        const data = await response.json();
        
        if (!data.success) throw new Error(data.message);
        
        const { project, insights, member_activity, items_to_report } = data;
        
        // Header
        document.getElementById('p-name').textContent = project.name;
        document.getElementById('view-title').textContent = `${project.name} Dashboard`;

        const descContainer = document.getElementById('p-description-container');
        const descEl = document.getElementById('p-description');
        if (descContainer && descEl) {
            if (project.description && project.description.trim()) {
                descEl.textContent = project.description;
                descContainer.style.display = 'block';
            } else {
                descContainer.style.display = 'none';
            }
        }

        // Stats
        document.getElementById('p-completion').textContent = `${insights.completion_rate}%`;
        document.getElementById('p-total').textContent = insights.total_tasks;
        document.getElementById('p-blocked').textContent = insights.blocked_tasks;
        document.getElementById('p-overdue').textContent = insights.overdue_tasks;
        
        // Active Members
        const activeList = document.getElementById('p-active-members');
        activeList.innerHTML = '';
        if (member_activity.length === 0) {
            activeList.innerHTML = '<li>No member activity logged.</li>';
        }
        member_activity.forEach(member => {
            activeList.innerHTML += `
                <li>
                    <div class="task-title">${member.name}</div>
                    <div class="task-meta">Completed ${member.tasks_completed} of ${member.tasks_assigned} assigned tasks</div>
                </li>
            `;
        });

        // Reports
        const reportsList = document.getElementById('p-reports');
        reportsList.innerHTML = '';
        items_to_report.forEach(item => {
            reportsList.innerHTML += `
                <li>
                    <div class="task-title">${item}</div>
                </li>
            `;
        });

        showState('project-insights');
    } catch (error) {
        console.error(error);
        alert('Failed to load project insights');
        showState('welcome-state');
    }
}

// ========== Create Project Modal ==========

function openCreateProjectModal() {
    const modal = document.getElementById('create-project-modal');
    modal.classList.add('visible');
    document.body.style.overflow = 'hidden';

    // Bind click event directly on button to ensure it fires reliably
    const aiBtn = document.getElementById('build-with-ai-btn');
    if (aiBtn) {
        aiBtn.onclick = handleBuildWithAI;
    }

    setTimeout(() => {
        const titleEl = document.getElementById('project-title');
        if (titleEl) titleEl.focus();
    }, 300);
}

function closeCreateProjectModal() {
    const modal = document.getElementById('create-project-modal');
    modal.classList.remove('visible');
    document.body.style.overflow = '';
    // Reset after close animation
    setTimeout(() => resetCreateProjectModal(), 300);
}

function handleModalOverlayClick(event) {
    if (event.target === event.currentTarget) {
        closeCreateProjectModal();
    }
}

function resetCreateProjectModal() {
    document.getElementById('create-project-form').reset();
    document.getElementById('modal-form-step').style.display = '';
    document.getElementById('modal-result-step').style.display = 'none';
    const submitBtn = document.getElementById('submit-create-btn');
    submitBtn.disabled = false;
    submitBtn.querySelector('.btn-text').textContent = 'Create with MCP';
    submitBtn.querySelector('.btn-spinner').style.display = 'none';

    const aiBtn = document.getElementById('build-with-ai-btn');
    if (aiBtn) {
        aiBtn.disabled = false;
        const btnText = aiBtn.querySelector('.btn-text');
        if (btnText) btnText.textContent = 'Enhance with AI';
        const btnSpinner = aiBtn.querySelector('.btn-spinner');
        if (btnSpinner) btnSpinner.style.display = 'none';
    }
}

async function handleBuildWithAI(event) {
    if (event) {
        if (typeof event.preventDefault === 'function') event.preventDefault();
        if (typeof event.stopPropagation === 'function') event.stopPropagation();
    }

    console.log('[Build with AI] Triggered');

    const titleEl = document.getElementById('project-title');
    const descEl = document.getElementById('project-description');
    const aiBtn = document.getElementById('build-with-ai-btn');

    let title = titleEl ? titleEl.value.trim() : '';
    let description = descEl ? descEl.value.trim() : '';

    if (!title && !description) {
        title = 'New Project Initiative';
    }

    // Set loading UI state
    let btnText = null;
    let btnSpinner = null;
    if (aiBtn) {
        aiBtn.disabled = true;
        btnText = aiBtn.querySelector('.btn-text');
        btnSpinner = aiBtn.querySelector('.btn-spinner');
        if (btnText) btnText.textContent = 'Enhancing with AI...';
        if (btnSpinner) btnSpinner.style.display = 'inline-block';
    }

    try {
        console.log('[Build with AI] Sending fetch request to /api/ai/enhance-project:', { title, description });
        const response = await fetch('/api/ai/enhance-project', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'AI enhancement failed');
        }

        const data = await response.json();
        console.log('[Build with AI] Received response:', data);

        if (data.title && titleEl) {
            titleEl.value = data.title;
            titleEl.classList.remove('field-ai-updated');
            void titleEl.offsetWidth; // trigger reflow for animation
            titleEl.classList.add('field-ai-updated');
        }
        if (data.description && descEl) {
            descEl.value = data.description;
            descEl.classList.remove('field-ai-updated');
            void descEl.offsetWidth; // trigger reflow for animation
            descEl.classList.add('field-ai-updated');
        }

        setTimeout(() => {
            if (titleEl) titleEl.classList.remove('field-ai-updated');
            if (descEl) descEl.classList.remove('field-ai-updated');
        }, 2000);

    } catch (error) {
        console.error('[Build with AI] Error:', error);
        alert(`AI Error: ${error.message}`);
    } finally {
        if (aiBtn) {
            aiBtn.disabled = false;
            if (btnText) btnText.textContent = 'Enhance with AI';
            if (btnSpinner) btnSpinner.style.display = 'none';
        }
    }
}

async function handleCreateProject(event) {
    event.preventDefault();

    const title = document.getElementById('project-title').value.trim();
    const description = document.getElementById('project-description').value.trim();
    const priority = document.getElementById('project-priority').value;

    if (!title) return;

    // Set loading state
    const submitBtn = document.getElementById('submit-create-btn');
    submitBtn.disabled = true;
    submitBtn.querySelector('.btn-text').textContent = 'Processing...';
    submitBtn.querySelector('.btn-spinner').style.display = 'inline-block';

    try {
        const response = await fetch('/api/projects/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description, priority }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to create project');
        }

        const data = await response.json();

        // Populate the comparison view
        document.getElementById('original-title').textContent = data.original.title;
        document.getElementById('original-description').textContent =
            data.original.description || '(no description provided)';
        document.getElementById('mcp-title').textContent = data.mcp_modified.title;
        document.getElementById('mcp-description').textContent = data.mcp_modified.description;

        // Switch to result step
        document.getElementById('modal-form-step').style.display = 'none';
        document.getElementById('modal-result-step').style.display = '';

        // Refresh the sidebar projects list
        refreshProjectsList();
    } catch (error) {
        console.error('Create project error:', error);
        alert(`Error: ${error.message}`);
        submitBtn.disabled = false;
        submitBtn.querySelector('.btn-text').textContent = 'Create with MCP';
        submitBtn.querySelector('.btn-spinner').style.display = 'none';
    }
}

async function refreshProjectsList() {
    try {
        const res = await fetch('/api/projects');
        const data = await res.json();
        renderSidebar('projects-list', data.projects, 'project');
    } catch (error) {
        console.error('Error refreshing projects:', error);
    }
}

// ========== Log Work Time Modal ==========

async function openLogTimeModal() {
    const modal = document.getElementById('log-time-modal');
    const memberSelect = document.getElementById('log-member-select');
    const taskSelect = document.getElementById('log-task-select');

    memberSelect.innerHTML = '<option value="">Loading members...</option>';
    taskSelect.innerHTML = '<option value="">Loading tasks...</option>';

    modal.classList.add('visible');
    document.body.style.overflow = 'hidden';

    try {
        const [membersRes, projectsRes] = await Promise.all([
            fetch('/api/members'),
            fetch('/api/projects')
        ]);
        const membersData = await membersRes.json();
        const projectsData = await projectsRes.json();

        // Populate members
        memberSelect.innerHTML = '<option value="">Select Member...</option>';
        (membersData.members || []).forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = `${m.name} (${m.role || 'Member'})`;
            memberSelect.appendChild(opt);
        });

        // Populate tasks across all projects
        taskSelect.innerHTML = '<option value="">Select Task...</option>';
        const projectList = projectsData.projects || [];
        for (const proj of projectList) {
            try {
                const tasksRes = await fetch(`/api/projects/${proj.id}/tasks`);
                const tasksData = await tasksRes.json();
                const tasks = tasksData.tasks || [];
                if (tasks.length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = proj.name;
                    tasks.forEach(t => {
                        const opt = document.createElement('option');
                        opt.value = t.id;
                        opt.textContent = `#${t.id} - ${t.title} [${t.status}]`;
                        optgroup.appendChild(opt);
                    });
                    taskSelect.appendChild(optgroup);
                }
            } catch (err) {
                console.error(`Error loading tasks for project ${proj.id}:`, err);
            }
        }
    } catch (error) {
        console.error('Error opening log time modal:', error);
        alert('Failed to load members or tasks for time logging.');
    }
}

function closeLogTimeModal() {
    const modal = document.getElementById('log-time-modal');
    modal.classList.remove('visible');
    document.body.style.overflow = '';
    document.getElementById('log-time-form').reset();
}

function handleLogTimeModalOverlayClick(event) {
    if (event.target === event.currentTarget) {
        closeLogTimeModal();
    }
}

async function handleLogTime(event) {
    event.preventDefault();

    const memberId = parseInt(document.getElementById('log-member-select').value);
    const taskId = parseInt(document.getElementById('log-task-select').value);
    const hoursLogged = parseFloat(document.getElementById('log-hours-input').value);
    const description = document.getElementById('log-desc-input').value.trim();

    if (!memberId || !taskId || isNaN(hoursLogged) || hoursLogged <= 0) {
        alert('Please fill out all required fields with valid values.');
        return;
    }

    const submitBtn = document.getElementById('submit-log-time-btn');
    submitBtn.disabled = true;
    submitBtn.querySelector('.btn-text').textContent = 'Submitting...';
    submitBtn.querySelector('.btn-spinner').style.display = 'inline-block';

    try {
        const response = await fetch(`/api/tasks/${taskId}/log-time`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                member_id: memberId,
                hours_logged: hoursLogged,
                description: description
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to log work time');
        }

        const data = await response.json();
        closeLogTimeModal();

        // Refresh active dashboard view
        const activeMember = document.querySelector('#members-list li.active');
        if (activeMember && activeMember.dataset.id) {
            loadMemberInsights(activeMember.dataset.id);
        } else if (currentProjectId) {
            loadProjectInsights(currentProjectId);
        }

        alert(`⏱️ Successfully logged ${hoursLogged} hours!`);
    } catch (error) {
        console.error('Log time error:', error);
        alert(`Error: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.querySelector('.btn-text').textContent = 'Submit Log';
        submitBtn.querySelector('.btn-spinner').style.display = 'none';
    }
}

