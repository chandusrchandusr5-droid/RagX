import React, { useEffect, useState } from 'react';
import {
  fetchAdminDashboard,
  fetchAdminUsers,
  fetchAdminUserDocuments,
  deleteUserAdmin,
  fetchAdminActivity,
  viewDocumentUrl
} from '../services/api';
import { Users, FileText, Activity, Shield, Trash2, Eye, RefreshCw, Search, CheckCircle, AlertTriangle } from 'lucide-react';

export default function AdminPortal() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboardData, setDashboardData] = useState(null);
  const [users, setUsers] = useState([]);
  const [activities, setActivities] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userDocs, setUserDocs] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);

  const loadDashboard = async () => {
    setLoading(true);
    setErr(null);
    try {
      const data = await fetchAdminDashboard();
      setDashboardData(data);
    } catch (e) {
      setErr(e.response?.data?.detail || 'Failed to load admin dashboard.');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    setLoading(true);
    setErr(null);
    try {
      const data = await fetchAdminUsers();
      setUsers(data.users || []);
    } catch (e) {
      setErr(e.response?.data?.detail || 'Failed to fetch users list.');
    } finally {
      setLoading(false);
    }
  };

  const loadActivities = async () => {
    setLoading(true);
    setErr(null);
    try {
      const data = await fetchAdminActivity(150);
      setActivities(data.activities || []);
    } catch (e) {
      setErr(e.response?.data?.detail || 'Failed to fetch activity logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'dashboard') loadDashboard();
    else if (activeTab === 'users') loadUsers();
    else if (activeTab === 'activity') loadActivities();
  }, [activeTab]);

  const handleInspectUserDocs = async (user) => {
    setSelectedUser(user);
    try {
      const data = await fetchAdminUserDocuments(user.id);
      setUserDocs(data.documents || []);
    } catch (e) {
      setErr('Failed to fetch user documents.');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm(`Are you sure you want to delete user account '${userId}' and all associated documents?`)) {
      return;
    }
    try {
      await deleteUserAdmin(userId);
      setMsg(`User '${userId}' deleted successfully.`);
      loadUsers();
    } catch (e) {
      setErr(e.response?.data?.detail || 'Failed to delete user.');
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.id?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Admin Portal Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-slate-900 border border-slate-800 rounded-3xl shadow-xl">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-2xl bg-purple-950/80 border border-purple-500/30 flex items-center justify-center shadow-lg shadow-purple-950/50">
            <Shield className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">RAGX Administrative Portal</h1>
            <p className="text-xs text-slate-400">
              System Metrics • User Management • Document Metadata Inspection • Security Activity Audit
            </p>
          </div>
        </div>

        {/* Tab Selector */}
        <div className="flex bg-slate-950 p-1.5 rounded-2xl border border-slate-800 self-start md:self-auto">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'dashboard' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab('users')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'users' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Users & Data</span>
          </button>

          <button
            onClick={() => setActiveTab('activity')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'activity' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Activity Log</span>
          </button>
        </div>
      </div>

      {msg && (
        <div className="p-4 rounded-2xl bg-emerald-950/60 border border-emerald-800/80 text-emerald-200 text-sm flex items-center space-x-2">
          <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
          <span>{msg}</span>
        </div>
      )}

      {err && (
        <div className="p-4 rounded-2xl bg-red-950/60 border border-red-800/80 text-red-200 text-sm flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <span>{err}</span>
        </div>
      )}

      {/* 1. DASHBOARD TAB */}
      {activeTab === 'dashboard' && (
        <div className="space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
              <div className="flex justify-between items-center text-slate-400 text-xs font-semibold mb-2">
                <span>TOTAL REGISTERED USERS</span>
                <Users className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-3xl font-black text-white">{dashboardData?.metrics?.total_users || 0}</div>
              <div className="text-[11px] text-slate-500 mt-1">{dashboardData?.metrics?.active_users || 0} Active accounts</div>
            </div>

            <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
              <div className="flex justify-between items-center text-slate-400 text-xs font-semibold mb-2">
                <span>SYSTEM ADMINISTRATORS</span>
                <Shield className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-3xl font-black text-purple-300">{dashboardData?.metrics?.admin_count || 0}</div>
              <div className="text-[11px] text-slate-500 mt-1">Authorized admin privileges</div>
            </div>

            <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
              <div className="flex justify-between items-center text-slate-400 text-xs font-semibold mb-2">
                <span>TOTAL SYSTEM DOCUMENTS</span>
                <FileText className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-3xl font-black text-indigo-300">{dashboardData?.metrics?.total_documents || 0}</div>
              <div className="text-[11px] text-slate-500 mt-1">{dashboardData?.metrics?.active_documents || 0} Active in knowledge bases</div>
            </div>

            <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl">
              <div className="flex justify-between items-center text-slate-400 text-xs font-semibold mb-2">
                <span>AUDIT ACTIVITY LOGS</span>
                <Activity className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-3xl font-black text-emerald-300">{dashboardData?.metrics?.total_activities || 0}</div>
              <div className="text-[11px] text-slate-500 mt-1">Recorded audit events</div>
            </div>
          </div>

          {/* Recent Activity Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4">
            <h3 className="font-bold text-lg text-white">Recent Security & Activity Feed</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="p-3">Timestamp</th>
                    <th className="p-3">User</th>
                    <th className="p-3">Action</th>
                    <th className="p-3">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {(dashboardData?.recent_activities || []).map((act) => (
                    <tr key={act.id} className="hover:bg-slate-950/40">
                      <td className="p-3 font-mono text-slate-400">{act.timestamp}</td>
                      <td className="p-3 font-semibold text-slate-200">{act.user_name} ({act.user_email})</td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded-md bg-purple-950 text-purple-300 font-semibold border border-purple-800">
                          {act.action}
                        </span>
                      </td>
                      <td className="p-3 text-slate-400">{act.details || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 2. USERS & DATA TAB */}
      {activeTab === 'users' && (
        <div className="space-y-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 bg-slate-900 border border-slate-800 p-4 rounded-2xl">
            <div className="relative w-full md:w-96">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="text"
                placeholder="Search users by name, email, or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              onClick={loadUsers}
              className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Users</span>
            </button>
          </div>

          {/* User Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="p-4">User ID</th>
                    <th className="p-4">Full Name</th>
                    <th className="p-4">Email</th>
                    <th className="p-4">Role</th>
                    <th className="p-4">Docs</th>
                    <th className="p-4">Registered</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-950/40">
                      <td className="p-4 font-mono text-slate-400">{u.id}</td>
                      <td className="p-4 font-bold text-slate-100">{u.full_name}</td>
                      <td className="p-4 text-slate-300">{u.email}</td>
                      <td className="p-4">
                        <span className={`px-2.5 py-1 rounded-full font-bold uppercase text-[10px] ${u.role === 'ADMIN' ? 'bg-purple-950 text-purple-300 border border-purple-800' : 'bg-cyan-950 text-cyan-300 border border-cyan-800'}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="p-4 font-semibold text-slate-200">{u.document_count || 0} files</td>
                      <td className="p-4 text-slate-400 font-mono">{u.created_at}</td>
                      <td className="p-4 text-right space-x-2">
                        <button
                          onClick={() => handleInspectUserDocs(u)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-colors inline-flex items-center space-x-1 cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Inspect Docs</span>
                        </button>

                        <button
                          onClick={() => handleDeleteUser(u.id)}
                          className="px-3 py-1.5 bg-red-950/80 hover:bg-red-900 text-red-200 border border-red-800/80 rounded-lg text-xs font-semibold transition-colors inline-flex items-center space-x-1 cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-red-400" />
                          <span>Delete</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Selected User Document Inspection Drawer */}
          {selectedUser && (
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4">
              <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                <h3 className="font-bold text-white text-base">
                  Documents for User: <span className="text-cyan-400">{selectedUser.full_name}</span> ({selectedUser.email})
                </h3>
                <button
                  onClick={() => setSelectedUser(null)}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs rounded-lg text-slate-300"
                >
                  Close Inspection
                </button>
              </div>

              {userDocs.length === 0 ? (
                <p className="text-xs text-slate-500 py-4">No documents uploaded by this user.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {userDocs.map((doc) => (
                    <div key={doc.document_id} className="p-4 bg-slate-950 border border-slate-800 rounded-2xl flex justify-between items-center">
                      <div>
                        <div className="font-bold text-slate-200 text-xs">{doc.document_name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {doc.total_pages} pages • {doc.total_chunks} chunks • {doc.file_size}
                        </div>
                      </div>
                      <a
                        href={viewDocumentUrl(doc.document_id)}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3 py-1.5 bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 rounded-lg text-xs font-semibold transition-colors"
                      >
                        View PDF
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 3. ACTIVITY LOG TAB */}
      {activeTab === 'activity' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-slate-900 border border-slate-800 p-4 rounded-2xl">
            <h3 className="font-bold text-white text-sm">System & User Security Activity Log</h3>
            <button
              onClick={loadActivities}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Log</span>
            </button>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
                  <tr>
                    <th className="p-4">Timestamp</th>
                    <th className="p-4">User</th>
                    <th className="p-4">Action</th>
                    <th className="p-4">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {activities.map((act) => (
                    <tr key={act.id} className="hover:bg-slate-950/40">
                      <td className="p-4 font-mono text-slate-400">{act.timestamp}</td>
                      <td className="p-4 font-semibold text-slate-200">{act.user_name} ({act.user_email})</td>
                      <td className="p-4">
                        <span className="px-2.5 py-1 rounded-full bg-purple-950 text-purple-300 font-bold uppercase text-[10px] border border-purple-800">
                          {act.action}
                        </span>
                      </td>
                      <td className="p-4 text-slate-400">{act.details || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
