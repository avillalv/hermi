/** Which host serves the console (08 section 2.1). Exactly `admin.hermi.world` and `admin.staging.hermi.world`. */
export const isAdminHost = (hostname: string = globalThis.location?.hostname ?? "") => /^admin\.(staging\.)?hermi\.world$/.test(hostname)

const LOCAL_HOSTS = ["localhost", "127.0.0.1"]

/** The console answers on the admin host, and on localhost for local and CI runs. The customer host never serves it. */
export const adminAvailable = (hostname: string = globalThis.location?.hostname ?? "") => isAdminHost(hostname) || LOCAL_HOSTS.includes(hostname)
