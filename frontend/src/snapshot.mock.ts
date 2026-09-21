import type { Snapshot, SnapshotClient } from './snapshot'

// Hand-calculated two-room fixture; used only by tests and explicit previews.
export const mockSnapshot: Snapshot = {
  id: '00000000-0000-0000-0000-000000000010', edition_id: '00000000-0000-0000-0000-000000000001',
  as_of: '2026-01-05T10:00:00+05:30', window_start: '2026-01-05T09:00:00+05:30', window_end: '2026-01-05T17:00:00+05:30',
  schema_version: 1, synthetic_data_only: true, input_hash: 'a'.repeat(64), edition_hash: 'b'.repeat(64), created_at: '2026-09-21T00:00:00Z',
  metrics: { scheduled_classes: 2, scheduled_occupied_rooms: 1, available_rooms: 1,
    booked_room_minutes: 90, available_room_minutes: 960, room_utilization: 0.09375,
    attendance_present: 1, attendance_recorded: 1, attendance_expected: 2, attendance_rate: 1,
    faculty_workload: [{ faculty_id: 'faculty-a', scheduled_minutes: 120 }] },
  coverage: { attendance_ratio: 0.5, missing_attendance: 1, sessions_in_window: 2 },
  anomalies: ['room_overlap', 'faculty_overlap', 'section_overlap'].map(rule => ({ rule, resource_id: rule.split('_')[0] + '-a', session_ids: ['session-a', 'session-b'], starts_at: '2026-01-05T09:30:00+05:30', ends_at: '2026-01-05T10:00:00+05:30' })),
}
export const mockSnapshotClient: SnapshotClient = {
  create: async body => ({ ...mockSnapshot, ...body }),
  get: async () => mockSnapshot,
}
