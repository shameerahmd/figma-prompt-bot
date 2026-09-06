/**
 * Figma AI Prompt Generator - Node.js Zero-Dependency Server.
 * Native HTTP server with static file serving and NVIDIA NIM proxy.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8080;
const PUBLIC_DIR = path.join(__dirname, 'public');
const NVIDIA_API_KEY = process.env.NVIDIA_API_KEY || '';

const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const SYSTEM_PROMPT = `You are a Figma AI UI/UX Prompt Compressor.
Convert raw user UI ideas into dense, declarative prompts using bracket syntax [Category: Component(Specs)].
Rules:
1. Output ONLY the bracketed prompt block. No intro or pleasantries.
2. Structure: [Frame], [Layout], [Header], [Content/Sections], [Controls/Actions], [Footer], [Tokens].
3. Use strict UI/UX terms (Auto-layout, BentoGrid, SegmentedControl, MetricCard, DataList).`;

function estimateTokens(text) {
  if (!text) return 0;
  const words = text.trim().split(/\s+/).length;
  return Math.max(1, Math.floor(words * 1.3));
}

const server = http.createServer(async (req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsedUrl.pathname;

  if (pathname === '/api/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'healthy',
      runtime: 'Node.js',
      version: '1.0.0',
      nvidia_key_configured: Boolean(NVIDIA_API_KEY)
    }));
    return;
  }

  if (pathname === '/api/optimize' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', async () => {
      try {
        const data = JSON.parse(body || '{}');
        const prompt = (data.prompt || '').trim();
        const apiKey = data.api_key || NVIDIA_API_KEY;
        const model = data.model || 'meta/llama-3.1-8b-instruct';
        const device = data.device || 'desktop';
        const style = data.style || 'saas_modern';

        if (!prompt) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: false, error: 'Prompt is required' }));
          return;
        }

        const startTime = Date.now();
        let optimizedText = '';
        let mode = 'mock';
        let inputTokens = estimateTokens(prompt);
        let outputTokens = 0;

        if (apiKey && apiKey.startsWith('nvapi-')) {
          try {
            const resp = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                model,
                messages: [
                  { role: 'system', content: SYSTEM_PROMPT },
                  { role: 'user', content: `Target: ${device}, Style: ${style}\n\nUser Request: ${prompt}` }
                ],
                temperature: 0.1,
                max_tokens: 300
              })
            });

            if (resp.ok) {
              const resJson = await resp.json();
              optimizedText = resJson.choices[0].message.content.trim();
              mode = 'nvidia_nim_live';
              inputTokens = resJson.usage?.prompt_tokens || inputTokens;
              outputTokens = resJson.usage?.completion_tokens || estimateTokens(optimizedText);
            }
          } catch (e) {
            console.warn('Live API request failed, falling back to heuristic:', e.message);
          }
        }

        if (!optimizedText) {
          // Heuristic fallback
          optimizedText = `[Frame: ${device === 'mobile' ? 'Mobile iOS 375px' : 'Desktop 1440px'}, ${style === 'minimal_dark' ? 'Dark OLED #09090B' : 'Clean Slate #0F172A'}]
[Layout: Vertical Auto-layout, 24px Gap, 32px Padding]
[Header: NavigationBar(BrandLogo, SearchInput, UserMenu)]
[Hero: SectionOverview(Heading("${prompt.slice(0, 40)}..."), MetricCardsRow(3))]
[Content: BentoGrid(2x2: DataVisualization, ActivityStream, TaskList, SettingsCard)]
[Footer: ActionToolbar(PrimaryBtn("Save Changes"), SecondaryBtn("Export"))]
[Tokens: Radius=8px, Inter Sans, 8px Grid Base]`;
          outputTokens = estimateTokens(optimizedText);
        }

        const latency = Date.now() - startTime;
        const equivalentVerbose = Math.floor(outputTokens * 2.8);
        const tokensSaved = Math.max(0, equivalentVerbose - outputTokens);
        const reductionPercentage = Math.round((tokensSaved / Math.max(1, equivalentVerbose)) * 100);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: true,
          raw_input: prompt,
          optimized_prompt: optimizedText,
          figma_formatted: optimizedText.replace(/\n+/g, ' '),
          metrics: {
            raw_input_tokens: inputTokens,
            optimized_prompt_tokens: outputTokens,
            equivalent_verbose_tokens: equivalentVerbose,
            tokens_saved: tokensSaved,
            reduction_percentage: reductionPercentage,
            latency_ms: latency,
            estimated_savings_100_runs_usd: (tokensSaved * 100 / 1000 * 0.003).toFixed(4)
          },
          mode,
          model_used: model,
          device,
          style
        }));
      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: err.message }));
      }
    });
    return;
  }

  // Serve static files
  let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        // Fallback to index.html for SPA
        fs.readFile(path.join(PUBLIC_DIR, 'index.html'), (err2, indexContent) => {
          if (err2) {
            res.writeHead(404);
            res.end('File not found');
          } else {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(indexContent);
          }
        });
      } else {
        res.writeHead(500);
        res.end(`Server Error: ${err.code}`);
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

server.listen(PORT, () => {
  console.log(`Figma AI Prompt Generator (Node.js) listening on http://localhost:${PORT}`);
});
