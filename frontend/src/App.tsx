import React, { useEffect, useState, useCallback } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import axios from 'axios';
import {
  Home, Map, Calendar, Wrench, BarChart2, Settings, LogOut,
  Bell, ChevronDown, Clock, RefreshCw, AlertTriangle, ShieldCheck,
  Play, FileCheck, Layers, AlertOctagon, Database, Cpu
} from 'lucide-react';

import {
  Station, Section, PlanTask, MaintenanceTaskItem, AssetItem,
  BlockWindowItem, ConflictItem, DataIntegration, GoodsForecastItem,
  RouteAnalysisResult, ModelHealth
} from './types';
import { API_URL, theme, cardStyle, badgeStyle, buttonPrimary, authHeaders, apiError } from './theme';

import { Login } from './components/Login';
import { MapView } from './components/MapView';
import { RouteAnalyzer } from './components/RouteAnalyzer';
import { OverviewView } from './components/OverviewView';
import { PlanningView } from './components/PlanningView';
import { TasksView } from './components/TasksView';
import { WeeklyView } from './components/WeeklyView';
import { MonthlyView } from './components/MonthlyView';
import { ConflictsView } from './components/ConflictsView';
import { ApprovalView } from './components/ApprovalView';
import { IntegrationsView } from './components/IntegrationsView';
import { SettingsView } from './components/SettingsView';

function ControlRoom({ token, onLogout }: { token: string; onLogout: () => void }) {
  // Navigation State
  const [activeTab, setActiveTab] = useState<
    'dashboard' | 'map' | 'planning' | 'tasks' | 'reports' | 'settings' | 'approval'
  >('dashboard');

  // Reports sub-tab
  const [reportsSubTab, setReportsSubTab] = useState<'conflicts' | 'weekly' | 'monthly' | 'integrations' | 'approval'>('conflicts');

  // Core Data Stores
  const [stations, setStations] = useState<Station[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [plans, setPlans] = useState<PlanTask[]>([]);
  const [tasks, setTasks] = useState<MaintenanceTaskItem[]>([]);
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [blocks, setBlocks] = useState<BlockWindowItem[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [integrations, setIntegrations] = useState<DataIntegration[]>([]);
  const [goodsForecasts, setGoodsForecasts] = useState<GoodsForecastItem[]>([]);
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);

  // States & Filters
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [optStatus, setOptStatus] = useState<string>('OPTIMAL');
  const [optObjective, setOptObjective] = useState<number>(18715.0);
  const [selectedHorizon, setSelectedHorizon] = useState<'weekly' | 'monthly'>('weekly');
  const [objectiveProfile, setObjectiveProfile] = useState<string>('safety_first');
  const [lastOptimizedAt, setLastOptimizedAt] = useState<string>('Just now');
  const [errorBanner, setErrorBanner] = useState<string>('');

  // Map & Route Analyzer Selection
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [routeFrom, setRouteFrom] = useState<string>('NDLS');
  const [routeTo, setRouteTo] = useState<string>('MTJ');
  const [routeAnalysis, setRouteAnalysis] = useState<RouteAnalysisResult | null>(null);

  // Approval Workspace Action State
  const [approverName, setApproverName] = useState<string>('Debosmita');
  const [approverRole, setApproverRole] = useState<string>('Chief Controller');
  const [approvalRemarks, setApprovalRemarks] = useState<string>('Approved per Indian Railways Safety Regulations');
  const [approvingTaskId, setApprovingTaskId] = useState<string | null>(null);

  // Live Clock
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('en-IN', { hour12: false }) + ' IST');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // ------------------------------------------------------------------------
  // DATA FETCHING
  // ------------------------------------------------------------------------
  const fetchAllData = useCallback(async () => {
    setLoading(true);
    setErrorBanner('');
    try {
      const headers = authHeaders(token);
      const [stRes, secRes, plRes, tskRes, astRes, blkRes, confRes, intRes, gfRes, mhRes] = await Promise.allSettled([
        axios.get<Station[]>(`${API_URL}/stations`, { headers }),
        axios.get<Section[]>(`${API_URL}/sections`, { headers }),
        axios.get<PlanTask[]>(`${API_URL}/plans/optimized`, { headers }),
        axios.get<MaintenanceTaskItem[]>(`${API_URL}/maintenance/tasks`, { headers }),
        axios.get<AssetItem[]>(`${API_URL}/assets`, { headers }),
        axios.get<BlockWindowItem[]>(`${API_URL}/blocks/availability`, { headers }),
        axios.get<ConflictItem[]>(`${API_URL}/plans/conflicts`, { headers }),
        axios.get<{ integrations: DataIntegration[] }>(`${API_URL}/data-integrations/status`, { headers }),
        axios.get<GoodsForecastItem[]>(`${API_URL}/goods-forecast?limit=100`, { headers }),
        axios.get<ModelHealth>(`${API_URL}/models/health`, { headers })
      ]);

      if (stRes.status === 'fulfilled') {
        const list = Array.isArray(stRes.value.data) ? stRes.value.data : [];
        setStations(list);
        if (list.length > 0 && !selectedStation) {
          const ndls = list.find(s => s.code === 'NDLS') || list[0];
          setSelectedStation(ndls);
        }
      }

      if (secRes.status === 'fulfilled') setSections(Array.isArray(secRes.value.data) ? secRes.value.data : []);
      if (plRes.status === 'fulfilled') setPlans(Array.isArray(plRes.value.data) ? plRes.value.data : []);
      if (tskRes.status === 'fulfilled') setTasks(Array.isArray(tskRes.value.data) ? tskRes.value.data : []);
      if (astRes.status === 'fulfilled') setAssets(Array.isArray(astRes.value.data) ? astRes.value.data : []);
      if (blkRes.status === 'fulfilled') setBlocks(Array.isArray(blkRes.value.data) ? blkRes.value.data : []);
      if (confRes.status === 'fulfilled') setConflicts(Array.isArray(confRes.value.data) ? confRes.value.data : []);
      if (intRes.status === 'fulfilled' && intRes.value.data?.integrations) {
        setIntegrations(intRes.value.data.integrations);
      }
      if (gfRes.status === 'fulfilled') setGoodsForecasts(Array.isArray(gfRes.value.data) ? gfRes.value.data : []);
      if (mhRes.status === 'fulfilled') setModelHealth(mhRes.value.data);

    } catch (err) {
      setErrorBanner(apiError(err, 'Failed to synchronize with Central Operations server.'));
    } finally {
      setLoading(false);
    }
  }, [token, selectedStation]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // ------------------------------------------------------------------------
  // TRIGGER CP-SAT OPTIMIZER
  // ------------------------------------------------------------------------
  const handleRunOptimizer = async () => {
    setOptimizing(true);
    setErrorBanner('');
    try {
      const headers = authHeaders(token);
      const res = await axios.post<{
        run_id: string;
        solver_status: string;
        objective_value: number;
        plan: PlanTask[];
        horizon: string;
        solver: string;
      }>(`${API_URL}/plans/generate`, {
        horizon: selectedHorizon,
        timeout_seconds: 30,
        objective_profile: objectiveProfile
      }, { headers });

      if (res.data?.plan && Array.isArray(res.data.plan)) {
        setPlans(res.data.plan);
        setOptStatus(res.data.solver_status || 'OPTIMAL');
        setOptObjective(res.data.objective_value || 18715.0);
        setLastOptimizedAt(new Date().toLocaleTimeString('en-IN', { hour12: false }) + ' IST');
      }
      await fetchAllData();
    } catch (err) {
      setErrorBanner(apiError(err, 'Optimization solver run encountered an error.'));
    } finally {
      setOptimizing(false);
    }
  };

  // ------------------------------------------------------------------------
  // APPROVE / REJECT TASK
  // ------------------------------------------------------------------------
  const handleApproveTask = async (taskId: string, action: 'APPROVED' | 'REJECTED') => {
    setApprovingTaskId(taskId);
    try {
      const headers = authHeaders(token);
      await axios.post(`${API_URL}/plans/approve`, {
        task_id: taskId,
        action,
        approver: approverName,
        role: approverRole,
        remarks: approvalRemarks
      }, { headers });

      setPlans(prev => prev.map(p => {
        if (p.task_id === taskId) {
          return {
            ...p,
            approval_status: action,
            approved_by: approverName,
            approved_at: new Date().toLocaleString('en-IN')
          };
        }
        return p;
      }));
    } catch (err) {
      setErrorBanner(apiError(err, 'Failed to update approval status.'));
    } finally {
      setApprovingTaskId(null);
    }
  };

  const totalTasks = tasks.length || 82;
  const blocksUsedCount = new Set(plans.map(p => p.block_id)).size || 12;

  // Sidebar navigation menu items matching reference image exactly
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Home },
    { id: 'map', label: 'Network Map', icon: Map },
    { id: 'planning', label: 'Block Planning', icon: Calendar },
    { id: 'tasks', label: 'Maintenance Tasks', icon: Wrench },
    { id: 'reports', label: 'Reports', icon: BarChart2 },
  ];

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: '#f8fafc',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    }}>
      {/* ================================================================== */}
      {/* 1. DARK NAVY SIDEBAR (Full Height, Matching Reference)            */}
      {/* ================================================================== */}
      <aside style={{
        width: 240,
        minWidth: 240,
        height: '100vh',
        position: 'sticky',
        top: 0,
        background: '#111c2d',
        color: '#ffffff',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '20px 16px',
        boxSizing: 'border-box',
        zIndex: 50
      }}>
        <div>
          {/* Top Brand Logo & Title */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '4px 6px 26px 6px'
          }}>
            <img
              src="/railway_logo.png"
              alt="Indian Railways"
              style={{
                width: 38,
                height: 38,
                borderRadius: '50%',
                objectFit: 'cover',
                flexShrink: 0
              }}
            />
            <div>
              <div style={{
                fontSize: 17,
                fontWeight: 800,
                color: '#ffffff',
                letterSpacing: '-0.01em',
                lineHeight: 1.15
              }}>
                RailSamanvay<span style={{ color: '#ef4444' }}>AI</span>
              </div>
              <div style={{
                fontSize: 10.5,
                color: '#94a3b8',
                fontWeight: 500,
                letterSpacing: '0.02em',
                marginTop: 2
              }}>
                Ministry of Railways
              </div>
            </div>
          </div>

          {/* Primary Navigation Menu */}
          <nav style={{ display: 'grid', gap: 6 }}>
            {navItems.map(item => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id as typeof activeTab)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    width: '100%',
                    padding: '11px 14px',
                    borderRadius: 10,
                    background: isActive ? '#1d4ed8' : 'transparent',
                    color: isActive ? '#ffffff' : '#94a3b8',
                    border: 'none',
                    fontSize: 13.5,
                    fontWeight: isActive ? 600 : 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    textAlign: 'left'
                  }}
                  onMouseEnter={e => {
                    if (!isActive) {
                      e.currentTarget.style.color = '#ffffff';
                      e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                    }
                  }}
                  onMouseLeave={e => {
                    if (!isActive) {
                      e.currentTarget.style.color = '#94a3b8';
                      e.currentTarget.style.background = 'transparent';
                    }
                  }}
                >
                  <Icon size={18} color={isActive ? '#ffffff' : '#94a3b8'} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom Menu & Branding */}
        <div>
          {/* Subtle Horizontal Divider */}
          <div style={{
            height: 1,
            background: 'rgba(255, 255, 255, 0.08)',
            margin: '16px 4px 16px 4px'
          }} />

          {/* Settings & Logout Items */}
          <div style={{ display: 'grid', gap: 6 }}>
            <button
              onClick={() => setActiveTab('settings')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                width: '100%',
                padding: '10px 14px',
                borderRadius: 10,
                background: activeTab === 'settings' ? '#1d4ed8' : 'transparent',
                color: activeTab === 'settings' ? '#ffffff' : '#94a3b8',
                border: 'none',
                fontSize: 13,
                fontWeight: activeTab === 'settings' ? 600 : 500,
                cursor: 'pointer',
                textAlign: 'left'
              }}
              onMouseEnter={e => {
                if (activeTab !== 'settings') {
                  e.currentTarget.style.color = '#ffffff';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                }
              }}
              onMouseLeave={e => {
                if (activeTab !== 'settings') {
                  e.currentTarget.style.color = '#94a3b8';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <Settings size={18} color={activeTab === 'settings' ? '#ffffff' : '#94a3b8'} />
              <span>Settings</span>
            </button>

            <button
              onClick={onLogout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                width: '100%',
                padding: '10px 14px',
                borderRadius: 10,
                background: 'transparent',
                color: '#94a3b8',
                border: 'none',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
                textAlign: 'left'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = '#ef4444';
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.08)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = '#94a3b8';
                e.currentTarget.style.background = 'transparent';
              }}
            >
              <LogOut size={18} color="#94a3b8" />
              <span>Logout</span>
            </button>
          </div>

          {/* Footer Branding */}
          <div style={{ padding: '24px 8px 6px 8px' }}>
            <div style={{
              fontSize: 12,
              fontWeight: 700,
              color: '#ffffff',
              letterSpacing: '-0.01em'
            }}>
              RailSamanvayAI
            </div>
            <div style={{
              fontSize: 10.5,
              color: '#64748b',
              marginTop: 2
            }}>
              Smarter Blocks. Safer Railways.
            </div>
          </div>
        </div>
      </aside>

      {/* ================================================================== */}
      {/* 2. MAIN CONTENT AREA (Header + View Container)                     */}
      {/* ================================================================== */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Top Navbar Matching Reference (Right-aligned user & bell) */}
        <header style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          padding: '16px 36px 12px 36px',
          gap: 22,
          background: '#f8fafc'
        }}>
          {/* Notification Bell with Red Dot */}
          <button
            title="Notifications"
            style={{
              position: 'relative',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Bell size={20} color="#475569" />
            <span style={{
              position: 'absolute',
              top: 5,
              right: 6,
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: '#ef4444'
            }} />
          </button>

          {/* User Profile Pill */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            cursor: 'pointer'
          }}>
            <div style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: '#2563eb',
              color: '#ffffff',
              fontWeight: 700,
              fontSize: 12.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              DM
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', lineHeight: 1.2 }}>
                Debosmita
              </span>
              <span style={{ fontSize: 11, color: '#64748b', fontWeight: 500 }}>
                Chief Controller
              </span>
            </div>
            <ChevronDown size={14} color="#94a3b8" />
          </div>
        </header>

        {/* Dynamic Workspace Container */}
        <main style={{ padding: '4px 36px 36px 36px', flex: 1, overflowY: 'auto' }}>
          {errorBanner && (
            <div style={{
              padding: '12px 16px',
              background: 'rgba(239, 68, 68, 0.1)',
              border: `1px solid ${theme.red}`,
              borderRadius: 10,
              color: '#dc2626',
              fontSize: 13,
              marginBottom: 20,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <AlertTriangle size={18} color={theme.red} />
                <span>{errorBanner}</span>
              </div>
              <button
                onClick={() => setErrorBanner('')}
                style={{ background: 'none', border: 0, color: '#dc2626', cursor: 'pointer', fontSize: 14 }}
              >
                ✕
              </button>
            </div>
          )}

          {/* VIEW: DASHBOARD (Identical to user reference screenshot) */}
          {activeTab === 'dashboard' && (
            <OverviewView
              totalTasks={totalTasks}
              plans={plans}
              tasks={tasks}
              blocks={blocks}
              conflicts={conflicts}
              optStatus={optStatus}
              optObjective={optObjective}
              optimizing={optimizing}
              onRunOptimizer={handleRunOptimizer}
              onNavigateToConflicts={() => {
                setActiveTab('reports');
                setReportsSubTab('conflicts');
              }}
              onNavigateToPlanning={() => setActiveTab('planning')}
            />
          )}

          {/* VIEW: NETWORK MAP & AI ANALYZER */}
          {activeTab === 'map' && (
            <div style={{ display: 'grid', gap: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: '#0f172a' }}>
                    Network Map & AI Corridor Analyzer
                  </h1>
                  <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>
                    Geospatial view of {stations.length} Indian Railways stations and active corridors.
                  </p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(360px, 1fr)', gap: 20 }}>
                <MapView
                  stations={stations}
                  sections={sections}
                  selectedStation={selectedStation}
                  onSelectStation={(s) => {
                    setSelectedStation(s);
                    setRouteFrom(s.code);
                  }}
                  routeAnalysis={routeAnalysis}
                />

                <div style={{ display: 'grid', gap: 16 }}>
                  {selectedStation && (
                    <div style={cardStyle}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                        <div>
                          <span style={badgeStyle('rgba(56, 189, 248, 0.2)', theme.cyan)}>
                            STATION JUNCTION INSPECTOR
                          </span>
                          <h3 style={{ margin: '6px 0 0', fontSize: 18, fontWeight: 800, color: theme.text }}>
                            {selectedStation.name} ({selectedStation.code})
                          </h3>
                        </div>
                        <div style={{ fontSize: 11, color: theme.textDim }}>
                          {selectedStation.lat.toFixed(4)}, {selectedStation.lon.toFixed(4)}
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 12 }}>
                        <div style={{ padding: 10, background: theme.bg, borderRadius: 8 }}>
                          <span style={{ color: theme.textDim, display: 'block', marginBottom: 2 }}>Connected Corridors</span>
                          <strong style={{ color: theme.text }}>
                            {sections.filter(sec => sec.station_from === selectedStation.code || sec.station_to === selectedStation.code).length} Lines
                          </strong>
                        </div>
                        <div style={{ padding: 10, background: theme.bg, borderRadius: 8 }}>
                          <span style={{ color: theme.textDim, display: 'block', marginBottom: 2 }}>Scheduled Blocks</span>
                          <strong style={{ color: theme.cyan }}>
                            {plans.filter(p => (p.section_id || '').includes(selectedStation.code)).length} Blocks
                          </strong>
                        </div>
                      </div>
                    </div>
                  )}

                  <RouteAnalyzer
                    stations={stations}
                    token={token}
                    fromStation={routeFrom}
                    setFromStation={setRouteFrom}
                    toStation={routeTo}
                    setToStation={setRouteTo}
                    routeAnalysis={routeAnalysis}
                    setRouteAnalysis={setRouteAnalysis}
                  />
                </div>
              </div>
            </div>
          )}

          {/* VIEW: BLOCK PLANNING (With Joint Possessions & Form IR-CO-04 Sanctions) */}
          {activeTab === 'planning' && (
            <div style={{ display: 'grid', gap: 18 }}>
              {/* Planning Sub-Header Navigation */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #e2e8f0', paddingBottom: 12 }}>
                <div>
                  <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: '#0f172a' }}>
                    Automatic Block Planning Workspace
                  </h1>
                  <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>
                    Google OR-Tools CP-SAT multi-department synergy engine and Official Sanction Memo generator.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    onClick={() => setActiveTab('approval')}
                    style={{
                      background: '#ffffff',
                      border: '1px solid #cbd5e1',
                      color: '#0f172a',
                      padding: '8px 14px',
                      borderRadius: 8,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6
                    }}
                  >
                    <FileCheck size={14} color="#16a34a" />
                    Possession Sign-Off & Sanctions
                  </button>
                  <button
                    onClick={handleRunOptimizer}
                    disabled={optimizing}
                    style={{
                      ...buttonPrimary,
                      padding: '8px 16px',
                      fontSize: 12
                    }}
                  >
                    {optimizing ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} fill="#ffffff" />}
                    Re-Optimize Schedule
                  </button>
                </div>
              </div>

              <PlanningView
                plans={plans}
                totalTasks={totalTasks}
                blocksUsedCount={blocksUsedCount}
                selectedHorizon={selectedHorizon}
                setSelectedHorizon={setSelectedHorizon}
                objectiveProfile={objectiveProfile}
                setObjectiveProfile={setObjectiveProfile}
                optStatus={optStatus}
                optObjective={optObjective}
                lastOptimizedAt={lastOptimizedAt}
                optimizing={optimizing}
                onRunOptimizer={handleRunOptimizer}
                onApproveTask={handleApproveTask}
                approvingTaskId={approvingTaskId}
              />
            </div>
          )}

          {/* VIEW: MAINTENANCE TASKS */}
          {activeTab === 'tasks' && <TasksView tasks={tasks} />}

          {/* VIEW: REPORTS (Aggregated Reports Workspace) */}
          {activeTab === 'reports' && (
            <div style={{ display: 'grid', gap: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #e2e8f0', paddingBottom: 14 }}>
                <div>
                  <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: '#0f172a' }}>
                    Operations & Conflict Reports
                  </h1>
                  <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>
                    Review corridor conflicts, weekly schedules, monthly rolling forecasts, and central feeds.
                  </p>
                </div>

                {/* Sub-Tabs Pills */}
                <div style={{ display: 'flex', gap: 8, background: '#e2e8f0', padding: 4, borderRadius: 10 }}>
                  {[
                    { id: 'conflicts', label: `Conflicts (${conflicts.length})` },
                    { id: 'weekly', label: 'Weekly Plan' },
                    { id: 'monthly', label: 'Monthly Forecast' },
                    { id: 'integrations', label: 'IT Feeds' },
                    { id: 'approval', label: 'Sanction Memos' }
                  ].map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setReportsSubTab(tab.id as typeof reportsSubTab)}
                      style={{
                        padding: '6px 14px',
                        borderRadius: 8,
                        background: reportsSubTab === tab.id ? '#ffffff' : 'transparent',
                        color: reportsSubTab === tab.id ? '#0f172a' : '#64748b',
                        fontWeight: reportsSubTab === tab.id ? 700 : 500,
                        border: 'none',
                        fontSize: 12,
                        cursor: 'pointer',
                        boxShadow: reportsSubTab === tab.id ? '0 1px 3px rgba(0,0,0,0.08)' : 'none'
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {reportsSubTab === 'conflicts' && <ConflictsView conflicts={conflicts} />}
              {reportsSubTab === 'weekly' && <WeeklyView plans={plans} />}
              {reportsSubTab === 'monthly' && <MonthlyView goodsForecasts={goodsForecasts} />}
              {reportsSubTab === 'integrations' && <IntegrationsView integrations={integrations} />}
              {reportsSubTab === 'approval' && (
                <ApprovalView
                  plans={plans}
                  approverName={approverName}
                  setApproverName={setApproverName}
                  approverRole={approverRole}
                  setApproverRole={setApproverRole}
                  approvalRemarks={approvalRemarks}
                  setApprovalRemarks={setApprovalRemarks}
                  onApproveTask={handleApproveTask}
                  approvingTaskId={approvingTaskId}
                />
              )}
            </div>
          )}

          {/* VIEW: POSSESSION SIGN-OFF & OFFICIAL SANCTION MEMOS */}
          {activeTab === 'approval' && (
            <div style={{ display: 'grid', gap: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: '#0f172a' }}>
                    Control Office Sanction Workspace
                  </h1>
                  <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>
                    Official Indian Railways Form IR-CO-04 Sanction Notices, PTW Clearances & Chief Controller Sign-Off.
                  </p>
                </div>
                <button
                  onClick={() => setActiveTab('planning')}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #cbd5e1',
                    color: '#0f172a',
                    padding: '8px 14px',
                    borderRadius: 8,
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  ← Back to Planning
                </button>
              </div>

              <ApprovalView
                plans={plans}
                approverName={approverName}
                setApproverName={setApproverName}
                approverRole={approverRole}
                setApproverRole={setApproverRole}
                approvalRemarks={approvalRemarks}
                setApprovalRemarks={setApprovalRemarks}
                onApproveTask={handleApproveTask}
                approvingTaskId={approvingTaskId}
              />
            </div>
          )}

          {/* VIEW: SETTINGS */}
          {activeTab === 'settings' && <SettingsView modelHealth={modelHealth} />}
        </main>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// ROOT ROUTER
// --------------------------------------------------------------------------
export default function App() {
  const [token, setToken] = useState<string>(() => localStorage.getItem('token') || '');

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={token ? <Navigate to="/" /> : <Login setToken={setToken} />}
        />
        <Route
          path="/*"
          element={
            token ? (
              <ControlRoom
                token={token}
                onLogout={() => {
                  localStorage.removeItem('token');
                  setToken('');
                }}
              />
            ) : (
              <Navigate to="/login" />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
