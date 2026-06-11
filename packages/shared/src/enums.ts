/** 与 OpenAPI / docs/incident_state_machine.md 对齐 */

export const Severity = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
} as const
export type Severity = (typeof Severity)[keyof typeof Severity]

export const IncidentStatus = {
  OPEN: 'open',
  ACKNOWLEDGED: 'acknowledged',
  INVESTIGATING: 'investigating',
  MITIGATED: 'mitigated',
  RESOLVED: 'resolved',
  CLOSED: 'closed',
} as const
export type IncidentStatus = (typeof IncidentStatus)[keyof typeof IncidentStatus]

export const IncidentAction = {
  ACKNOWLEDGE: 'acknowledge',
  START_INVESTIGATION: 'start_investigation',
  MITIGATE: 'mitigate',
  RESOLVE: 'resolve',
  CLOSE: 'close',
  REOPEN_INVESTIGATION: 'reopen_investigation',
  ASSIGN: 'assign',
  UPDATE_SEVERITY: 'update_severity',
  ADD_NOTE: 'add_note',
} as const
export type IncidentAction = (typeof IncidentAction)[keyof typeof IncidentAction]

export const AlertStatus = {
  FIRING: 'firing',
  RESOLVED: 'resolved',
} as const
export type AlertStatus = (typeof AlertStatus)[keyof typeof AlertStatus]

export const UserRole = {
  ADMIN: 'admin',
  OPERATOR: 'operator',
} as const
export type UserRole = (typeof UserRole)[keyof typeof UserRole]

export const INCIDENT_STATUS_LABELS: Record<IncidentStatus, string> = {
  open: '待处理',
  acknowledged: '已确认',
  investigating: '调查中',
  mitigated: '已缓解',
  resolved: '已解决',
  closed: '已关闭',
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  critical: '严重',
  high: '高',
  medium: '中',
  low: '低',
}

export const STATUS_ACTIONS: Partial<Record<IncidentStatus, { action: IncidentAction; label: string }[]>> = {
  open: [
    { action: IncidentAction.ACKNOWLEDGE, label: '确认' },
    { action: IncidentAction.START_INVESTIGATION, label: '开始调查' },
  ],
  acknowledged: [{ action: IncidentAction.START_INVESTIGATION, label: '开始调查' }],
  investigating: [
    { action: IncidentAction.MITIGATE, label: '标记缓解' },
    { action: IncidentAction.RESOLVE, label: '解决' },
  ],
  mitigated: [{ action: IncidentAction.RESOLVE, label: '解决' }],
  resolved: [
    { action: IncidentAction.CLOSE, label: '关闭' },
    { action: IncidentAction.REOPEN_INVESTIGATION, label: '重新调查' },
  ],
}
