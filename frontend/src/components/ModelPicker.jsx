import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api';
import './ModelPicker.css';

function formatCtx(n) {
  if (!n) return '';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(0)}M ctx`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K ctx`;
  return `${n} ctx`;
}

function formatPrice(p) {
  if (p === 0) return 'Free';
  if (p < 0.01) return `$${p.toFixed(4)}/M`;
  return `$${p.toFixed(2)}/M`;
}

function isMultimodal(modality) {
  return modality && modality.includes('image');
}

export default function ModelPicker({ selectedIds = [], onChange, singleSelect = false, placeholder = 'Search models…' }) {
  const [allModels, setAllModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [providerFilter, setProviderFilter] = useState('all');
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);

  const loadModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listModels();
      setAllModels(data.models || []);
    } catch (e) {
      setError('Could not load models. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const providers = ['all', ...Array.from(new Set(allModels.map((m) => m.id.split('/')[0]))).sort()];

  const filtered = allModels.filter((m) => {
    const q = query.toLowerCase();
    const matchesQuery = !q || m.id.toLowerCase().includes(q) || m.name.toLowerCase().includes(q);
    const matchesProvider = providerFilter === 'all' || m.id.startsWith(providerFilter + '/');
    const notAlreadyAdded = singleSelect || !selectedIds.includes(m.id);
    return matchesQuery && matchesProvider && notAlreadyAdded;
  });

  const handleSelect = (model) => {
    if (!selectedIds.includes(model.id)) {
      onChange(singleSelect ? model.id : [...selectedIds, model.id]);
    }
    setOpen(false);
    setQuery('');
  };

  const handleRemove = (id) => {
    onChange(selectedIds.filter((s) => s !== id));
  };

  return (
    <div className="model-picker" ref={dropdownRef}>
      {/* Selected chips (multi-select mode) */}
      {!singleSelect && selectedIds.length > 0 && (
        <div className="picker-chips">
          {selectedIds.map((id) => {
            const model = allModels.find((m) => m.id === id);
            return (
              <div key={id} className="picker-chip">
                <span className="chip-provider">{id.split('/')[0]}</span>
                <span className="chip-name">{model ? model.name.replace(/^[^:]+:\s*/, '') : id.split('/')[1]}</span>
                <button className="chip-remove" onClick={() => handleRemove(id)} aria-label={`Remove ${id}`}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Search input */}
      <div className="picker-search-row">
        <div className="picker-input-wrap">
          <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            className="picker-input"
            placeholder={loading ? 'Loading models…' : placeholder}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
            onFocus={() => setOpen(true)}
            disabled={loading}
            autoComplete="off"
            spellCheck={false}
          />
          {loading && <div className="picker-spinner" />}
        </div>

        {/* Provider filter */}
        <select
          className="provider-filter"
          value={providerFilter}
          onChange={(e) => setProviderFilter(e.target.value)}
        >
          {providers.map((p) => (
            <option key={p} value={p}>{p === 'all' ? 'All providers' : p}</option>
          ))}
        </select>
      </div>

      {/* Dropdown */}
      {open && !loading && (
        <div className="picker-dropdown">
          {error && <div className="picker-error">{error}</div>}
          {!error && filtered.length === 0 && (
            <div className="picker-empty">
              {query ? `No models match "${query}"` : 'No models available'}
            </div>
          )}
          {!error && filtered.slice(0, 80).map((model) => (
            <button
              key={model.id}
              className="picker-option"
              onClick={() => handleSelect(model)}
              type="button"
            >
              <div className="option-main">
                <span className="option-provider">{model.id.split('/')[0]}</span>
                <span className="option-name">{model.name.replace(/^[^:]+:\s*/, '')}</span>
                {isMultimodal(model.modality) && (
                  <span className="option-tag tag-vision">vision</span>
                )}
              </div>
              <div className="option-meta">
                <span className="option-id">{model.id}</span>
                <div className="option-stats">
                  {model.context_length && <span className="option-stat">{formatCtx(model.context_length)}</span>}
                  <span className={`option-price ${model.price_per_million === 0 ? 'price-free' : ''}`}>
                    {formatPrice(model.price_per_million)}
                  </span>
                </div>
              </div>
            </button>
          ))}
          {filtered.length > 80 && (
            <div className="picker-overflow">Showing 80 of {filtered.length} — refine your search</div>
          )}
        </div>
      )}
    </div>
  );
}
