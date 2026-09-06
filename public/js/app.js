/**
 * Figma AI Prompt Optimizer - Main Client Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // State
  const state = {
    selectedDevice: 'desktop',
    selectedStyle: 'saas_modern',
    selectedModel: 'meta/llama-3.1-8b-instruct',
    apiKey: localStorage.getItem('figma_opt_api_key') || '',
    history: JSON.parse(localStorage.getItem('figma_opt_history') || '[]'),
    currentResult: null,
    isGenerating: false
  };

  // DOM Elements
  const userPromptInput = document.getElementById('userPromptInput');
  const inputTokenCount = document.getElementById('inputTokenCount');
  const optimizeBtn = document.getElementById('optimizeBtn');
  const modelSelect = document.getElementById('modelSelect');
  const connectionStatus = document.getElementById('connectionStatus');

  // Metrics
  const metricReduction = document.getElementById('metricReduction');
  const metricSaved = document.getElementById('metricSaved');
  const metricOutputTokens = document.getElementById('metricOutputTokens');
  const metricLatency = document.getElementById('metricLatency');

  // Outputs
  const promptOutputBlock = document.getElementById('promptOutputBlock');
  const copyPromptBtn = document.getElementById('copyPromptBtn');
  const exportJsonBtn = document.getElementById('exportJsonBtn');

  // Diff
  const diffVerboseTokens = document.getElementById('diffVerboseTokens');
  const diffOptimizedTokens = document.getElementById('diffOptimizedTokens');
  const diffVerboseText = document.getElementById('diffVerboseText');
  const diffOptimizedText = document.getElementById('diffOptimizedText');

  // History
  const historyList = document.getElementById('historyList');
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');

  // Settings Modal
  const settingsModal = document.getElementById('settingsModal');
  const openSettingsBtn = document.getElementById('openSettingsBtn');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  const apiKeyInput = document.getElementById('apiKeyInput');
  const toggleKeyVisibility = document.getElementById('toggleKeyVisibility');

  // How-To Modal
  const howToModal = document.getElementById('howToModal');
  const howToFigmaBtn = document.getElementById('howToFigmaBtn');
  const closeHowToBtn = document.getElementById('closeHowToBtn');
  const closeHowToFooterBtn = document.getElementById('closeHowToFooterBtn');

  // Theme Toggle
  const themeToggleBtn = document.getElementById('themeToggleBtn');

  // Tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  // Device & Style Grid Buttons
  const deviceCards = document.querySelectorAll('.device-card');
  const styleCards = document.querySelectorAll('.style-card');
  const chipButtons = document.querySelectorAll('.chip');

  // Initialize UI
  initTheme();
  updateStatusBadge();
  renderHistory();
  if (state.apiKey) {
    apiKeyInput.value = state.apiKey;
  }

  // Event Listeners: Input Token Counter
  userPromptInput.addEventListener('input', () => {
    const text = userPromptInput.value.trim();
    const count = estimateWordsToTokens(text);
    inputTokenCount.textContent = `${count} tokens`;
  });

  // Event Listeners: Quick Prompt Chips
  chipButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.getAttribute('data-prompt');
      userPromptInput.value = prompt;
      userPromptInput.dispatchEvent(new Event('input'));
      userPromptInput.focus();
    });
  });

  // Event Listeners: Device Selector
  deviceCards.forEach(card => {
    card.addEventListener('click', () => {
      deviceCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.selectedDevice = card.getAttribute('data-device');
    });
  });

  // Event Listeners: Style Selector
  styleCards.forEach(card => {
    card.addEventListener('click', () => {
      styleCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.selectedStyle = card.getAttribute('data-style');
    });
  });

  // Event Listeners: Model Selector
  modelSelect.addEventListener('change', (e) => {
    state.selectedModel = e.target.value;
  });

  // Event Listeners: Tabs
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetTab = btn.getAttribute('data-tab');
      document.getElementById(targetTab).classList.add('active');
    });
  });

  // Event Listeners: Theme Toggle
  themeToggleBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('figma_opt_theme', nextTheme);
  });

  function initTheme() {
    const saved = localStorage.getItem('figma_opt_theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
  }

  // Event Listeners: Settings Modal
  openSettingsBtn.addEventListener('click', () => {
    apiKeyInput.value = state.apiKey;
    settingsModal.classList.add('open');
  });

  const closeSettings = () => settingsModal.classList.remove('open');
  closeSettingsBtn.addEventListener('click', closeSettings);
  cancelSettingsBtn.addEventListener('click', closeSettings);

  saveSettingsBtn.addEventListener('click', () => {
    const key = apiKeyInput.value.trim();
    state.apiKey = key;
    localStorage.setItem('figma_opt_api_key', key);
    updateStatusBadge();
    closeSettings();
    showToast(key ? 'NVIDIA API Key saved' : 'Key cleared (using Demo Mode)');
  });

  toggleKeyVisibility.addEventListener('click', () => {
    if (apiKeyInput.type === 'password') {
      apiKeyInput.type = 'text';
      toggleKeyVisibility.textContent = 'Hide';
    } else {
      apiKeyInput.type = 'password';
      toggleKeyVisibility.textContent = 'Show';
    }
  });

  // Event Listeners: How To Use Modal
  if (howToFigmaBtn) {
    howToFigmaBtn.addEventListener('click', () => {
      howToModal.classList.add('open');
    });
  }
  const closeHowTo = () => howToModal.classList.remove('open');
  if (closeHowToBtn) closeHowToBtn.addEventListener('click', closeHowTo);
  if (closeHowToFooterBtn) closeHowToFooterBtn.addEventListener('click', closeHowTo);

  // Close modals on outside click
  window.addEventListener('click', (e) => {
    if (e.target === settingsModal) closeSettings();
    if (e.target === howToModal) closeHowTo();
  });

  // Keyboard shortcut: Ctrl + Enter
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleOptimize();
    }
  });

  optimizeBtn.addEventListener('click', handleOptimize);

  // Copy Prompt Handler
  copyPromptBtn.addEventListener('click', () => {
    if (!state.currentResult) return;
    const textToCopy = state.currentResult.figma_formatted || state.currentResult.optimized_prompt;
    navigator.clipboard.writeText(textToCopy).then(() => {
      showToast('Copied Figma prompt to clipboard!');
    });
  });

  // Export JSON Handler
  exportJsonBtn.addEventListener('click', () => {
    if (!state.currentResult) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(state.currentResult, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", `figma-prompt-${Date.now()}.json`);
    dlAnchorElem.click();
    showToast('JSON exported successfully');
  });

  // Clear History
  clearHistoryBtn.addEventListener('click', () => {
    state.history = [];
    localStorage.removeItem('figma_opt_history');
    renderHistory();
    showToast('History cleared');
  });

  // Main Optimization Request (Server-Sent-Event streaming)
  async function handleOptimize() {
    const prompt = userPromptInput.value.trim();
    if (!prompt) {
      showToast('Please enter your UI requirements first');
      userPromptInput.focus();
      return;
    }

    if (state.isGenerating) return;

    // Gather selected components
    const checkedComponents = Array.from(
      document.querySelectorAll('#componentTags input:checked')
    ).map(cb => cb.value);

    setLoading(true);

    const payload = {
      prompt: prompt,
      device: state.selectedDevice,
      style: state.selectedStyle,
      model: state.selectedModel,
      components: checkedComponents,
      api_key: state.apiKey || undefined
    };

    const streamBox = document.createElement('div');
    streamBox.className = 'streaming-live';
    streamBox.innerHTML = `<span class="streaming-part"></span><span class="streaming-caret"></span>`;
    promptOutputBlock.innerHTML = '';
    promptOutputBlock.appendChild(streamBox);
    const streamingPart = streamBox.querySelector('.streaming-part');

    let partial = '';

    try {
      const res = await fetch('/api/optimize/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      // Non-stream response (e.g. 400/500 JSON error)
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Request failed (${res.status})`);
      }

      // Fallback: plain JSON (network/proxy that drops SSE)
      if (!res.body) {
        const data = await res.json();
        if (data.success === false) throw new Error(data.error || 'Optimization request failed');
        state.currentResult = data;
        displayResults(data);
        saveToHistory(prompt, data);
        showToast('Prompt optimized successfully!');
        return;
      }

      // Consume SSE stream
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const updateLive = () => {
        streamingPart.textContent = partial || 'Generating…';
        streamBox.scrollIntoView({ block: 'nearest' });
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        // SSE frames are separated by blank lines
        let idx;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          for (const evt of parseEventFrame(frame)) {
            if (evt.type === 'token') {
              partial += evt.text;
              updateLive();
            } else if (evt.type === 'result') {
              state.currentResult = evt;
              displayResults(evt);
              saveToHistory(prompt, evt);
            } else if (evt.type === 'error') {
              throw new Error(evt.error || 'Optimization failed');
            }
          }
        }
      }

      if (state.currentResult) {
        showToast('Prompt optimized successfully!');
      } else {
        throw new Error('No result returned from server');
      }

    } catch (err) {
      console.error(err);
      showToast(`Error: ${err.message}`);
    } finally {
      setLoading(false);
      streamBox.remove();
      if (!state.currentResult) {
        showToast('No output generated. Check your API key or try again.');
      }
    }
  }

  // Split an SSE frame into parsed events (handles multi-data frames)
  function parseEventFrame(frame) {
    const events = [];
    let dataLines = [];
    const lines = frame.split('\n');
    for (const line of lines) {
      if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      } else if (line.startsWith('event:')) {
        // Ignore event type; we dispatch by payload.
      } else if (line === '') {
        // blank; flush collected data
        if (dataLines.length) {
          try { events.push(JSON.parse(dataLines.join('\n'))); } catch (e) {}
          dataLines = [];
        }
      }
    }
    if (dataLines.length) {
      try { events.push(JSON.parse(dataLines.join('\n'))); } catch (e) {}
    }
    return events;
  }

  function displayResults(data) {
    const metrics = data.metrics || {};

    // Update Metrics
    metricReduction.textContent = `${metrics.reduction_percentage || 0}%`;
    metricSaved.textContent = metrics.tokens_saved || 0;
    metricOutputTokens.textContent = metrics.optimized_prompt_tokens || 0;
    metricLatency.textContent = metrics.latency_ms || 0;

    // Highlight & display prompt
    promptOutputBlock.innerHTML = syntaxHighlight(data.optimized_prompt);

    // Update Visualizer Frame
    renderWireframe(data.optimized_prompt, 'mockupBody');

    // Update Token Diff Tab
    diffVerboseTokens.textContent = metrics.equivalent_verbose_tokens || 0;
    diffOptimizedTokens.textContent = metrics.optimized_prompt_tokens || 0;

    diffVerboseText.innerHTML = `<p><strong>Raw Intent:</strong> "${escapeHtml(data.raw_input)}"</p>
<p style="margin-top:8px; opacity:0.8;">Equivalent standard conversational LLM prompt requires <em>${metrics.equivalent_verbose_tokens || 0} tokens</em> with verbose prose and lacks strict layout coordinates.</p>`;

    diffOptimizedText.innerHTML = `<pre style="font-family:var(--font-mono); font-size:0.75rem;">${escapeHtml(data.optimized_prompt)}</pre>`;
  }

  function syntaxHighlight(text) {
    if (!text) return '';
    const safe = escapeHtml(text);
    // Highlight [Category: ...] tags
    return safe.replace(/\[([A-Za-z0-9_\/\s\-]+):/g, '<span class="syntax-tag">[$1:</span>')
               .replace(/\]/g, '<span class="syntax-tag">]</span>')
               .replace(/\((.*?)\)/g, '(<span class="syntax-val">$1</span>)');
  }

  function setLoading(isLoading) {
    state.isGenerating = isLoading;
    if (isLoading) {
      optimizeBtn.disabled = true;
      optimizeBtn.innerHTML = `<i data-lucide="loader" class="spin"></i> <span>Optimizing Prompt...</span>`;
    } else {
      optimizeBtn.disabled = false;
      optimizeBtn.innerHTML = `<i data-lucide="zap"></i> <span>Generate Optimized Figma Prompt</span> <kbd class="kbd-shortcut">Ctrl + ↵</kbd>`;
    }
    if (window.lucide) lucide.createIcons();
  }

  function updateStatusBadge() {
    if (state.apiKey && state.apiKey.startsWith('nvapi-')) {
      connectionStatus.className = 'status-chip chip-online';
      connectionStatus.innerHTML = '<span class="status-dot"></span><span class="status-label">NVIDIA NIM Live</span>';
    } else {
      connectionStatus.className = 'status-chip chip-offline';
      connectionStatus.innerHTML = '<span class="status-dot"></span><span class="status-label">Demo Mode (Heuristic)</span>';
    }
  }

  function saveToHistory(rawInput, result) {
    const item = {
      id: Date.now(),
      raw: rawInput,
      optimized: result.optimized_prompt,
      device: result.device,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    state.history.unshift(item);
    if (state.history.length > 20) state.history.pop();
    localStorage.setItem('figma_opt_history', JSON.stringify(state.history));
    renderHistory();
  }

  function renderHistory() {
    if (state.history.length === 0) {
      historyList.innerHTML = '<p class="history-empty">No previous prompts saved in this session.</p>';
      return;
    }

    let html = '';
    state.history.slice(0, 5).forEach(item => {
      html += `
        <div class="history-item" data-id="${item.id}">
          <span class="history-text">${escapeHtml(item.raw)}</span>
          <span class="history-meta">${item.device || 'desktop'} • ${item.timestamp}</span>
        </div>
      `;
    });

    historyList.innerHTML = html;

    // Click item to load
    document.querySelectorAll('.history-item').forEach(el => {
      el.addEventListener('click', () => {
        const id = parseInt(el.getAttribute('data-id'), 10);
        const found = state.history.find(h => h.id === id);
        if (found) {
          userPromptInput.value = found.raw;
          userPromptInput.dispatchEvent(new Event('input'));
          promptOutputBlock.innerHTML = syntaxHighlight(found.optimized);
          renderWireframe(found.optimized, 'mockupBody');
          showToast('Loaded prompt from history');
        }
      });
    });
  }

  function showToast(message) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<i data-lucide="check" style="width:14px;height:14px;"></i> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);
    if (window.lucide) lucide.createIcons();

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }

  function estimateWordsToTokens(str) {
    if (!str) return 0;
    const words = str.trim().split(/\s+/).length;
    return Math.max(1, Math.floor(words * 1.3));
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
