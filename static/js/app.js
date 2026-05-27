/**
 * Main Application Logic for simplified Projects AI Assistant
 */
const State = {
    projects: [],
    activeProject: null,
    conversationId: null,
    generalChatHistory: [],
    selectedImageFile: null,
};

// DOM Elements
const El = {
    projectList: document.getElementById('project-list'),
    projectHeader: document.getElementById('project-header'),
    projectName: document.getElementById('active-project-name'),
    projectDesc: document.getElementById('active-project-desc'),
    chatHistory: document.getElementById('chat-history'),
    chatInput: document.getElementById('chat-input'),
    btnSend: document.getElementById('btn-send'),
    btnNewProject: document.getElementById('btn-new-project'),
    btnUpload: document.getElementById('btn-upload'),
    fileInput: document.getElementById('file-upload'),
    toolIndicator: document.getElementById('tool-indicator'),
    modalContainer: document.getElementById('modal-container'),
    modalContent: document.getElementById('modal-content'),
    btnEditDesc: document.getElementById('btn-edit-desc'),
    btnDeleteProject: document.getElementById('btn-delete-project'),
    btnOrganizeMemory: document.getElementById('btn-organize-memory'),
    btnGeneralChat: document.getElementById('btn-general-chat'),
    imagePreviewContainer: document.getElementById('image-preview-container'),
    imagePreviewThumbnail: document.getElementById('image-preview-thumbnail'),
    imagePreviewFilename: document.getElementById('image-preview-filename'),
    btnRemoveImage: document.getElementById('btn-remove-image'),
};

/**
 * Initialize App
 */
async function init() {
    // Dynamic sidebar status dot based on active API network requests
    API.onStatusChange = isBusy => {
        const dot = document.getElementById('sidebar-status-dot');
        const text = document.getElementById('sidebar-status-text');
        if (!dot || !text) return;
        
        if (isBusy) {
            dot.className = 'status-dot offline'; // Turns red pulsing
            text.innerText = '🔴 Generating Response...';
        } else {
            dot.className = 'status-dot online'; // Turns green glowing
            text.innerText = '🟢 Ready to Help';
        }
    };

    setupEventListeners();
    await loadProjects();
}

/**
 * Load & Render Project List
 */
async function loadProjects() {
    try {
        State.projects = await API.getProjects();
        renderProjectList();
    } catch (err) {
        console.error('Failed to load projects:', err);
    }
}

function renderProjectList() {
    El.projectList.innerHTML = State.projects.map(p => `
        <div class="project-item ${State.activeProject?.id === p.id ? 'active' : ''}" 
             onclick="selectProject('${p.id}')">
            <h4>${p.name}</h4>
            <p>${p.description || 'No description'}</p>
        </div>
    `).join('');
}

/**
 * Select a Project
 */
async function selectProject(id) {
    const project = State.projects.find(p => p.id === id);
    if (!project) return;

    State.activeProject = project;
    State.conversationId = null; 
    renderProjectList();

    // Update Header
    El.projectName.innerText = project.name;
    El.projectDesc.innerText = project.description || 'No description provided.';
    El.projectHeader.classList.remove('hidden');

    // Reset Chat & Load History
    El.chatHistory.innerHTML = '<div class="loading-spinner" style="margin: 20px auto;"></div>';
    
    try {
        const conversations = await API.getConversations(project.id);
        if (conversations && conversations.length > 0) {
            // Sort by created_at desc (most recent first) to get latest conversation
            conversations.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            State.conversationId = conversations[0].id;
            
            const messages = await API.getMessages(project.id, State.conversationId);
            El.chatHistory.innerHTML = '';
            
            if (messages && messages.length > 0) {
                // Filter and append user and assistant messages
                messages.forEach(msg => {
                    if (msg.role === 'user') {
                        appendMessage('user', msg.content);
                    } else if (msg.role === 'assistant') {
                        appendMessage('ai', msg.content);
                    }
                });
            } else {
                appendMessage('ai', "How can I assist you?");
            }
        } else {
            El.chatHistory.innerHTML = '';
            appendMessage('ai', "How can I assist you?");
        }
    } catch (err) {
        console.error('Failed to load chat history:', err);
        El.chatHistory.innerHTML = '';
        appendMessage('ai', "How can I assist you?");
    }
}

/**
 * Chat Console Logic
 */
async function sendChat() {
    const text = El.chatInput.value.trim();
    const hasImage = !!State.selectedImageFile;

    if (!text && !hasImage) return;

    // --- Scenario A: Sending an Image with or without a custom prompt ---
    if (hasImage) {
        const file = State.selectedImageFile;
        removeSelectedImage();
        El.chatInput.value = '';

        // 1. Show user inputs (image thumbnail + prompt text if any)
        const localPreviewUrl = URL.createObjectURL(file);
        appendImageMessage('user', localPreviewUrl);
        if (text) {
            appendMessage('user', text);
        }

        El.toolIndicator.classList.remove('hidden');
        appendMessage('ai', 'Analyzing your image...');

        // Branch by Active Project vs General Assistant
        if (State.activeProject) {
            try {
                // Project upload
                const formData = new FormData();
                formData.append('file', file);

                const uploadRes = await fetch(`/projects/${State.activeProject.id}/images/upload`, {
                    method: 'POST',
                    body: formData
                });
                if (!uploadRes.ok) throw new Error('Upload failed');
                const imageData = await uploadRes.json();

                // Gemini Project Analysis with custom prompt
                const analysis = await API.analyzeImage(State.activeProject.id, imageData.id, text || null);
                appendMessage('ai', `**Analysis Summary:**\n${analysis.analysis}`);
            } catch (err) {
                appendMessage('ai', 'Vision Analysis Error: ' + err.message);
            } finally {
                El.toolIndicator.classList.add('hidden');
            }
        } else {
            // General Chat stateless upload + analysis
            try {
                const res = await API.generalAnalyzeImage(file, text || null);
                appendMessage('ai', `**Analysis Summary:**\n${res.analysis}`);
            } catch (err) {
                appendMessage('ai', 'Vision Analysis Error: ' + err.message);
            } finally {
                El.toolIndicator.classList.add('hidden');
            }
        }
        return;
    }

    // --- Scenario B: Normal Text Message ---
    if (!State.activeProject) {
        appendMessage('user', text);
        El.chatInput.value = '';
        El.toolIndicator.classList.remove('hidden');
        
        try {
            const history = State.generalChatHistory || [];
            const res = await API.generalChat(text, history);
            
            history.push({ role: 'user', content: text });
            history.push({ role: 'assistant', content: res.assistant_message });
            State.generalChatHistory = history;
            
            appendMessage('ai', res.assistant_message);
        } catch (err) {
            appendMessage('ai', 'Error: ' + err.message);
        } finally {
            El.toolIndicator.classList.add('hidden');
        }
        return;
    }

    El.chatInput.value = '';
    appendMessage('user', text);
    El.toolIndicator.classList.remove('hidden');

    try {
        const res = await API.sendMessage(State.activeProject.id, text, State.conversationId);
        State.conversationId = res.conversation_id;
        
        // Show tool badges
        if (res.tool_calls_made && res.tool_calls_made.length > 0) {
            res.tool_calls_made.forEach(tool => appendToolBadge(tool));
        }
        
        // Show any images generated by tools
        if (res.images && res.images.length > 0) {
            res.images.forEach(img => {
                if (img.url) appendImageMessage('ai', img.url);
            });
        }

        appendMessage('ai', res.assistant_message);
    } catch (err) {
        appendMessage('ai', 'Error: ' + err.message);
    } finally {
        El.toolIndicator.classList.add('hidden');
    }
}

/**
 * Inline Vision: Upload & Analyze
 */
function handleFileSelection(e) {
    const file = e.target.files[0];
    if (!file) return;

    State.selectedImageFile = file;

    const previewUrl = URL.createObjectURL(file);
    El.imagePreviewThumbnail.src = previewUrl;
    El.imagePreviewFilename.innerText = file.name;
    El.imagePreviewContainer.classList.remove('hidden');
    
    El.fileInput.value = ''; // Reset file input
}

function removeSelectedImage() {
    State.selectedImageFile = null;
    El.imagePreviewContainer.classList.add('hidden');
    El.imagePreviewThumbnail.src = '';
    El.imagePreviewFilename.innerText = '';
}

function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `${role}-bubble animate-pop`;
    
    // Simple markdown-ish bold/newline support
    const formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
    div.innerHTML = formatted;
    
    El.chatHistory.appendChild(div);
    scrollToBottom();
}

function appendImageMessage(role, url) {
    const container = document.createElement('div');
    container.className = `chat-image-bubble ${role} animate-pop`;
    
    const img = document.createElement('img');
    img.src = url;
    
    // Crucial: scroll again once the image actualy loads and pushes the height
    img.onload = () => scrollToBottom();
    
    container.appendChild(img);
    El.chatHistory.appendChild(container);
    scrollToBottom();
}

function scrollToBottom() {
    El.chatHistory.scrollTo({
        top: El.chatHistory.scrollHeight,
        behavior: 'smooth'
    });
}

function appendToolBadge(name) {
    const span = document.createElement('span');
    span.className = 'tool-badge';
    span.innerText = `AI Action: ${name}`;
    El.chatHistory.appendChild(span);
}

/**
 * Event Listeners
 */
function setupEventListeners() {
    El.btnSend.onclick = sendChat;
    El.chatInput.onkeydown = e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChat();
        }
    };
    
    El.btnUpload.onclick = () => El.fileInput.click();
    El.fileInput.onchange = handleFileSelection;
    El.btnRemoveImage.onclick = removeSelectedImage;
    
    El.btnNewProject.onclick = showNewProjectModal;
    El.btnEditDesc.onclick = editProjectDescription;
    El.btnDeleteProject.onclick = deleteProjectAction;
    El.btnOrganizeMemory.onclick = organizeMemoryAction;
    El.btnGeneralChat.onclick = switchToGeneralChat;
    El.modalContainer.onclick = e => {
        if (e.target === El.modalContainer) hideModal();
    };
}

/**
 * Switch back to General Chat session
 */
function switchToGeneralChat() {
    State.activeProject = null;
    State.conversationId = null;
    
    renderProjectList();
    El.projectHeader.classList.add('hidden');
    
    El.chatHistory.innerHTML = '';
    
    const history = State.generalChatHistory || [];
    if (history.length > 0) {
        history.forEach(msg => {
            if (msg.role === 'user') {
                appendMessage('user', msg.content);
            } else if (msg.role === 'assistant') {
                appendMessage('ai', msg.content);
            }
        });
    } else {
        appendMessage('ai', "Hello! How can I help you today ? Ask me anything or create a project to get started. I'm ready to help you with research, brain storming and project organization.");
    }
}

/**
 * Edit Project Description Action
 */
async function editProjectDescription() {
    if (!State.activeProject) return;
    const newDesc = prompt("Enter new project description:", State.activeProject.description || "");
    if (newDesc === null) return; // Cancelled
    
    try {
        const updated = await API.updateProject(State.activeProject.id, { description: newDesc.trim() });
        State.activeProject.description = updated.description;
        El.projectDesc.innerText = updated.description || 'No description provided.';
        
        // Update the description in sidebar list
        const pIdx = State.projects.findIndex(p => p.id === State.activeProject.id);
        if (pIdx !== -1) {
            State.projects[pIdx].description = updated.description;
            renderProjectList();
        }
    } catch (err) {
        alert("Failed to update description: " + err.message);
    }
}

/**
 * Delete Project Action
 */
async function deleteProjectAction() {
    if (!State.activeProject) return;
    
    const confirmDelete = confirm(`Are you absolutely sure you want to delete the project "${State.activeProject.name}"?\n\nThis will permanently delete the project and all its related records (conversation history, brief, images, agent runs, memories) from database. This action cannot be undone.`);
    if (!confirmDelete) return;

    try {
        await API.deleteProject(State.activeProject.id);
        
        // Remove from local projects list
        State.projects = State.projects.filter(p => p.id !== State.activeProject.id);
        State.activeProject = null;
        State.conversationId = null;
        
        // Update UI
        renderProjectList();
        El.projectHeader.classList.add('hidden');
        
        // Reset chat history to welcome message
        El.chatHistory.innerHTML = `
            <div class="ai-bubble">
                Hello! How can I help you today ? Ask me anything or create a project to get started. I'm ready to help you with research, brain storming and project organization.
            </div>
        `;
        
        alert("Project successfully deleted.");
    } catch (err) {
        alert("Failed to delete project: " + err.message);
    }
}

/**
 * Organize Project Memory Action
 */
async function organizeMemoryAction() {
    if (!State.activeProject) return;
    
    const originalText = El.btnOrganizeMemory.innerHTML;
    El.btnOrganizeMemory.disabled = true;
    El.btnOrganizeMemory.innerHTML = `<span>🧠</span> Triggering...`;
    
    try {
        // 1. Trigger the background agent
        const run = await API.triggerAgentRun(State.activeProject.id);
        const runId = run.id;
        
        // 2. Start polling status
        El.btnOrganizeMemory.innerHTML = `<span>🧠</span> Pending...`;
        
        const pollInterval = setInterval(async () => {
            try {
                const runStatus = await API.getAgentRun(State.activeProject.id, runId);
                const status = runStatus.status.toLowerCase();
                
                if (status === 'running') {
                    El.btnOrganizeMemory.innerHTML = `<span>🧠</span> Organizing...`;
                } else if (status === 'completed') {
                    clearInterval(pollInterval);
                    El.btnOrganizeMemory.disabled = false;
                    El.btnOrganizeMemory.innerHTML = originalText;
                    
                    // Show a message in the chat history explaining the success
                    appendMessage('ai', '🧠 **Memory Sync Completed:** I have successfully analyzed the project history and organized your planning criteria, entities, constraints, and approach into durable memory files!');
                } else if (status === 'failed') {
                    clearInterval(pollInterval);
                    El.btnOrganizeMemory.disabled = false;
                    El.btnOrganizeMemory.innerHTML = originalText;
                    alert("Memory organization agent failed: " + (runStatus.error || "Unknown error"));
                }
            } catch (pollErr) {
                console.error("Error polling agent run status:", pollErr);
            }
        }, 1500);
        
    } catch (err) {
        El.btnOrganizeMemory.disabled = false;
        El.btnOrganizeMemory.innerHTML = originalText;
        alert("Failed to start memory organization: " + err.message);
    }
}

/**
 * Project Creation Modal
 */
function showNewProjectModal() {
    El.modalContent.innerHTML = `
        <h3>New Project</h3>
        <div style="margin: 20px 0;">
            <div class="form-group" style="margin-bottom: 15px;">
                <label style="display:block; margin-bottom:5px; font-size:12px; color:var(--text-muted);">Name</label>
                <input type="text" id="new-p-name" placeholder="Project name..." style="width:100%; padding:10px; border-radius:8px; border:1px solid var(--panel-border); background:rgba(0,0,0,0.2); color:white;">
            </div>
            <div class="form-group">
                <label style="display:block; margin-bottom:5px; font-size:12px; color:var(--text-muted);">Description</label>
                <input type="text" id="new-p-desc" placeholder="What is this about?" style="width:100%; padding:10px; border-radius:8px; border:1px solid var(--panel-border); background:rgba(0,0,0,0.2); color:white;">
            </div>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button class="btn" style="background:rgba(255,255,255,0.1); color:white;" onclick="hideModal()">Cancel</button>
            <button class="btn btn-primary" onclick="createNewProject()">Create Project</button>
        </div>
    `;
    El.modalContainer.classList.remove('hidden');
}

function hideModal() { El.modalContainer.classList.add('hidden'); }

async function createNewProject() {
    const name = document.getElementById('new-p-name').value;
    const description = document.getElementById('new-p-desc').value;
    if (!name) return;

    try {
        const p = await API.createProject({ name, description });
        hideModal();
        await loadProjects();
        selectProject(p.id);
    } catch (err) {
        alert(err.message);
    }
}

// Start
init();
