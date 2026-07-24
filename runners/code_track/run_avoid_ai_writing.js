#!/usr/bin/env node
// Run the avoid-ai-writing detector engine over text files and emit
// normalized findings JSON. Zero dependencies, Node >= 18.
//
// Usage: node run_avoid_ai_writing.js <out.json> <file-or-dir> [...]
// Env:   REGISTERBENCH_TOOLS_DIR overrides the default ../../../tools location.
//        REGISTERBENCH_CONTEXT_MODE sets analyzeText contextMode (default general).

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const TOOLS_DIR = process.env.REGISTERBENCH_TOOLS_DIR ||
  path.resolve(__dirname, '..', '..', '..', 'tools');
const TOOL_DIR = path.join(TOOLS_DIR, 'avoid-ai-writing');
const AIDetector = require(path.join(TOOL_DIR, 'detector', 'patterns.js'));

const [outFile, ...inputs] = process.argv.slice(2);
if (!outFile || inputs.length === 0) {
  console.error('usage: node run_avoid_ai_writing.js <out.json> <file-or-dir> [...]');
  process.exit(1);
}

function collect(p) {
  const st = fs.statSync(p);
  if (st.isDirectory()) {
    return fs.readdirSync(p)
      .filter((f) => f.endsWith('.txt') || f.endsWith('.md'))
      .map((f) => path.join(p, f));
  }
  return [p];
}

const contextMode = process.env.REGISTERBENCH_CONTEXT_MODE || 'general';
const sha = execSync('git rev-parse HEAD', { cwd: TOOL_DIR }).toString().trim();

const result = {
  tool: 'avoid-ai-writing-detector',
  sha,
  run_date: new Date().toISOString().slice(0, 10),
  options: { contextMode },
  files: {},
};

for (const input of inputs) {
  for (const file of collect(input)) {
    const text = fs.readFileSync(file, 'utf8');
    const r = AIDetector.analyzeText(text, { contextMode });
    result.files[path.basename(file)] = {
      words: text.split(/\s+/).filter(Boolean).length,
      score: r.score,
      label: r.label,
      findings: (r.issues || []).map((i) => ({
        rule: i.type,
        text: i.text,
        index: Number.isInteger(i.index) ? i.index : null,
        severity: i.severity || null,
      })),
    };
  }
}

fs.writeFileSync(outFile, JSON.stringify(result, null, 2));
console.log(`avoid-ai-writing-detector: ${Object.keys(result.files).length} files -> ${outFile}`);
