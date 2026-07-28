/**
 * VITAL HUB - AI ASSISTANT WIDGET
 * Floating "AI Hub" chat button used on every page.
 * Talks to the real backend LLM endpoint (/api/ai/consultation-chat/) —
 * no more hardcoded keyword matching.
 */

let _aiHistory = [];
let _aiLoading = false;

function toggleAIHub() {
    const hub = document.getElementById('ai-hub');
    if (!hub) return;
    hub.classList.toggle('translate-y-[120%]');
    hub.classList.toggle('opacity-0');
    hub.classList.toggle('translate-y-0');
    hub.classList.toggle('opacity-100');
}

function askQuick(text) {
    const input = document.getElementById('ai-input');
    if (!input) return;
    input.value = text;
    processAIQuery();
}

async function processAIQuery() {
    const input = document.getElementById('ai-input');
    if (!input || _aiLoading) return;
    const query = input.value.trim();
    if (!query) return;

    appendMessage('user', query);
    input.value = '';
    _aiLoading = true;
    const loadingId = appendLoading();

    try {
        const res = await fetch('/api/ai/consultation-chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: query, history: _aiHistory })
        });
        const data = await res.json();
        removeMessage(loadingId);

        if (!res.ok || !data.success) {
            appendMessage('bot', data.message || "I'm having trouble reaching the AI engine right now.");
            return;
        }

        appendMessage('bot', data.response);
        _aiHistory.push({ role: 'user', content: query });
        _aiHistory.push({ role: 'ai', content: data.response });
    } catch (err) {
        removeMessage(loadingId);
        appendMessage('bot', '⚠️ Neural Core disconnected. Please try again.');
    } finally {
        _aiLoading = false;
    }
}

function appendLoading() {
    const content = document.getElementById('ai-content');
    if (!content) return null;
    const id = 'ai-loading-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'flex gap-3 mb-4';
    div.innerHTML = `
        <div class="w-8 h-8 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
            <i data-lucide="sparkles" size="14"></i>
        </div>
        <div class="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-1">
            <span class="w-2 h-2 bg-slate-300 rounded-full animate-bounce"></span>
            <span class="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style="animation-delay:0.1s"></span>
            <span class="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style="animation-delay:0.2s"></span>
        </div>`;
    content.appendChild(div);
    content.scrollTop = content.scrollHeight;
    if (window.lucide) lucide.createIcons();
    return id;
}

function removeMessage(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
}

function appendMessage(role, text) {
    const content = document.getElementById('ai-content');
    if (!content) return;
    const msg = document.createElement('div');
    msg.className = `flex gap-3 mb-4 ${role === 'user' ? 'flex-row-reverse' : ''}`;
    const isUser = role === 'user';
    const avatarCls = `w-8 h-8 ${isUser ? 'bg-slate-900' : 'bg-blue-100'} text-${isUser ? 'white' : 'blue-600'} rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm`;
    msg.innerHTML = `
        <div class="${avatarCls}">
            <i data-lucide="${isUser ? 'user' : 'sparkles'}" size="14"></i>
        </div>
        <div class="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm max-w-[80%]">
            <p class="text-xs font-bold text-slate-700 leading-relaxed whitespace-pre-wrap"></p>
        </div>
    `;
    msg.querySelector('p').textContent = text;
    content.appendChild(msg);
    content.scrollTop = content.scrollHeight;
    if (window.lucide) lucide.createIcons();
}
