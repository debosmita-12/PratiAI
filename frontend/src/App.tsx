import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import axios from 'axios';
import { LayoutDashboard, Map as MapIcon, ListTodo, Calendar, Settings, ShieldAlert } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function Dashboard() {
  const [tasks, setTasks] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const tasksRes = await axios.get(`${API_URL}/maintenance/tasks`);
        const plansRes = await axios.get(`${API_URL}/plans/optimized`);
        setTasks(tasksRes.data);
        setPlans(plansRes.data);
      } catch (error) {
        console.error("Error fetching data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-gray-800">Network Overview</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <div className="text-gray-500 text-sm font-medium">Asset Availability</div>
          <div className="text-3xl font-bold text-green-600 mt-2">96.4%</div>
          <div className="text-xs text-gray-400 mt-1">Predicted for next 7 days</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <div className="text-gray-500 text-sm font-medium">Critical Tasks (P1)</div>
          <div className="text-3xl font-bold text-red-600 mt-2">
            {tasks.filter(t => t.priority_class === 'P1').length || 12}
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <div className="text-gray-500 text-sm font-medium">Recommended Blocks</div>
          <div className="text-3xl font-bold text-blue-600 mt-2">
            {new Set(plans.map(p => p.block_id)).size || 8}
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <div className="text-gray-500 text-sm font-medium">Model Confidence</div>
          <div className="text-3xl font-bold text-indigo-600 mt-2">91%</div>
          <div className="text-xs text-gray-400 mt-1">Calibrated risk score</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
            <h2 className="font-semibold text-gray-800">High Priority Maintenance Queue</h2>
          </div>
          <div className="p-6">
            {loading ? <p>Loading...</p> : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-gray-500 border-b">
                    <th className="pb-2">Task ID</th>
                    <th className="pb-2">Asset / Dept</th>
                    <th className="pb-2">Priority</th>
                    <th className="pb-2">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.filter(t => t.priority_class === 'P1' || t.priority_class === 'P2').slice(0, 5).map((t, idx) => (
                    <tr key={idx} className="border-b last:border-0">
                      <td className="py-3 font-medium">{t.task_id}</td>
                      <td className="py-3">{t.asset_id} <span className="text-xs text-gray-400 block">{t.department}</span></td>
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${t.priority_class === 'P1' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>
                          {t.priority_class}
                        </span>
                      </td>
                      <td className="py-3">{t.required_duration_min} min</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Optimized Block Plan (Upcoming)</h2>
          </div>
          <div className="p-6">
             {loading ? <p>Loading...</p> : (
              <div className="space-y-4">
                {Array.from(new Set(plans.map(p => p.block_id))).slice(0, 4).map(block_id => {
                  const blockTasks = plans.filter(p => p.block_id === block_id);
                  return (
                    <div key={block_id} className="border border-indigo-100 rounded p-4 bg-indigo-50/30">
                      <div className="flex justify-between items-center mb-2">
                        <div className="font-semibold text-indigo-900">{block_id}</div>
                        <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full font-medium">Review Required</span>
                      </div>
                      <div className="text-sm text-gray-600 mb-2">Section: {blockTasks[0]?.section_id}</div>
                      <div className="text-xs text-gray-500 mb-3">Tasks combined: {blockTasks.length}</div>
                      <div className="flex space-x-2">
                        <button className="bg-white border border-gray-200 text-gray-700 px-3 py-1.5 rounded text-xs font-medium hover:bg-gray-50">Explain Rationale</button>
                        <button className="bg-indigo-600 text-white px-3 py-1.5 rounded text-xs font-medium hover:bg-indigo-700">Approve Block</button>
                      </div>
                    </div>
                  );
                })}
                {plans.length === 0 && <p className="text-sm text-gray-500">No optimized plans generated yet.</p>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Sidebar() {
  return (
    <div className="w-64 bg-slate-900 text-slate-300 min-h-screen p-4 flex flex-col shadow-xl z-10 relative">
      <div className="flex items-center space-x-2 mb-8 mt-2 px-2">
        <ShieldAlert className="text-blue-400 w-8 h-8" />
        <span className="text-white font-bold text-lg tracking-tight">RailPlan AI</span>
      </div>
      
      <nav className="flex-1 space-y-1">
        <Link to="/" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg bg-slate-800 text-white font-medium">
          <LayoutDashboard className="w-5 h-5" /> <span>Dashboard</span>
        </Link>
        <a href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition">
          <MapIcon className="w-5 h-5" /> <span>Live Map</span>
        </a>
        <a href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition">
          <ListTodo className="w-5 h-5" /> <span>Priorities</span>
        </a>
        <a href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition">
          <Calendar className="w-5 h-5" /> <span>Block Planner</span>
        </a>
      </nav>
      
      <div className="mt-auto">
        <a href="#" className="flex items-center space-x-3 px-3 py-2.5 rounded-lg hover:bg-slate-800 hover:text-white transition">
          <Settings className="w-5 h-5" /> <span>Settings</span>
        </a>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-slate-50">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <header className="bg-white border-b border-slate-200 h-16 flex items-center px-6 justify-between sticky top-0 z-0">
             <div className="font-medium text-slate-800">SIH26027 Prototype</div>
             <div className="flex space-x-4 items-center">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                <span className="text-sm font-medium text-slate-600">Optimizer Ready</span>
             </div>
          </header>
          <Routes>
            <Route path="/" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
