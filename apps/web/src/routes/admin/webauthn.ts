// Thin wrappers over navigator.credentials for the admin 2FA (08 section 2.2). The server speaks base64url.
const b64uToBuf = (s: string): ArrayBuffer => {
  const pad = "=".repeat((4 - (s.length % 4)) % 4)
  const bin = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"))
  return Uint8Array.from(bin, (c) => c.charCodeAt(0)).buffer
}
export const bufToB64u = (b: ArrayBuffer): string =>
  btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "")

type Json = Record<string, unknown>
const descriptor = (d: Json) => ({ ...d, id: b64uToBuf(String(d.id)) }) as PublicKeyCredentialDescriptor

export const passkeysSupported = () => typeof PublicKeyCredential !== "undefined" && !!navigator.credentials

/** The person closed the browser prompt, or the authenticator refused. */
export class PasskeyCancelled extends Error {}

/** Ask the authenticator to sign the server's challenge. */
export async function getAssertion(opts: Json) {
  const publicKey = {
    ...opts,
    challenge: b64uToBuf(String(opts.challenge)),
    allowCredentials: ((opts.allowCredentials as Json[] | undefined) ?? []).map(descriptor),
  } as PublicKeyCredentialRequestOptions
  const cred = (await navigator.credentials.get({ publicKey }).catch(() => null)) as
    | (PublicKeyCredential & { response: AuthenticatorAssertionResponse })
    | null
  if (!cred) throw new PasskeyCancelled()
  return {
    credential_id: bufToB64u(cred.rawId),
    client_data_json: bufToB64u(cred.response.clientDataJSON),
    authenticator_data: bufToB64u(cred.response.authenticatorData),
    signature: bufToB64u(cred.response.signature),
  }
}

/** Create a passkey from the server's registration options. */
export async function createPasskey(opts: Json) {
  const user = opts.user as Json
  const publicKey = {
    ...opts,
    challenge: b64uToBuf(String(opts.challenge)),
    user: { ...user, id: b64uToBuf(String(user.id)) },
    excludeCredentials: ((opts.excludeCredentials as Json[] | undefined) ?? []).map(descriptor),
  } as unknown as PublicKeyCredentialCreationOptions
  const cred = (await navigator.credentials.create({ publicKey }).catch(() => null)) as
    | (PublicKeyCredential & { response: AuthenticatorAttestationResponse })
    | null
  if (!cred) throw new PasskeyCancelled()
  return {
    client_data_json: bufToB64u(cred.response.clientDataJSON),
    attestation_object: bufToB64u(cred.response.attestationObject),
  }
}
