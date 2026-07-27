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
      // Documentation living alongside fixtures is not itself a fixture.
      .filter((f) => !/^(README|PROVENANCE|NOTES)\.md$/i.test(f))
      .map((f) => path.join(p, f));
  }
  return [p];
}

const contextMode = process.env.REGISTERBENCH_CONTEXT_MODE || 'general';
const sha = execSync('git rev-parse HEAD', { cwd: TOOL_DIR }).toString().trim();

// The engine refuses input over MAX_WORDS (10,000 as of 27156c7) and returns
// label 'Text too long' with zero issues. Four MD&A documents in the
// finance-audit corpus exceed that, so a naive single call records zeros while
// their words stay in the flags/1k denominator, understating the tool roughly
// 2.5x and making the comparison against unslop (which reads them) unfair.
// Long inputs are therefore split at paragraph boundaries and analyzed in
// pieces. Document-level rules report a rate rather than a located span, so
// they would otherwise fire once per chunk; they are deduplicated by
// rule+text across chunks of the same document.
const DETECTOR_MAX_WORDS = 10000;
const CHUNK_WORDS = 9000;  // headroom under the cap
const DOC_LEVEL = new Set([
  'em-dash', 'uniformity', 'punct-distribution', 'fnword-trigram-entropy',
  'cross-para-burstiness', 'low-ttr', 'smart-punct-signature', 'formatting',
  'normalization-flag', 'title-case-header',
]);

function wordCount(s) {
  return s.split(/\s+/).filter(Boolean).length;
}

// Split on blank lines, packing paragraphs until the chunk approaches the cap.
function chunkText(text) {
  if (wordCount(text) <= DETECTOR_MAX_WORDS) return [{ text, offset: 0 }];
  const paras = text.split(/\n\s*\n/);
  const chunks = [];
  let buf = [];
  let bufWords = 0;
  let offset = 0;
  let consumed = 0;
  for (const p of paras) {
    const pw = wordCount(p);
    if (bufWords + pw > CHUNK_WORDS && buf.length) {
      const joined = buf.join('\n\n');
      chunks.push({ text: joined, offset });
      consumed += joined.length + 2;
      offset = consumed;
      buf = [];
      bufWords = 0;
    }
    buf.push(p);
    bufWords += pw;
  }
  if (buf.length) chunks.push({ text: buf.join('\n\n'), offset });
  return chunks;
}

const result = {
  tool: 'avoid-ai-writing-detector',
  sha,
  run_date: new Date().toISOString().slice(0, 10),
  options: {
    contextMode,
    chunking: `paragraph-packed at <=${CHUNK_WORDS} words for inputs over the engine's ${DETECTOR_MAX_WORDS}-word cap; document-level rules deduplicated across chunks`,
  },
  files: {},
};

for (const input of inputs) {
  for (const file of collect(input)) {
    const text = fs.readFileSync(file, 'utf8');
    const chunks = chunkText(text);
    const findings = [];
    const seenDocLevel = new Set();
    const labels = [];
    let scoreSum = 0;
    let scoreWeight = 0;

    for (const chunk of chunks) {
      const r = AIDetector.analyzeText(chunk.text, { contextMode });
      labels.push(r.label);
      const cw = wordCount(chunk.text);
      if (typeof r.score === 'number') {
        scoreSum += r.score * cw;
        scoreWeight += cw;
      }
      for (const i of (r.issues || [])) {
        if (DOC_LEVEL.has(i.type)) {
          const key = `${i.type}:${String(i.text).toLowerCase()}`;
          if (seenDocLevel.has(key)) continue;
          seenDocLevel.add(key);
        }
        findings.push({
          rule: i.type,
          text: i.text,
          // Offsets are chunk-relative; shift back to document coordinates.
          index: Number.isInteger(i.index) ? i.index + chunk.offset : null,
          severity: i.severity || null,
        });
      }
    }

    if (labels.some((l) => l === 'Text too long')) {
      console.error(`ERROR ${path.basename(file)}: a chunk still exceeded the engine cap. Lower CHUNK_WORDS.`);
      process.exit(1);
    }

    result.files[path.basename(file)] = {
      words: wordCount(text),
      chunks: chunks.length,
      score: scoreWeight ? Math.round(scoreSum / scoreWeight) : 0,
      label: chunks.length === 1 ? labels[0] : `${labels.length} chunks, word-weighted score`,
      findings,
    };
  }
}

fs.writeFileSync(outFile, JSON.stringify(result, null, 2));
console.log(`avoid-ai-writing-detector: ${Object.keys(result.files).length} files -> ${outFile}`);
