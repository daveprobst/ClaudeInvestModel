import crypto from 'node:crypto'

const b64 = (b) => Buffer.from(b).toString('base64url')
const sign = (data, secret) => crypto.createHmac('sha256', secret).update(data).digest('base64url')

/** Minimal HS256 JWT (no dependency). exp is seconds since epoch. */
export function signToken(claims, secret, ttlSeconds, now = Date.now()) {
  const head = b64(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = b64(JSON.stringify({ ...claims, iat: Math.floor(now / 1000), exp: Math.floor(now / 1000) + ttlSeconds }))
  return `${head}.${body}.${sign(`${head}.${body}`, secret)}`
}

export function verifyToken(token, secret, now = Date.now()) {
  if (typeof token !== 'string') return null
  const parts = token.split('.')
  if (parts.length !== 3) return null
  const [head, body, sig] = parts
  const expect = sign(`${head}.${body}`, secret)
  const a = Buffer.from(sig), b = Buffer.from(expect)
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null
  try {
    if (JSON.parse(Buffer.from(head, 'base64url')).alg !== 'HS256') return null
    const claims = JSON.parse(Buffer.from(body, 'base64url'))
    if (typeof claims.exp !== 'number' || claims.exp * 1000 < now) return null
    return claims
  } catch { return null }
}
