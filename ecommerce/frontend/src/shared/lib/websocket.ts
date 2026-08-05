export function websocketUrl(path: string, token: string): string {
  const configured = import.meta.env.VITE_WS_BASE_URL?.replace(/\/$/, '')
  const base =
    configured ??
    `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
  let normalizedPath = path.startsWith('/') ? path : `/${path}`

  // The configured base may already include the backend's /ws prefix.
  // Callers use full backend route paths, so remove the duplicated prefix.
  if (base.endsWith('/ws') && normalizedPath.startsWith('/ws/')) {
    normalizedPath = normalizedPath.slice(3)
  }

  return `${base}${normalizedPath}?token=${encodeURIComponent(token)}`
}
