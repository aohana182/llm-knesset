import { useState, useEffect } from 'react';
import { api } from '../api';
import ModelPicker from './ModelPicker';
import './AdminPanel.css';

export default function AdminPanel({ onClose, isAdmin }) {
  // Admin-only state
  const [settings, setSettings] = useState(null);
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [adminEmails, setAdminEmails] = useState([]);
  const [newAdminEmail, setNewAdminEmail] = useState('');
  const [testing, setTesting] = useState(false);
  const [testStatus, setTestStatus] = useState(null);

  // Per-user state
  const [councilModels, setCouncilModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [usingDefaults, setUsingDefaults] = useState(true);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const prefs = await api.getPrefs();
      setCouncilModels(prefs.council_models || []);
      setChairmanModel(prefs.chairman_model || '');
      setUsingDefaults(prefs.using_defaults);

      if (isAdmin) {
        const s = await api.getSettings();
        setSettings(s);
        setAdminEmails(s.admin_emails || []);
      }
    } catch (e) {
      console.error('Failed to load settings:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus(null);
    try {
      await api.updatePrefs({ council_models: councilModels, chairman_model: chairmanModel });

      if (isAdmin) {
        const adminUpdates = { admin_emails: adminEmails };
        if (apiKey.trim()) adminUpdates.openrouter_api_key = apiKey.trim();
        await api.updateSettings(adminUpdates);
        await loadAll();
        setApiKey('');
      }

      setSaveStatus({ ok: true, msg: 'Settings saved.' });
    } catch (e) {
      setSaveStatus({ ok: false, msg: 'Failed to save settings.' });
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus(null), 3500);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestStatus(null);
    try {
      const result = await api.testConnection();
      setTestStatus(result.success
        ? { ok: true, msg: 'Connection successful. API key is valid.' }
        : { ok: false, msg: result.error || 'Connection failed.' });
    } catch (e) {
      setTestStatus({ ok: false, msg: 'Could not reach the backend.' });
    } finally {
      setTesting(false);
      setTimeout(() => setTestStatus(null), 4000);
    }
  };

  const handleCouncilChange = (ids) => {
    setCouncilModels(ids);
    if (ids.length > 0 && !ids.includes(chairmanModel)) {
      setChairmanModel(ids[0]);
    }
  };

  const addAdminEmail = () => {
    const e = newAdminEmail.trim().toLowerCase();
    if (e && !adminEmails.includes(e)) {
      setAdminEmails([...adminEmails, e]);
      setNewAdminEmail('');
    }
  };

  const removeAdminEmail = (email) => {
    setAdminEmails(adminEmails.filter((e) => e !== email));
  };

  return (
    <div className="admin-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="admin-panel">
        <div className="admin-header">
          <div className="admin-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14" />
              <path d="M12 2v2M12 20v2M2 12h2M20 12h2" />
            </svg>
            <h2>{isAdmin ? 'Settings' : 'My Models'}</h2>
          </div>
          <button className="admin-close" onClick={onClose} aria-label="Close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {loading ? (
          <div className="admin-loading">Loading…</div>
        ) : (
          <div className="admin-body">

            {/* ── API Key (admin only) ────────────────────────── */}
            {isAdmin && (
              <section className="admin-section">
                <div className="section-label">
                  <svg className="section-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
                  </svg>
                  <h3>OpenRouter API Key</h3>
                  {settings?.openrouter_api_key_set && <span className="badge badge-green">Connected</span>}
                </div>
                {settings?.openrouter_api_key_set && (
                  <div className="current-key">Current key: <code>{settings.openrouter_api_key_preview}</code></div>
                )}
                <p className="section-desc">
                  Get your key at <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer">openrouter.ai/keys</a>
                </p>
                <div className="key-input-row">
                  <div className="input-wrapper">
                    <input
                      type={showKey ? 'text' : 'password'}
                      className="admin-input"
                      placeholder={settings?.openrouter_api_key_set ? 'Enter new key to replace…' : 'sk-or-v1-…'}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      autoComplete="off"
                      spellCheck={false}
                    />
                    <button className="toggle-visibility" onClick={() => setShowKey((v) => !v)} type="button" tabIndex={-1}>
                      {showKey ? (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                      ) : (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                      )}
                    </button>
                  </div>
                  <button className="btn btn-outline" onClick={handleTest} disabled={testing || (!apiKey.trim() && !settings?.openrouter_api_key_set)}>
                    {testing ? 'Testing…' : 'Test'}
                  </button>
                </div>
                {testStatus && (
                  <div className={`status-msg ${testStatus.ok ? 'status-ok' : 'status-err'}`}>
                    {testStatus.ok ? '✓' : '✗'} {testStatus.msg}
                  </div>
                )}
              </section>
            )}

            {/* ── Council Models (all users) ──────────────────── */}
            <section className="admin-section">
              <div className="section-label">
                <svg className="section-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4M8 11V9M16 11V9"/>
                </svg>
                <h3>My Council Models</h3>
                <span className="badge">{councilModels.length} selected</span>
                {usingDefaults && <span className="badge badge-muted">default</span>}
              </div>
              <p className="section-desc">
                These models will debate and rank each other's responses in your conversations.
              </p>
              <ModelPicker
                selectedIds={councilModels}
                onChange={handleCouncilChange}
                placeholder="Search OpenRouter models to add…"
              />
            </section>

            {/* ── Chairman Model (all users) ──────────────────── */}
            <section className="admin-section">
              <div className="section-label">
                <svg className="section-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
                <h3>My Chairman Model</h3>
              </div>
              <p className="section-desc">
                Synthesizes all responses into the final answer. Can be any model on OpenRouter.
              </p>
              {chairmanModel && <div className="current-chairman">Current: <code>{chairmanModel}</code></div>}
              <ModelPicker
                selectedIds={chairmanModel ? [chairmanModel] : []}
                onChange={(id) => setChairmanModel(id)}
                singleSelect={true}
                placeholder="Search for a chairman model…"
              />
            </section>

            {/* ── Admin Emails (admin only) ───────────────────── */}
            {isAdmin && (
              <section className="admin-section">
                <div className="section-label">
                  <svg className="section-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                  <h3>Admins</h3>
                  <span className="badge">{adminEmails.length}</span>
                </div>
                <p className="section-desc">
                  These Google-account emails have admin access to manage the API key and admin list.
                </p>
                <div className="email-list">
                  {adminEmails.map((email) => (
                    <div key={email} className="email-chip">
                      <span>{email}</span>
                      <button className="chip-remove" onClick={() => removeAdminEmail(email)}>
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
                <div className="add-model-row">
                  <input
                    type="email"
                    className="admin-input"
                    placeholder="someone@gmail.com"
                    value={newAdminEmail}
                    onChange={(e) => setNewAdminEmail(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addAdminEmail()}
                  />
                  <button className="btn btn-outline" onClick={addAdminEmail} disabled={!newAdminEmail.trim()}>Add</button>
                </div>
              </section>
            )}

          </div>
        )}

        <div className="admin-footer">
          {saveStatus && (
            <div className={`status-msg ${saveStatus.ok ? 'status-ok' : 'status-err'}`}>
              {saveStatus.ok ? '✓' : '✗'} {saveStatus.msg}
            </div>
          )}
          <div className="footer-actions">
            <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving || loading}>
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
