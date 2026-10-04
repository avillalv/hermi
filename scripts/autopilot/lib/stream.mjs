// Pure helpers: parse the `claude -p --output-format stream-json --verbose --forward-subagent-text`
// stream. Shapes were observed on Claude Code 2.1.288:
//   system/init            {session_id, model, permissionMode, apiKeySource, agents, tools, ...}
//   assistant              {message:{model, content:[text|thinking|tool_use]}, parent_tool_use_id, subagent_type?}
//   user                   {message:{content:[tool_result]}, parent_tool_use_id, tool_use_result?}
//   rate_limit_event       {rate_limit_info:{status, resetsAt, rateLimitType, utilization, overageStatus,
//                           isUsingOverage, ...}}
//   result                 {subtype, is_error, result, permission_denials, total_cost_usd, num_turns,
//                           api_error_status, terminal_reason, session_id}
// A subagent's final report arrives as an assistant message (parent_tool_use_id set, message.model of the
// subagent) holding a `SubagentHandback` tool_use whose input.message is the report text; plain text blocks
// are handled too. Nothing here touches the disk or the clock except through the injected `now`.

import { assessRateLimit } from './limits.mjs';

export const OPUS_PREFIX = 'claude-opus-5-5';
export const SONNET_PREFIX = 'claude-sonnet-5-5';

/** Agents whose Opus verdict the driver accepts. A verdict from any other agent is ignored. */
export const APPROVER_AGENTS = new Set(['opus-reviewer', 'opus-judge']);

export function parseLine(line) {
  const t = String(line).trim();
  if (!t.startsWith('{')) return null;
  try {
    const o = JSON.parse(t);
    return o && typeof o === 'object' ? o : null;
  } catch {
    return null;
  }
}

const VERDICT_RE = /^[\s*_`>-]*VERDICT:\s*(APPROVE|REQUEST_CHANGES)\s+([A-Za-z0-9][A-Za-z0-9._-]*)[\s*_`]*$/;

/** Every `VERDICT: APPROVE <id>` / `VERDICT: REQUEST_CHANGES <id>` line of a text, in order. */
export function extractVerdicts(text) {
  const out = [];
  for (const raw of String(text ?? '').split(/\r?\n/)) {
    const m = VERDICT_RE.exec(raw);
    if (m) out.push({ verdict: m[1], stepId: m[2].replace(/[.,;:]+$/, '') });
  }
  return out;
}

const flat = (s, n) => {
  const t = String(s ?? '').replace(/\s+/g, ' ').trim();
  return t.length > n ? `${t.slice(0, n)}...` : t;
};

const baseName = (p) => String(p ?? '').split(/[\\/]/).filter(Boolean).slice(-2).join('/');

/** One-line hint for a tool call: the part of the input a human wants to see. */
export function toolHint(name, input = {}) {
  switch (name) {
    case 'Bash':
    case 'PowerShell':
      return flat(input.command, 100);
    case 'Read':
    case 'Write':
    case 'Edit':
    case 'NotebookEdit':
      return baseName(input.file_path ?? input.notebook_path);
    case 'Grep':
    case 'Glob':
      return flat(input.pattern, 80);
    case 'WebFetch':
      return flat(input.url, 100);
    case 'WebSearch':
      return flat(input.query, 100);
    case 'Agent':
    case 'Task':
      return `${input.subagent_type ?? 'general-purpose'}: ${flat(input.description, 80)}`;
    case 'Skill':
      return flat(input.skill, 60);
    default: {
      const first = Object.values(input).find((v) => typeof v === 'string');
      return flat(first, 80);
    }
  }
}

const shortModel = (m) => String(m ?? '?').replace(/^claude-/, '');

function resultText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) return content.map((b) => (typeof b === 'string' ? b : b?.text ?? '')).join('\n');
  return '';
}

export class StreamTracker {
  constructor({ now = () => new Date() } = {}) {
    this.now = now;
    this.init = null;
    this.sessionId = null;
    this.rateLimit = null; // latest raw rate_limit_info
    this.rejected = new Map(); // limit type -> assessment, cleared when that type is allowed again
    this.overageUsed = false; // paid extra usage was drawn on
    this.overageEnabled = false; // extra usage is switched on for the account
    this.result = null;
    this.approvals = new Map(); // verdict id -> {model, at, agent, source, toolUseId}
    this.tainted = new Set(); // Agent calls whose models or hand-back were not clean: no verdict of theirs counts
    this.changesRequested = new Set();
    this.subagents = new Map(); // subagent type -> Set(model)
    this.toolUses = new Map(); // tool_use_id -> {name, input} (main thread)
    this.errorResults = []; // [{id, tool, input, text}] tool results with is_error
    this.hookResponses = []; // [{event, name, exitCode, outcome, stderr}]
    this.lastText = '';
    this.lines = 0;
  }

  /** Feed one raw stdout line. Returns {lines: string[] for the console, signals: object[]}. */
  feed(line) {
    const out = { lines: [], signals: [] };
    const o = parseLine(line);
    if (!o) return out;
    this.lines++;
    if (o.session_id && !this.sessionId) this.sessionId = o.session_id;
    switch (o.type) {
      case 'system':
        if (o.subtype === 'init') this.#onInit(o, out);
        else if (o.subtype === 'hook_response') this.#onHookResponse(o);
        break;
      case 'assistant':
        this.#onAssistant(o, out);
        break;
      case 'user':
        this.#onUser(o, out);
        break;
      case 'rate_limit_event':
        this.#onRateLimit(o, out);
        break;
      case 'result':
        this.#onResult(o, out);
        break;
      default:
        break;
    }
    return out;
  }

  #onInit(o, out) {
    this.sessionId = o.session_id ?? this.sessionId;
    this.init = {
      sessionId: o.session_id ?? null,
      model: o.model ?? null,
      permissionMode: o.permissionMode ?? null,
      apiKeySource: o.apiKeySource ?? null,
      agents: Array.isArray(o.agents) ? o.agents : [],
      cwd: o.cwd ?? null,
    };
    out.lines.push(`init: model=${this.init.model} permissionMode=${this.init.permissionMode} session=${String(this.init.sessionId).slice(0, 8)}`);
    out.signals.push({ kind: 'init', init: this.init });
  }

  // Only present with --include-hook-events (the canary asks for it).
  #onHookResponse(o) {
    this.hookResponses.push({
      event: o.hook_event ?? null,
      name: o.hook_name ?? null,
      exitCode: o.exit_code ?? null,
      outcome: o.outcome ?? null,
      stderr: String(o.stderr ?? '').slice(0, 300),
    });
    if (this.hookResponses.length > 200) this.hookResponses.shift();
  }

  #onAssistant(o, out) {
    const model = o.message?.model ?? null;
    // The agent type comes with the forwarded message, or from the Agent call that spawned it.
    const sub = o.parent_tool_use_id ? { id: o.parent_tool_use_id, agent: o.subagent_type ?? this.toolUses.get(o.parent_tool_use_id)?.input?.subagent_type ?? null, model } : null;
    if (sub) this.#noteSubagent(sub.agent, model);
    const prefix = sub ? `[${sub.agent ?? 'subagent'} ${shortModel(model)}] ` : '';
    for (const block of o.message?.content ?? []) {
      let text = null;
      if (block.type === 'text') text = block.text;
      else if (block.type === 'tool_use' && block.name === 'SubagentHandback') text = block.input?.message;
      else if (block.type === 'tool_use' && !sub) {
        this.#rememberToolUse(block);
        out.lines.push(`tool ${block.name}: ${toolHint(block.name, block.input)}`);
        continue;
      } else if (block.type === 'tool_use') {
        this.#rememberToolUse(block);
        continue;
      }
      if (!text) continue;
      if (!sub) this.lastText = text;
      out.lines.push(`${prefix}${block.type === 'text' ? 'say' : 'report'}: ${flat(text, 300)}`);
      if (sub) this.#considerVerdicts(text, { model, agent: sub.agent, source: 'assistant', toolUseId: sub.id }, out);
    }
  }

  #onUser(o, out) {
    // Harness result of a finished subagent call: authoritative model and agent type.
    const tur = o.tool_use_result;
    if (tur && typeof tur === 'object' && tur.agentType && tur.resolvedModel) {
      this.#noteSubagent(tur.agentType, tur.resolvedModel);
      const toolUseId = o.message?.content?.find?.((b) => b?.type === 'tool_result')?.tool_use_id ?? null;
      // modelsUsed (only present when the agent switched models mid-run) must be all Opus, and a hand-back
      // must have been delivered cleanly ('send'); otherwise nothing this agent said is a verdict, and a
      // verdict already taken from its forwarded text is revoked.
      const mixed = Array.isArray(tur.modelsUsed) && tur.modelsUsed.some((m) => !String(m).startsWith(OPUS_PREFIX));
      const unclean = tur.handback !== undefined && tur.handback !== 'send';
      if (mixed || unclean) {
        if (toolUseId) {
          this.tainted.add(toolUseId);
          for (const [id, a] of this.approvals) if (a.toolUseId === toolUseId) this.approvals.delete(id);
        }
      } else {
        const text = tur.handbackReport?.text ?? resultText(tur.content);
        this.#considerVerdicts(text, { model: tur.resolvedModel, agent: tur.agentType, source: 'result', toolUseId }, out);
      }
    }
    if (o.parent_tool_use_id) return; // subagent internals: no console noise
    const content = o.message?.content;
    if (!Array.isArray(content)) return;
    for (const block of content) {
      if (block.type !== 'tool_result' || !block.is_error) continue;
      const known = this.toolUses.get(block.tool_use_id) ?? {};
      const text = resultText(block.content);
      this.errorResults.push({ id: block.tool_use_id, tool: known.name ?? '?', input: known.input ?? null, text: text.slice(0, 400) });
      if (this.errorResults.length > 100) this.errorResults.shift();
      out.lines.push(`tool error (${known.name ?? '?'}): ${flat(text, 160)}`);
    }
  }

  #onRateLimit(o, out) {
    const info = o.rate_limit_info;
    const a = assessRateLimit(info);
    if (!a) return;
    this.rateLimit = info;
    const key = a.type ?? 'unknown';
    if (a.rejected) this.rejected.set(key, a);
    else this.rejected.delete(key);
    if (a.usingOverage) this.overageUsed = true;
    if (a.overageEnabled) this.overageEnabled = true;
    if (a.rejected || a.warning || a.usingOverage) {
      out.lines.push(`limit: ${a.type ?? '?'} status=${a.status}${a.utilization != null ? ` utilization=${a.utilization}` : ''}${a.usingOverage ? ' USING EXTRA USAGE' : ''}`);
    }
    out.signals.push({ kind: 'rate_limit', assessment: a, info });
  }

  #onResult(o, out) {
    this.result = o;
    const n = Array.isArray(o.permission_denials) ? o.permission_denials.length : 0;
    out.lines.push(`result: ${o.subtype ?? '?'}${o.is_error ? ' (error)' : ''} turns=${o.num_turns ?? '?'} cost=$${Number(o.total_cost_usd ?? 0).toFixed(2)} denials=${n}${o.is_error && o.result ? ` | ${flat(o.result, 200)}` : ''}`);
    out.signals.push({ kind: 'result', result: o });
  }

  #rememberToolUse(block) {
    if (!block.id) return;
    this.toolUses.set(block.id, { name: block.name, input: block.input });
    if (this.toolUses.size > 500) this.toolUses.delete(this.toolUses.keys().next().value);
  }

  #noteSubagent(agent, model) {
    if (!agent || !model) return;
    if (!this.subagents.has(agent)) this.subagents.set(agent, new Set());
    this.subagents.get(agent).add(model);
  }

  /**
   * Approvals come only from a subagent whose model starts with the Opus 5.5 id and whose agent type is
   * in APPROVER_AGENTS (a verdict from the main thread, from Sonnet, from an unnamed agent or from any
   * other agent is ignored), and only from an Agent call that was not tainted by a mid-run model switch
   * or an unclean hand-back. The last verdict per id wins (REQUEST_CHANGES revokes an earlier APPROVE).
   */
  #considerVerdicts(text, { model, agent, source, toolUseId = null }, out) {
    if (!text || !String(model ?? '').startsWith(OPUS_PREFIX)) return;
    if (!agent || !APPROVER_AGENTS.has(agent)) return;
    if (toolUseId && this.tainted.has(toolUseId)) return;
    // the verdict is the last line of the message: an earlier VERDICT line followed by more text does not count
    for (const { verdict, stepId } of extractVerdicts(String(text).trimEnd().split(/\r?\n/).at(-1))) {
      if (verdict === 'APPROVE') {
        this.approvals.set(stepId, { model, at: this.now().toISOString(), agent, source, toolUseId });
        this.changesRequested.delete(stepId);
      } else {
        this.approvals.delete(stepId);
        this.changesRequested.add(stepId);
      }
      out.signals.push({ kind: 'verdict', verdict, stepId, model, agent });
    }
  }
}
