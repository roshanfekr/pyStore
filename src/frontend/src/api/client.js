// Thin fetch wrapper around the Django REST API.
//
// Auth uses DRF TokenAuthentication (token kept in localStorage) and the SPA
// shares the Django session cookie with the server-rendered pages, so the guest
// cart and login state are consistent across both. CSRF tokens are forwarded
// from the cookie for session-authenticated requests.

const TOKEN_KEY = 'pystore.token'
const API_BASE = '/api/v1'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

function getCookie(name) {
  const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)')
  return match ? decodeURIComponent(match[2]) : ''
}

export function getCsrfToken() {
  return getCookie('csrftoken')
}

export async function api(path, { method = 'GET', body, headers = {} } = {}) {
  const finalHeaders = {
    Accept: 'application/json',
    ...headers,
  }
  if (body !== undefined) {
    finalHeaders['Content-Type'] = 'application/json'
  }
  const token = getToken()
  if (token) {
    finalHeaders.Authorization = `Token ${token}`
  }
  const csrf = getCookie('csrftoken')
  if (csrf) {
    finalHeaders['X-CSRFToken'] = csrf
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: finalHeaders,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 204) {
    return null
  }

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = data?.error
    const message =
      (data && (data.detail || data.message)) ||
      (error && typeof error === 'object' ? error.message : error) ||
      `Request failed (${response.status})`
    const failure = new Error(message)
    failure.status = response.status
    failure.data = data
    throw failure
  }
  return data
}
