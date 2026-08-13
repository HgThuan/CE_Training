export function websocketUrl(path: string, token: string): string {
  const configured = import.meta.env.VITE_WS_BASE_URL?.replace(/\/$/, '')
  const base =
    configured ??
    `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${base}${normalizedPath}?token=${encodeURIComponent(token)}`
}
