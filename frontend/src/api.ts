export type Actor = { id: string; username: string; role: 'viewer' | 'planner' }
export type Edition = {
  id: string; seed: number; generator_version: string; logical_content_hash: string;
  config: { start_date: string; weeks: number; students_per_section: number };
  frozen_at: string;
}
export type Room = { id: string; code: string; capacity: number; kind: 'classroom' | 'lab'; lab_type: string | null }
export type Page<T> = { items: T[]; total: number; limit: number; offset: number }

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const csrf = document.cookie.split('; ').find(value => value.startsWith('twin_csrf='))?.split('=')[1]
  const response = await fetch(`/api/v1${path}`, {
    method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'The server could not complete this request.' }))
    throw new ApiError(error.message, response.status)
  }
  return response.status === 204 ? undefined as T : response.json()
}
