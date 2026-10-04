import dns from "node:dns/promises";
import { pathToFileURL } from "node:url";

const USAGE = "Usage: check-mail-auth <domain> [--selector <dkim-selector>]\n  Checks SPF, DKIM (default selector: resend), DMARC and MX. Exits 1 if any is missing.";

async function txt(resolver, name) {
  try {
    return (await resolver.resolveTxt(name)).map((chunks) => chunks.join(""));
  } catch {
    return [];
  }
}

export async function run(argv, resolver = dns, log = console.log) {
  const args = [...argv];
  let selector = "resend";
  const i = args.indexOf("--selector");
  if (i !== -1) selector = args.splice(i, 2)[1];
  const domain = args[0];
  if (!domain || !selector || domain.startsWith("-")) {
    log(USAGE);
    return 2;
  }
  let mx = [];
  try {
    mx = await resolver.resolveMx(domain);
  } catch {}
  const spf = (await txt(resolver, domain)).filter((r) => r.startsWith("v=spf1"));
  const checks = [
    ["SPF", spf.length === 1],
    ["DKIM", (await txt(resolver, `${selector}._domainkey.${domain}`)).some((r) => /(^|;)\s*p=[A-Za-z0-9+/=]+/.test(r))],
    ["DMARC", (await txt(resolver, `_dmarc.${domain}`)).some((r) => r.startsWith("v=DMARC1"))],
    ["MX", mx.length > 0],
  ];
  for (const [name, ok] of checks) log(`${ok ? "ok     " : "MISSING"} ${name}`);
  return checks.every(([, ok]) => ok) ? 0 : 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await run(process.argv.slice(2));
}
