import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom';
import axios from 'axios';
import { LayoutDashboard, Map as MapIcon, ListTodo, Calendar, Settings, ShieldAlert, LogOut, Activity } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function Login({ setToken }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isRegister) {
        await axios.post(`${API_URL}/auth/register`, { email, password, full_name: "Admin" });
      }
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', password);
      const res = await axios.post(`${API_URL}/auth/token`, params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      localStorage.setItem('token', res.data.access_token);
      setToken(res.data.access_token);
      navigate('/');
    } catch (err) {
      alert("Authentication failed.");
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-slate-50">
      <div className="w-96 bg-white p-8 rounded-xl shadow-lg border border-slate-100">
        <div className="flex items-center space-x-2 mb-6 justify-center">
          <ShieldAlert className="text-blue-500 w-8 h-8" />
          <span className="text-slate-800 font-bold text-2xl tracking-tight">RailPlan AI</span>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full p-2 border border-slate-300 rounded-md" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="mt-1 w-full p-2 border border-slate-300 rounded-md" required />
          </div>
          <button type="submit" className="w-full bg-blue-600 text-white p-2 rounded-md font-medium hover:bg-blue-700">
            {isRegister ? 'Register & Login' : 'Sign In'}
          </button>
        </form>
        <button onClick={() => setIsRegister(!isRegister)} className="mt-4 text-sm text-blue-600 hover:underline w-full text-center">
          {isRegister ? 'Already have an account? Sign in' : 'Need an account? Register'}
        </button>
      </div>
    </div>
  );
}

function MapView({ stations }) {
  if (!stations.length) return <div>Loading Map...</div>;
  const center = [stations[0].lat, stations[0].lon];
  const positions = stations.map(s => [s.lat, s.lon]);
  
  return (
    <div className="h-96 w-full rounded-lg overflow-hidden border border-slate-200 shadow-sm z-0 relative">
      <MapContainer center={center} zoom={6} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
        <TileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png" />
        {stations.map((s, idx) => (
          <Marker key={idx} position={[s.lat, s.lon]}>
            <Popup><b>{s.name}</b> ({s.code})<br/>Critical Node</Popup>
          </Marker>
        ))}
        <Polyline positions={positions} color="blue" weight={3} opacity={0.6} />
      </MapContainer>
    </div>
  );
}

function Dashboard({ token }) {
  const [tasks, setTasks] = useState([]);
  const [plans, setPlans] = useState([]);
  const [stations, setStations] = useState([]);
  const [optRuns, setOptRuns] = useState([]);
  const [modelHealth, setModelHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [tasksRes, plansRes, stationsRes, runsRes, healthRes] = await Promise.all([
          axios.get(`${API_URL}/maintenance/tasks`, { headers }),
          axios.get(`${API_URL}/plans/optimized`, { headers }),
          axios.get(`${API_URL}/stations`, { headers }),
          axios.get(`${API_URL}/optimization/runs`, { headers }),
          axios.get(`${API_URL}/models/health`, { headers })
        ]);
        setTasks(tasksRes.data);
        setPlans(plansRes.data);
        setStations(stationsRes.data);
        setOptRuns(runsRes.data);
        setModelHealth(healthRes.data);
      } catch (error) {
        console.error("Error fetching data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-slate-800">Track Network Analysis (Delhi-Mumbai)</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
          <div className="text-slate-500 text-sm font-medium">Network Coverage</div>
          <div className="text-2xl font-bold text-slate-800 mt-1">{stations.length} Stations</div>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
          <div className="text-slate-500 text-sm font-medium">Critical Defect Tasks</div>
          <div className="text-2xl font-bold text-red-600 mt-1">{tasks.filter(t => t.priority_class === 'P1').length} Tasks</div>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
          <div className="text-slate-500 text-sm font-medium">Model Precision (PR-AUC)</div>
          <div className="text-2xl font-bold text-indigo-600 mt-1">
            {modelHealth?.metrics?.pr_auc ? (modelHealth.metrics.pr_auc * 100).toFixed(1) + '%' : 'Loading...'}
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
          <div className="text-slate-500 text-sm font-medium">Last Optimization Status</div>
          <div className="text-2xl font-bold text-green-600 mt-1">
            {optRuns[0]?.status || 'FEASIBLE'}
          </div>
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-lg font-bold mb-3 text-slate-800">Geospatial Track Status</h2>
        <MapView stations={stations} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
            <h2 className="font-semibold text-slate-800">Maintenance Backlog (Top 5)</h2>
          </div>
          <div className="p-5">
            {loading ? <p>Loading...</p> : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-slate-500 border-b">
                    <th className="pb-2">Task</th>
                    <th className="pb-2">Section</th>
                    <th className="pb-2">Priority</th>
                    <th className="pb-2">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.slice(0, 5).map((t, idx) => (
                    <tr key={idx} className="border-b last:border-0 border-slate-100">
                      <td className="py-3 font-medium text-slate-700">{t.id.substring(0, 12)}...</td>
                      <td className="py-3 text-slate-600">{t.asset_id.substring(0,8)}</td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${t.priority_class === 'P1' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                          {t.priority_class || 'P1'}
                        </span>
                      </td>
                      <td className="py-3 text-slate-600">{t.required_duration_min} min</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 bg-slate-50">
            <h2 className="font-semibold text-slate-800">Optimized Block Schedule (CP-SAT)</h2>
          </div>
          <div className="p-5">
             {loading ? <p>Loading...</p> : (
              <div className="space-y-4">
                {Array.from(new Set(plans.map(p => p.block_id))).slice(0, 3).map((block_id: any) => {
                  const blockTasks = plans.filter(p => p.block_id === block_id);
                  return (
                    <div key={block_id} className="border border-indigo-100 rounded-lg p-4 bg-indigo-50/50">
                      <div className="flex justify-between items-center mb-2">
                        <div className="font-semibold text-indigo-900">{block_id}</div>
                        <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full font-medium">Ready</span>
                      </div>
                      <div className="text-sm text-slate-600 mb-1">Section: {blockTasks[0]?.section_id}</div>
                      <div className="text-xs text-slate-500 mb-3">Tasks bundled: {blockTasks.length} (Hard constraint max: 2)</div>
                      <button className="bg-indigo-600 text-white px-3 py-1.5 rounded text-xs font-medium hover:bg-indigo-700 w-full transition">Approve Block</button>
                    </div>
                  );
                })}
                {plans.length === 0 && <p className="text-sm text-slate-500 text-center py-4">Optimizer is computing schedules...</p>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Sidebar({ setToken }) {
  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  return (
    <div className="w-64 bg-slate-900 text-slate-300 min-h-screen p-4 flex flex-col shadow-xl z-20 relative">
      <div className="flex items-center space-x-2 mb-8 mt-2 px-2">
        <ShieldAlert className="text-blue-400 w-8 h-8" />
        <span className="text-white font-bold text-lg tracking-tight">RailPlan AI SaaS</span>
      </div>
      
      <nav className="flex-1 space-y-1">
        <Link to="/" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg bg-slate-800 text-white font-medium">
          <LayoutDashboard className="w-5 h-5" /> <span>Dashboard</span>
        </Link>
        <a href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition">
          <MapIcon className="w-5 h-5" /> <span>Track Analysis</span>
        </a>
        <a href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition">
          <Activity className="w-5 h-5" /> <span>Model Health</span>
        </a>
        <a href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition">
          <Calendar className="w-5 h-5" /> <span>Block Planner</span>
        </a>
      </nav>
      
      <div className="mt-auto space-y-1">
        <a href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition">
          <Settings className="w-5 h-5" /> <span>Settings</span>
        </a>
        <button onClick={handleLogout} className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-red-500/10 hover:text-red-400 text-slate-400 w-full transition text-left">
          <LogOut className="w-5 h-5" /> <span>Logout</span>
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));

  return (
    <Router>
      <Routes>
        <Route path="/login" element={!token ? <Login setToken={setToken} /> : <Navigate to="/" />} />
        <Route path="/*" element={
          token ? (
            <div className="flex min-h-screen bg-slate-50">
              <Sidebar setToken={setToken} />
              <main className="flex-1 overflow-auto h-screen">
                <header className="bg-white border-b border-slate-200 h-16 flex items-center px-6 justify-between sticky top-0 z-10">
                   <div className="font-medium text-slate-800">Production Control Center</div>
                   <div className="flex space-x-4 items-center">
                      <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)] animate-pulse"></span>
                      <span className="text-sm font-medium text-slate-600">Database Connected</span>
                   </div>
                </header>
                <Routes>
                  <Route path="/" element={<Dashboard token={token} />} />
                </Routes>
              </main>
            </div>
          ) : <Navigate to="/login" />
        } />
      </Routes>
    </Router>
  );
}
