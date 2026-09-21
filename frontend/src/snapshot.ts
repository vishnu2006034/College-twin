import { api } from './api'

export type SnapshotRequest = { edition_id: string; as_of: string; window_start: string; window_end: string }
export type Snapshot = SnapshotRequest & {
  id: string; schema_version: 1; synthetic_data_only: true; input_hash: string; edition_hash: string; created_at: string
  metrics: {
    scheduled_classes: number; scheduled_occupied_rooms: number; available_rooms: number
    booked_room_minutes: number; available_room_minutes: number; room_utilization: number | null
    attendance_present: number; attendance_recorded: number; attendance_expected: number; attendance_rate: number | null
    faculty_workload: { faculty_id: string; scheduled_minutes: number }[]
  }
  coverage: { attendance_ratio: number | null; missing_attendance: number; sessions_in_window: number }
  anomalies: { rule: string; resource_id: string; session_ids: string[]; starts_at: string; ends_at: string }[]
}
export interface SnapshotClient {
  create(body: SnapshotRequest, key: string): Promise<Snapshot>
  get(id: string): Promise<Snapshot>
}
export const snapshotClient: SnapshotClient = {
  create: (body, key) => api('/snapshots', body, { 'Idempotency-Key': key }),
  get: id => api(`/snapshots/${encodeURIComponent(id)}`),
}
