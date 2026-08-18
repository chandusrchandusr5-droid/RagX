import React, { useState } from 'react';
import { updateProfile, changePassword, deleteAccount } from '../services/api';
import { X, User, Lock, Trash2, LogOut, Shield, CheckCircle, AlertTriangle } from 'lucide-react';

export default function SettingsModal({ user, onClose, onUserUpdated, onLogout }) {
  const [activeSubTab, setActiveSubTab] = useState('profile');
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    setLoading(true);

    try {
      const res = await updateProfile(fullName);
      setMsg('Profile name updated successfully.');
      onUserUpdated(res.user);
    } catch (error) {
      setErr(error.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    setLoading(true);

    try {
      await changePassword(currentPassword, newPassword);
      setMsg('Password updated successfully. Please log in again.');
      setCurrentPassword('');
      setNewPassword('');
    } catch (error) {
      setErr(error.response?.data?.detail || 'Failed to change password.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    setErr(null);
    setLoading(true);
    try {
      await deleteAccount();
      onLogout();
    } catch (error) {
      setErr(error.response?.data?.detail || 'Failed to delete account.');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex justify-between items-center bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
              <User className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-base">Account Settings</h3>
              <p className="text-xs text-slate-400">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Subtabs */}
        <div className="flex border-b border-slate-800 bg-slate-950/30 px-6 pt-3 space-x-4">
          <button
            onClick={() => { setActiveSubTab('profile'); setMsg(null); setErr(null); }}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeSubTab === 'profile' ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Profile</span>
          </button>

          <button
            onClick={() => { setActiveSubTab('security'); setMsg(null); setErr(null); }}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeSubTab === 'security' ? 'border-cyan-500 text-cyan-400' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            <span>Security</span>
          </button>

          <button
            onClick={() => { setActiveSubTab('account'); setMsg(null); setErr(null); }}
            className={`pb-3 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-1.5 ${
              activeSubTab === 'account' ? 'border-red-500 text-red-400' : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Account</span>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 flex-1 overflow-y-auto space-y-4">
          {msg && (
            <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800/80 text-emerald-200 text-xs flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{msg}</span>
            </div>
          )}

          {err && (
            <div className="p-3 rounded-xl bg-red-950/60 border border-red-800/80 text-red-200 text-xs flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{err}</span>
            </div>
          )}

          {/* Profile Tab */}
          {activeSubTab === 'profile' && (
            <form onSubmit={handleUpdateProfile} className="space-y-4">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Account Role</span>
                  <span className={`px-2 py-0.5 rounded-full font-bold uppercase ${user?.role === 'ADMIN' ? 'bg-purple-950 text-purple-300 border border-purple-800' : 'bg-cyan-950 text-cyan-300 border border-cyan-800'}`}>
                    {user?.role}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">User ID</span>
                  <span className="font-mono text-slate-300">{user?.id}</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Display Name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded-xl transition-colors cursor-pointer"
              >
                Save Name Changes
              </button>
            </form>
          )}

          {/* Security Tab */}
          {activeSubTab === 'security' && (
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Current Password</label>
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">New Password</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs rounded-xl transition-colors cursor-pointer"
              >
                Update Password
              </button>
            </form>
          )}

          {/* Account Tab */}
          {activeSubTab === 'account' && (
            <div className="space-y-4">
              <div className="p-4 bg-red-950/30 border border-red-900/50 rounded-2xl">
                <h4 className="font-bold text-red-300 text-sm mb-1">Delete Account</h4>
                <p className="text-xs text-red-400/80 mb-4">
                  Permanently delete your account and all associated documents, vector embeddings, and RAG data space. This action cannot be undone.
                </p>

                {!showDeleteConfirm ? (
                  <button
                    type="button"
                    onClick={() => setShowDeleteConfirm(true)}
                    className="px-4 py-2 bg-red-800 hover:bg-red-700 text-white font-semibold text-xs rounded-xl transition-colors cursor-pointer"
                  >
                    Delete My Account
                  </button>
                ) : (
                  <div className="space-y-2">
                    <p className="text-xs font-bold text-red-200">Are you absolutely sure?</p>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={handleDeleteAccount}
                        disabled={loading}
                        className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-bold text-xs rounded-xl transition-colors cursor-pointer"
                      >
                        Confirm Delete
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowDeleteConfirm(false)}
                        className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition-colors cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex justify-between items-center">
          <button
            type="button"
            onClick={onLogout}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5 text-slate-400" />
            <span>Sign Out</span>
          </button>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
