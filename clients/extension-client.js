/** Resolve a pointer without rendering a browser page. */
export async function resolveHumain(endpoint, request, fetchImpl = fetch) {
  const response = await fetchImpl(`${endpoint.replace(/\/$/, '')}/v1/resolve`, {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify(request),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || payload.error || 'HumAIn resolver error');
  return payload;
}

export function canRenderTrustedProjection(response) {
  return response?.resolution_state === 'trusted_projection' || response?.resolution_state === 'mutual_trust';
}
