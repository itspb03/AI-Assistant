/**
 * API Wrapper for AI Project Assistant Backend
 */
const API = {
    baseUrl: '', // Same origin

    async request(endpoint, options = {}) {
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
        }
    },

    // Projects
    getProjects() { return this.request('/projects'); },
    createProject(data) { return this.request('/projects', { method: 'POST', body: JSON.stringify(data) }); },
    getProject(id) { return this.request(`/projects/${id}`); },

    // Briefs
    getBrief(projectId) { return this.request(`/projects/${projectId}/brief`); },
    updateBrief(projectId, data) { return this.request(`/projects/${projectId}/brief`, { method: 'POST', body: JSON.stringify(data) }); },

    // Chat
    sendMessage(projectId, userMessage, conversationId = null) {
        return this.request(`/projects/${projectId}/chat`, {
            method: 'POST',
            body: JSON.stringify({ user_message: userMessage, conversation_id: conversationId })
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
    analyzeImage(projectId, imageId) {
        return this.request(`/projects/${projectId}/images/${imageId}/analyze`, { method: 'POST' });
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
