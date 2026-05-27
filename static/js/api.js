/**
 * API Wrapper for AI Project Assistant Backend
 */
const API = {
    baseUrl: '', // Same origin
    activeRequests: 0,
    onStatusChange: null, // Callback for UI state tracking

    async request(endpoint, options = {}) {
        this.activeRequests++;
        if (this.onStatusChange) {
            this.onStatusChange(true);
        }

        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        try {
            const response = await fetch(url, { ...options, headers });
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            if (response.status === 204) return null;
            return await response.json();
        } catch (err) {
            console.error(`API Error [${endpoint}]:`, err);
            throw err;
        } finally {
            this.activeRequests--;
            if (this.activeRequests <= 0) {
                this.activeRequests = 0;
                if (this.onStatusChange) {
                    this.onStatusChange(false);
                }
            }
        }
    },

    // Projects
    getProjects() { return this.request('/projects'); },
    createProject(data) { return this.request('/projects', { method: 'POST', body: JSON.stringify(data) }); },
    getProject(id) { return this.request(`/projects/${id}`); },
    updateProject(id, data) {
        return this.request(`/projects/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },
    deleteProject(id) {
        return this.request(`/projects/${id}`, {
            method: 'DELETE'
        });
    },

    // Briefs
    getBrief(projectId) { return this.request(`/projects/${projectId}/brief`); },
    updateBrief(projectId, data) { return this.request(`/projects/${projectId}/brief`, { method: 'POST', body: JSON.stringify(data) }); },

    // Conversations & Messages
    getConversations(projectId) {
        return this.request(`/projects/${projectId}/conversations`);
    },
    getMessages(projectId, conversationId) {
        return this.request(`/projects/${projectId}/conversations/${conversationId}/messages`);
    },

    // Chat
    sendMessage(projectId, userMessage, conversationId = null) {
        return this.request(`/projects/${projectId}/chat`, {
            method: 'POST',
            body: JSON.stringify({ user_message: userMessage, conversation_id: conversationId })
        });
    },
    generalChat(userMessage, history = []) {
        return this.request('/general-chat', {
            method: 'POST',
            body: JSON.stringify({ user_message: userMessage, history })
        });
    },

    // Images
    getImages(projectId) { return this.request(`/projects/${projectId}/images`); },
    generateImage(projectId, prompt) {
        return this.request(`/projects/${projectId}/images`, {
            method: 'POST',
            body: JSON.stringify({ prompt })
        });
    },
    analyzeImage(projectId, imageId, prompt = null) {
        return this.request(`/projects/${projectId}/images/${imageId}/analyze`, {
            method: 'POST',
            body: JSON.stringify({ prompt })
        });
    },
    generalAnalyzeImage(file, prompt = null) {
        this.activeRequests++;
        if (this.onStatusChange) this.onStatusChange(true);

        const formData = new FormData();
        formData.append('file', file);
        if (prompt) formData.append('prompt', prompt);

        return fetch(`${this.baseUrl}/general-chat/analyze-image`, {
            method: 'POST',
            body: formData
        }).then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        }).finally(() => {
            this.activeRequests--;
            if (this.activeRequests <= 0) {
                this.activeRequests = 0;
                if (this.onStatusChange) this.onStatusChange(false);
            }
        });
    },

    // Agent Runs
    triggerAgentRun(projectId) {
        return this.request(`/projects/${projectId}/agent-runs`, { method: 'POST' });
    },
    getAgentRun(projectId, runId) {
        return this.request(`/projects/${projectId}/agent-runs/${runId}`);
    },
    listAgentRuns(projectId) {
        return this.request(`/projects/${projectId}/agent-runs`);
    }
};
