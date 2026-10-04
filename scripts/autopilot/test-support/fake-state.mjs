// Shared state of the simulation used by driver.test.mjs: a directory (FAKE_STATE_DIR) holding the
// fake GitHub state, the scenario the test wants, and a log of every fake claude call.
// The bare origin repository lives next to it (FAKE_STATE_DIR/../origin.git).

import fs from 'node:fs';
import path from 'node:path';

export const DIR = process.env.FAKE_STATE_DIR;
const file = (name) => path.join(DIR, name);

export const readJson = (name, fallback) => {
  try {
    return JSON.parse(fs.readFileSync(file(name), 'utf8'));
  } catch {
    return fallback;
  }
};
export const writeJson = (name, obj) => fs.writeFileSync(file(name), JSON.stringify(obj, null, 2));

export const ORIGIN = () => path.join(DIR, '..', 'origin.git');

const emptyGh = () => ({ nextPr: 1, prs: {}, ciHeads: {}, mainCi: null, calls: [] });
export const ghState = {
  load: () => readJson('gh.json', emptyGh()),
  save: (s) => writeJson('gh.json', s),
};

/** What the test wants the fake session to do: {steps, rules: [{match, do, ...}], ci, mainCi, ...}. */
export const scenario = () => readJson('scenario.json', {});

export const appendCall = (call) => fs.appendFileSync(file('calls.jsonl'), `${JSON.stringify(call)}\n`);

export function createPr(state, { headRefName, title, isDraft }) {
  const number = state.nextPr++;
  state.prs[number] = { number, headRefName, title, isDraft, state: 'OPEN', labels: [] };
  return number;
}
