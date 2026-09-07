import React from 'react';
import { Calendar } from 'lucide-react';
import { PlanTask } from '../types';
import { theme, cardStyle, badgeStyle, getDeptColor, getPriorityBadge } from '../theme';

export function WeeklyView({ plans }: { plans: PlanTask[] }) {
  const days = [
    'Day 1 - Monday', 'Day 2 - Tuesday', 'Day 3 - Wednesday',
    'Day 4 - Thursday', 'Day 5 - Friday', 'Day 6 - Saturday', 'Day 7 - Sunday'
  ];

  return (
    <div style={{ display: 'grid', gap: 20 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: theme.text }}>
          Weekly 7-Day Corridor Possession Schedule
        </h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, color: theme.textMuted }}>
          Corridor-by-corridor breakdown of approved line blocks, power isolations, and joint multi-department slots.
        </p>
      </div>

      <div style={{ display: 'grid', gap: 14 }}>
        {days.map((day, dIdx) => {
          const dayTasks = plans.slice(dIdx * 8, (dIdx + 1) * 8);
          return (
            <div key={dIdx} style={cardStyle}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Calendar size={18} color={theme.cyan} />
                  <strong style={{ fontSize: 15, color: theme.text }}>{day}</strong>
                  <span style={badgeStyle('rgba(56, 189, 248, 0.2)', theme.cyan)}>
                    {dayTasks.length} Scheduled Possessions
                  </span>
                </div>
                <span style={{ fontSize: 12, color: theme.green, fontWeight: 600 }}>
                  Corridor Availability: 94.2%
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
                {dayTasks.map((t, i) => {
                  const deptColor = getDeptColor(t.department);
                  return (
                    <div key={i} style={{
                      padding: 12,
                      background: theme.bg,
                      border: `1px solid ${theme.border}`,
                      borderRadius: 8
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <span style={badgeStyle(deptColor.bg, deptColor.text)}>
                          {t.department}
                        </span>
                        <span style={{ fontSize: 11, color: theme.cyan, fontWeight: 700 }}>
                          {t.duration || t.required_duration_min} min
                        </span>
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: theme.text }}>
                        {t.section_id}
                      </div>
                      <div style={{ fontSize: 11, color: theme.textDim, margin: '4px 0' }}>
                        {t.task_type} · Slot: 01:00 - 04:30 Midnight
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8, paddingTop: 6, borderTop: `1px solid ${theme.border}` }}>
                        <span style={getPriorityBadge(t.priority)}>{t.priority}</span>
                        <span style={{ fontSize: 10, color: t.approval_status === 'APPROVED' ? theme.green : theme.amber }}>
                          {t.approval_status === 'APPROVED' ? '✓ Authorized' : '⏳ Pending'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
