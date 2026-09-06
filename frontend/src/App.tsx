import { CSSProperties, FormEvent, useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import axios, { AxiosError } from 'axios';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Calendar,
  Clock,
  LayoutDashboard,
  Layers,
  ListTodo,
  LogOut,
  Map as MapIcon,
  MapPin,
  PlusCircle,
  Settings,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { MapContainer, Marker, Popup, Polyline, TileLayer } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

L.Marker.prototype.options.icon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

type Station = {
  id?: number | string;
  code: string;
  name: string;
  lat: number;
  lon: number;
};

type StationRef = Partial<Station>;

type Analysis = {
  block_required?: boolean;
  risk_level?: string;
  confidence?: number;
  recommendation?: string;
  reason?: string;
  explanation?: string;
  from_station?: StationRef;
  to_station?: StationRef;
  station_from?: StationRef;
  station_to?: StationRef;
};

type DashboardData = {
  total_stations?: number;
  active_blocks?: number;
  pending_analyses?: number;
  safety_alerts?: number;
  recent_activities?: Array<{
    title?: string;
    description?: string;
    created_at?: string;
  }>;
};

const inputStyle: CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  padding: '11px 12px',
  border: '1px solid #cbd5e1',
  borderRadius: 9,
  fontSize: 14,
  outline: 'none',
  background: '#f8fafc',
};

const buttonStyle: CSSProperties = {
  width: '100%',
  padding: '12px',
  border: 0,
  borderRadius: 9,
  background: '#2563eb',
  color: '#ffffff',
  fontWeight: 700,
  cursor: 'pointer',
  fontSize: 14,
};

const cardStyle: CSSProperties = {
  background: '#ffffff',
  border: '1px solid #e2e8f0',
  borderRadius: 14,
  padding: 20,
  boxShadow: '0 1px 3px rgba(15,23,42,.05)',
};

const labelStyle: CSSProperties = {
  display: 'block',
  marginBottom: 6,
  color: '#475569',
  fontSize: 12,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '.04em',
};

function apiError(error: unknown, fallback: string) {
  const detail = (error as AxiosError<{ detail?: string }>).response?.data?.detail;
  return typeof detail === 'string' ? detail : fallback;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

function Login({ setToken }: { setToken: (token: string) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');

    try {
      const cleanEmail = email.trim().toLowerCase();

      if (isRegister) {
        await axios.post(`${API_URL}/auth/register`, {
          email: cleanEmail,
          password,
          full_name: fullName.trim() || 'Admin',
        });
      }

      const form = new URLSearchParams({
        username: cleanEmail,
        password,
      });

      const { data } = await axios.post<{ access_token: string }>(
        `${API_URL}/auth/token`,
        form,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        },
      );

      if (!data.access_token) {
        throw new Error('The server did not return an access token.');
      }

      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      navigate('/');
    } catch (err) {
      setError(apiError(err, 'Authentication failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        padding: 24,
        background: '#f1f5f9',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <section
        style={{
          ...cardStyle,
          width: '100%',
          maxWidth: 420,
          padding: 32,
          boxShadow: '0 12px 32px rgba(15,23,42,.12)',
        }}
      >
        <header style={{ textAlign: 'center', marginBottom: 28 }}>
          <ShieldAlert size={40} color="#2563eb" />
          <h1 style={{ margin: '10px 0 0', color: '#0f172a' }}>RailPlan AI</h1>
          <p style={{ color: '#64748b', fontSize: 14 }}>
            Automatic Railway Block Planning SaaS
          </p>
        </header>

        {error && (
          <div
            style={{
              marginBottom: 16,
              padding: 12,
              borderRadius: 8,
              background: '#fef2f2',
              color: '#b91c1c',
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={submit} style={{ display: 'grid', gap: 16 }}>
          {isRegister && (
            <div>
              <label style={labelStyle}>Full name</label>
              <input
                style={inputStyle}
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
                placeholder="Your name"
              />
            </div>
          )}

          <div>
            <label style={labelStyle}>Email</label>
            <input
              style={inputStyle}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              placeholder="admin@railplan.ai"
            />
          </div>

          <div>
            <label style={labelStyle}>Password</label>
            <input
              style={inputStyle}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            style={{ ...buttonStyle, opacity: loading ? 0.65 : 1 }}
            disabled={loading}
          >
            {loading ? 'Please wait…' : isRegister ? 'Register & Sign In' : 'Sign In'}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setIsRegister((value) => !value);
            setError('');
          }}
          style={{
            width: '100%',
            marginTop: 16,
            border: 0,
            background: 'transparent',
            color: '#2563eb',
            cursor: 'pointer',
          }}
        >
          {isRegister
            ? 'Already have an account? Sign in'
            : 'New to RailPlan? Create an account'}
        </button>
      </section>
    </main>
  );
}

function MapView({
  stations,
  highlightedRoute,
}: {
  stations: Station[];
  highlightedRoute: Analysis | null;
}) {
  const center: LatLngExpression = stations.length
    ? [stations[0].lat, stations[0].lon]
    : [20.5937, 78.9629];

  const positions = stations.map(
    (station) => [station.lat, station.lon] as LatLngExpression,
  );

  const from = highlightedRoute?.from_station ?? highlightedRoute?.station_from;
  const to = highlightedRoute?.to_station ?? highlightedRoute?.station_to;

  const route =
    from?.lat != null &&
    from?.lon != null &&
    to?.lat != null &&
    to?.lon != null
      ? [
          [from.lat, from.lon],
          [to.lat, to.lon],
        ]
      : null;

  return (
    <div
      style={{
        height: 380,
        overflow: 'hidden',
        borderRadius: 14,
        border: '1px solid #e2e8f0',
      }}
    >
      <MapContainer
        center={center}
        zoom={stations.length ? 5 : 4}
        scrollWheelZoom={false}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors &copy; CARTO"
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />

        {stations.map((station) => (
          <Marker
            key={station.id ?? station.code}
            position={[station.lat, station.lon]}
          >
            <Popup>
              <strong>{station.name}</strong>
              <br />
              Code: {station.code}
              <br />
              <small>
                {station.lat.toFixed(4)}, {station.lon.toFixed(4)}
              </small>
            </Popup>
          </Marker>
        ))}

        {positions.length > 1 && (
          <Polyline
            positions={positions}
            color="#3b82f6"
            weight={3}
            opacity={0.55}
            dashArray="4 6"
          />
        )}

        {route && (
          <Polyline
            positions={route}
            color={highlightedRoute?.block_required ? '#ef4444' : '#10b981'}
            weight={6}
            opacity={0.9}
          />
        )}
      </MapContainer>
    </div>
  );
}

function AddStationModal({
  open,
  onClose,
  onAdded,
  token,
}: {
  open: boolean;
  onClose: () => void;
  onAdded: () => Promise<void>;
  token: string;
}) {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');

    const latitude = Number(lat);
    const longitude = Number(lon);

    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      latitude < -90 ||
      latitude > 90 ||
      longitude < -180 ||
      longitude > 180
    ) {
      setError('Enter valid latitude and longitude values.');
      return;
    }

    setLoading(true);

    try {
      await axios.post(
        `${API_URL}/stations`,
        {
          code: code.trim().toUpperCase(),
          name: name.trim(),
          lat: latitude,
          lon: longitude,
        },
        { headers: authHeaders(token) },
      );

      await onAdded();
      setCode('');
      setName('');
      setLat('');
      setLon('');
      onClose();
    } catch (err) {
      setError(apiError(err, 'Failed to add station.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'grid',
        placeItems: 'center',
        padding: 16,
        background: 'rgba(15,23,42,.55)',
      }}
    >
      <section
        style={{
          ...cardStyle,
          width: '100%',
          maxWidth: 500,
          padding: 0,
          overflow: 'hidden',
        }}
      >
        <header
          style={{
            padding: '16px 20px',
            background: '#0f172a',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <strong>
            <PlusCircle
              size={18}
              style={{ verticalAlign: 'middle', marginRight: 8 }}
            />
            Add New Railway Station
          </strong>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            style={{
              color: '#ffffff',
              background: 'none',
              border: 0,
              fontSize: 24,
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </header>

        <form onSubmit={submit} style={{ padding: 20, display: 'grid', gap: 14 }}>
          {error && <div style={{ color: '#b91c1c', fontSize: 13 }}>{error}</div>}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Station code</label>
              <input
                style={inputStyle}
                value={code}
                onChange={(event) => setCode(event.target.value)}
                required
                placeholder="BVI"
              />
            </div>

            <div>
              <label style={labelStyle}>Station name</label>
              <input
                style={inputStyle}
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                placeholder="Borivali"
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Latitude</label>
              <input
                style={inputStyle}
                type="number"
                step="any"
                value={lat}
                onChange={(event) => setLat(event.target.value)}
                required
              />
            </div>

            <div>
              <label style={labelStyle}>Longitude</label>
              <input
                style={inputStyle}
                type="number"
                step="any"
                value={lon}
                onChange={(event) => setLon(event.target.value)}
                required
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'end', gap: 10 }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                border: 0,
                background: 'transparent',
                cursor: 'pointer',
                color: '#475569',
              }}
            >
              Cancel
            </button>

            <button
              type="submit"
              style={{ ...buttonStyle, width: 'auto', padding: '10px 16px' }}
              disabled={loading}
            >
              {loading ? 'Saving…' : 'Add Station'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function RouteAnalyzer({
  stations,
  token,
  onResult,
}: {
  stations: Station[];
  token: string;
  onResult: (result: Analysis) => void;
}) {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [department, setDepartment] = useState('ENGINEERING');
  const [condition, setCondition] = useState('0.55');
  const [overdue, setOverdue] = useState('14');
  const [traffic, setTraffic] = useState('130');
  const [critical, setCritical] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Analysis | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (stations.length >= 2) {
      setFrom(stations[0].code);
      setTo(stations[1].code);
    }
  }, [stations]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!from || !to || from === to) {
      setError('Choose two different stations.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const { data } = await axios.post<Analysis>(
        `${API_URL}/routes/analyze`,
        {
          station_from: from,
          station_to: to,
          department,
          condition_score: Number(condition),
          overdue_days: Number(overdue),
          traffic_load: Number(traffic),
          safety_critical: critical,
        },
        { headers: authHeaders(token) },
      );

      setResult(data);
      onResult(data);
    } catch (err) {
      setError(apiError(err, 'Failed to analyze route.'));
    } finally {
      setLoading(false);
    }
  }

  const recommendation =
    result?.recommendation ?? result?.reason ?? result?.explanation;

  return (
    <section style={cardStyle}>
      <header
        style={{
          margin: '-20px -20px 20px',
          padding: 20,
          background: '#0f172a',
          color: '#ffffff',
          borderRadius: '14px 14px 0 0',
        }}
      >
        <h2 style={{ margin: 0, fontSize: 18 }}>
          <Sparkles
            size={19}
            style={{
              verticalAlign: 'middle',
              color: '#fbbf24',
              marginRight: 8,
            }}
          />
          AI Route & Block Requirement Analyzer
        </h2>
      </header>

      <form onSubmit={submit} style={{ display: 'grid', gap: 15 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={labelStyle}>Origin station</label>
            <select
              style={inputStyle}
              value={from}
              onChange={(event) => setFrom(event.target.value)}
            >
              {stations.map((station) => (
                <option key={station.code} value={station.code}>
                  {station.name} ({station.code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={labelStyle}>Destination station</label>
            <select
              style={inputStyle}
              value={to}
              onChange={(event) => setTo(event.target.value)}
            >
              {stations.map((station) => (
                <option key={station.code} value={station.code}>
                  {station.name} ({station.code})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          <div>
            <label style={labelStyle}>Department</label>
            <select
              style={inputStyle}
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
            >
              <option>ENGINEERING</option>
              <option>OPERATIONS</option>
              <option>SIGNAL</option>
            </select>
          </div>

          <div>
            <label style={labelStyle}>Condition score</label>
            <input
              style={inputStyle}
              type="number"
              min="0"
              max="1"
              step="0.01"
              value={condition}
              onChange={(event) => setCondition(event.target.value)}
            />
          </div>

          <div>
            <label style={labelStyle}>Overdue days</label>
            <input
              style={inputStyle}
              type="number"
              min="0"
              value={overdue}
              onChange={(event) => setOverdue(event.target.value)}
            />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'end', gap: 16 }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Traffic load</label>
            <input
              style={inputStyle}
              type="number"
              min="0"
              value={traffic}
              onChange={(event) => setTraffic(event.target.value)}
            />
          </div>

          <label style={{ fontSize: 13, color: '#334155' }}>
            <input
              type="checkbox"
              checked={critical}
              onChange={(event) => setCritical(event.target.checked)}
            />{' '}
            Safety-critical work
          </label>

          <button
            type="submit"
            style={{ ...buttonStyle, width: 'auto', padding: '11px 16px' }}
            disabled={loading || stations.length < 2}
          >
            {loading ? 'Analyzing…' : 'Analyze route'}{' '}
            <ArrowRight size={15} style={{ verticalAlign: 'middle' }} />
          </button>
        </div>

        {error && <p style={{ margin: 0, color: '#b91c1c', fontSize: 13 }}>{error}</p>}
      </form>

      {result && (
        <div
          style={{
            marginTop: 18,
            padding: 16,
            borderRadius: 10,
            background: result.block_required ? '#fef2f2' : '#ecfdf5',
            color: '#1e293b',
          }}
        >
          <strong style={{ color: result.block_required ? '#b91c1c' : '#047857' }}>
            {result.block_required ? 'Block required' : 'Block not required'}
          </strong>

          {result.risk_level && <span> · Risk: {result.risk_level}</span>}

          {typeof result.confidence === 'number' && (
            <span> · Confidence: {(result.confidence * 100).toFixed(0)}%</span>
          )}

          {recommendation && (
            <p style={{ margin: '8px 0 0', fontSize: 13 }}>
              {recommendation}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Activity;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <article style={cardStyle}>
      <Icon size={21} color={color} />
      <p style={{ ...labelStyle, margin: '12px 0 4px' }}>{label}</p>
      <strong style={{ color: '#0f172a', fontSize: 28 }}>{value}</strong>
    </article>
  );
}

function Dashboard({
  token,
  onLogout,
}: {
  token: string;
  onLogout: () => void;
}) {
  const [stations, setStations] = useState<Station[]>([]);
  const [summary, setSummary] = useState<DashboardData>({});
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadDashboard() {
    setLoading(true);
    setError('');

    try {
      const headers = authHeaders(token);

      const [stationResponse, dashboardResponse] = await Promise.all([
        axios.get<Station[]>(`${API_URL}/stations`, { headers }),
        axios
          .get<DashboardData>(`${API_URL}/dashboard/summary`, { headers })
          .catch(() => ({ data: {} as DashboardData })),
      ]);

      setStations(Array.isArray(stationResponse.data) ? stationResponse.data : []);
      setSummary(dashboardResponse.data ?? {});
    } catch (err) {
      setError(apiError(err, 'Unable to load the dashboard.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, [token]);

  const activity = Array.isArray(summary.recent_activities)
    ? summary.recent_activities
    : [];

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#f8fafc',
        color: '#0f172a',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <header
        style={{
          height: 64,
          padding: '0 24px',
          background: '#0f172a',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <strong>
          <ShieldAlert
            size={21}
            style={{
              verticalAlign: 'middle',
              marginRight: 8,
              color: '#60a5fa',
            }}
          />
          RailPlan AI
        </strong>

        <button
          type="button"
          onClick={onLogout}
          style={{
            border: 0,
            background: 'transparent',
            color: '#cbd5e1',
            cursor: 'pointer',
          }}
        >
          <LogOut size={17} style={{ verticalAlign: 'middle', marginRight: 6 }} />
          Log out
        </button>
      </header>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '220px 1fr',
          minHeight: 'calc(100vh - 64px)',
        }}
      >
        <aside
          style={{
            padding: 18,
            borderRight: '1px solid #e2e8f0',
            background: '#ffffff',
          }}
        >
          <p style={labelStyle}>Workspace</p>

          {[
            [LayoutDashboard, 'Dashboard'],
            [MapIcon, 'Network map'],
            [ListTodo, 'Block plans'],
            [Calendar, 'Schedule'],
            [Settings, 'Settings'],
          ].map(([Icon, text]) => {
            const SidebarIcon = Icon as typeof LayoutDashboard;

            return (
              <div
                key={String(text)}
                style={{
                  padding: '10px 8px',
                  color: text === 'Dashboard' ? '#2563eb' : '#475569',
                  fontSize: 14,
                }}
              >
                <SidebarIcon
                  size={16}
                  style={{ verticalAlign: 'middle', marginRight: 9 }}
                />
                {String(text)}
              </div>
            );
          })}
        </aside>

        <main style={{ padding: 28, maxWidth: 1400, width: '100%', boxSizing: 'border-box' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 22,
            }}
          >
            <div>
              <h1 style={{ margin: 0, fontSize: 25 }}>Operations dashboard</h1>
              <p style={{ color: '#64748b', marginBottom: 0 }}>
                Monitor railway infrastructure and plan safe blocks.
              </p>
            </div>

            <button
              type="button"
              onClick={() => setShowModal(true)}
              style={{ ...buttonStyle, width: 'auto', padding: '11px 15px' }}
            >
              <PlusCircle
                size={17}
                style={{ verticalAlign: 'middle', marginRight: 6 }}
              />
              Add station
            </button>
          </div>

          {error && (
            <div
              style={{
                padding: 12,
                background: '#fef2f2',
                color: '#b91c1c',
                marginBottom: 16,
                borderRadius: 8,
              }}
            >
              {error}
            </div>
          )}

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
              gap: 16,
              marginBottom: 22,
            }}
          >
            <Stat
              icon={MapPin}
              label="Stations"
              value={summary.total_stations ?? stations.length}
              color="#2563eb"
            />
            <Stat
              icon={Layers}
              label="Active blocks"
              value={summary.active_blocks ?? 0}
              color="#7c3aed"
            />
            <Stat
              icon={Activity}
              label="Pending analyses"
              value={summary.pending_analyses ?? 0}
              color="#d97706"
            />
            <Stat
              icon={AlertTriangle}
              label="Safety alerts"
              value={summary.safety_alerts ?? 0}
              color="#dc2626"
            />
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1.2fr) minmax(320px, .8fr)',
              gap: 20,
            }}
          >
            <div style={{ display: 'grid', gap: 20 }}>
              <RouteAnalyzer
                stations={stations}
                token={token}
                onResult={setAnalysis}
              />

              <section style={cardStyle}>
                <h2 style={{ marginTop: 0, fontSize: 17 }}>
                  <MapIcon
                    size={18}
                    style={{
                      verticalAlign: 'middle',
                      marginRight: 8,
                      color: '#2563eb',
                    }}
                  />
                  Rail network
                </h2>

                {loading ? (
                  <p style={{ color: '#64748b' }}>Loading map…</p>
                ) : (
                  <MapView stations={stations} highlightedRoute={analysis} />
                )}
              </section>
            </div>

            <section style={cardStyle}>
              <h2 style={{ marginTop: 0, fontSize: 17 }}>
                <Clock
                  size={18}
                  style={{
                    verticalAlign: 'middle',
                    marginRight: 8,
                    color: '#2563eb',
                  }}
                />
                Recent activity
              </h2>

              {activity.length ? (
                activity.map((item, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '12px 0',
                      borderBottom: '1px solid #e2e8f0',
                    }}
                  >
                    <strong style={{ fontSize: 14 }}>
                      {item.title ?? item.description ?? 'System activity'}
                    </strong>

                    {item.created_at && (
                      <small
                        style={{
                          display: 'block',
                          color: '#64748b',
                          marginTop: 4,
                        }}
                      >
                        {item.created_at}
                      </small>
                    )}
                  </div>
                ))
              ) : (
                <p style={{ color: '#64748b', fontSize: 14 }}>
                  No recent activity available.
                </p>
              )}
            </section>
          </div>
        </main>
      </div>

      <AddStationModal
        open={showModal}
        onClose={() => setShowModal(false)}
        onAdded={loadDashboard}
        token={token}
      />
    </div>
  );
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token') ?? '');

  function logout() {
    localStorage.removeItem('token');
    setToken('');
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            token ? <Navigate to="/" replace /> : <Login setToken={setToken} />
          }
        />

        <Route
          path="/*"
          element={
            token ? (
              <Dashboard token={token} onLogout={logout} />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;