/**
 * Figma Prompt Visualizer - Parses bracketed prompt tokens into a simulated wireframe mockup.
 */

function parsePromptToWireframe(promptText) {
  if (!promptText || typeof promptText !== 'string') return [];

  const lines = promptText.split(/\n+/);
  const blocks = [];

  const bracketRegex = /\[(.*?):\s*(.*?)\]/g;

  lines.forEach(line => {
    let match;
    while ((match = bracketRegex.exec(line)) !== null) {
      const category = match[1].trim();
      const content = match[2].trim();
      blocks.push({ category, content });
    }
  });

  return blocks;
}

function renderWireframe(promptText, targetElementId = 'mockupBody') {
  const container = document.getElementById(targetElementId);
  if (!container) return;

  const blocks = parsePromptToWireframe(promptText);

  if (blocks.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <i data-lucide="monitor" class="icon-large"></i>
        <p>No valid structural blocks found in prompt.</p>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  let html = '';

  blocks.forEach(block => {
    const cat = block.category.toLowerCase();

    // Parse sub-items inside parentheses e.g. Input(Email), Button("Sign In")
    const subItems = [];
    const itemRegex = /([A-Za-z0-9_\-]+)\s*\((.*?)\)/g;
    let itemMatch;
    let foundItems = false;

    while ((itemMatch = itemRegex.exec(block.content)) !== null) {
      foundItems = true;
      subItems.push({
        type: itemMatch[1],
        args: itemMatch[2]
      });
    }

    html += `<div class="wf-block" data-section="${block.category}">`;
    html += `<div class="wf-header">${escapeHtml(block.category)}</div>`;

    if (foundItems && subItems.length > 0) {
      html += `<div class="wf-items">`;
      subItems.forEach(item => {
        html += `<span class="wf-pill"><strong>${escapeHtml(item.type)}</strong>: ${escapeHtml(item.args)}</span>`;
      });
      html += `</div>`;
    } else {
      html += `<div class="wf-items"><span class="wf-pill">${escapeHtml(block.content)}</span></div>`;
    }

    html += `</div>`;
  });

  container.innerHTML = html;
  if (window.lucide) lucide.createIcons();
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
