// Honest placeholder for a script a later ticket builds. Test-like stubs fail so they never pass silently.
const [name, ticket] = process.argv.slice(2);
console.log(`npm run ${name}: not implemented ${ticket ? `until ${ticket}` : "yet"}`);
process.exit(name.startsWith("gen:") ? 0 : 1);
