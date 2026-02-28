import { useState, useMemo } from 'react'
import {
  Search, Filter, Plus, Download, Send,
  CheckSquare, Square, X, ChevronDown
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button, Badge } from '../components/ui'
import { motion, AnimatePresence } from 'framer-motion'

const DOSSIERS = [
  { num: 'DOS-2024-0142', nom: 'Kouassi Emmanuel',  type: 'SPFEI', statut: 'spfei',        date: '18/02/2026' },
  { num: 'DOS-2024-0141', nom: 'Diallo Fatoumata',  type: 'SCVAA', statut: 'scvaa',        date: '17/02/2026' },
  { num: 'DOS-2024-0140', nom: 'Koné Adama',        type: 'SPFEI', statut: 'nonconforme',  date: '16/02/2026' },
  { num: 'DOS-2024-0139', nom: 'Traoré Mariam',     type: 'SCVAA', statut: 'termine',      date: '15/02/2026' },
  { num: 'DOS-2024-0138', nom: 'Bamba Sékou',       type: 'SPFEI', statut: 'conservation', date: '14/02/2026' },
  { num: 'DOS-2024-0137', nom: 'Coulibaly Fatou',   type: 'SCVAA', statut: 'courrier',     date: '13/02/2026' },
]

const STATUTS = {
  courrier:     { label: 'Courrier',     color: '#1E40AF', bg: '#EFF6FF', border: '#BFDBFE' },
  spfei:        { label: 'SPFEI',       color: 'var(--ci-orange-dark)', bg: 'var(--ci-orange-pale)', border: '#FCD9BD' },
  scvaa:        { label: 'SCVAA',       color: 'var(--ci-green-dark)',  bg: 'var(--ci-green-pale)',  border: '#A7F3D0' },
  nonconforme:  { label: 'Non conforme',color: '#991B1B', bg: '#FEF2F2', border: '#FECACA' },
  conservation: { label: 'Conservation',color: '#5B21B6', bg: '#F5F3FF', border: '#DDD6FE' },
  termine:      { label: 'Terminé',     color: '#166534', bg: '#F0FDF4', border: '#BBF7D0' },
}

function StatusBadge({ statut }) {
  const s = STATUTS[statut] || { label: statut, color: 'var(--n-600)', bg: 'var(--n-100)', border: 'var(--n-200)' }
  return (
    <span style={{
      background: s.bg, color: s.color,
      border: `1px solid ${s.border}`,
      fontSize: '0.68rem', fontWeight: 700,
      letterSpacing: '0.05em', textTransform: 'uppercase',
      padding: '3px 10px', borderRadius: 99,
      whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 5,
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: s.color, opacity: 0.7 }} />
      {s.label}
    </span>
  )
}

export default function Dossiers() {
  const [selectedDossiers, setSelectedDossiers] = useState([])
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({ search: '', statut: '' })

  const filtered = useMemo(() => DOSSIERS.filter(d => {
    if (filters.search && !(
      d.nom.toLowerCase().includes(filters.search.toLowerCase()) ||
      d.num.toLowerCase().includes(filters.search.toLowerCase())
    )) return false
    if (filters.statut && d.statut !== filters.statut) return false
    return true
  }), [filters])

  const toggleSelect = (num) =>
    setSelectedDossiers(prev =>
      prev.includes(num) ? prev.filter(x => x !== num) : [...prev, num]
    )

  const selectAll = () =>
    setSelectedDossiers(
      selectedDossiers.length === filtered.length ? [] : filtered.map(d => d.num)
    )

  const hasActiveFilter = filters.search || filters.statut

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}
      className="page"
    >
      <div className="page-inner">

        {/* ─── En-tête ─── */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-7">
          <div>
            <span className="section-label">Gestion</span>
            <h1 className="font-display font-bold text-2xl sm:text-3xl" style={{ color: 'var(--n-900)' }}>
              Tous les <span style={{ color: 'var(--ci-orange)' }}>dossiers</span>
            </h1>
          </div>
          <Link to="/nouveau">
            <Button variant="primary">
              <Plus size={15} /> Nouveau dossier
            </Button>
          </Link>
        </div>

        {/* ─── Barre recherche + filtres ─── */}
        <div className="card mb-5">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--n-400)' }} />
              <input
                type="text"
                placeholder="Rechercher par nom, numéro…"
                value={filters.search}
                onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
                className="input-field pl-9"
              />
            </div>
            <button
              onClick={() => setShowFilters(p => !p)}
              className="btn btn-ghost btn-sm gap-1.5"
              style={{
                borderRadius: 8,
                border: showFilters ? '1.5px solid var(--ci-orange)' : '1.5px solid var(--n-200)',
                background: showFilters ? 'var(--ci-orange-pale)' : undefined,
                color: showFilters ? 'var(--ci-orange)' : 'var(--n-600)',
              }}
            >
              <Filter size={14} />
              <span className="hidden sm:inline">Filtres</span>
              {hasActiveFilter && (
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: 'var(--ci-orange)', flexShrink: 0,
                }} />
              )}
            </button>
          </div>

          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                style={{ overflow: 'hidden' }}
              >
                <div className="divider" style={{ margin: '1rem 0 0.75rem' }} />
                <div className="flex flex-wrap gap-3 items-end">
                  <div className="flex flex-col gap-1 min-w-[160px]">
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Statut</label>
                    <select
                      value={filters.statut}
                      onChange={e => setFilters(f => ({ ...f, statut: e.target.value }))}
                      className="input-field text-sm"
                      style={{ paddingTop: 8, paddingBottom: 8 }}
                    >
                      <option value="">Tous les statuts</option>
                      {Object.entries(STATUTS).map(([k, v]) => (
                        <option key={k} value={k}>{v.label}</option>
                      ))}
                    </select>
                  </div>
                  {hasActiveFilter && (
                    <button
                      onClick={() => setFilters({ search: '', statut: '' })}
                      className="btn btn-ghost btn-sm"
                      style={{ borderRadius: 8 }}
                    >
                      <X size={13} /> Réinitialiser
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ─── Barre d'actions ─── */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <button
              onClick={selectAll}
              className="flex items-center gap-1.5 text-sm font-medium transition-colors"
              style={{ color: 'var(--n-500)' }}
            >
              {selectedDossiers.length === filtered.length && filtered.length > 0
                ? <CheckSquare size={16} style={{ color: 'var(--ci-orange)' }} />
                : <Square size={16} />
              }
              <span className="hidden sm:inline">
                {selectedDossiers.length > 0
                  ? `${selectedDossiers.length} sélectionné(s)`
                  : 'Sélectionner tout'
                }
              </span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <p className="text-sm" style={{ color: 'var(--n-400)' }}>
              {filtered.length} dossier{filtered.length > 1 ? 's' : ''}
            </p>

            {/* Export */}
            <div className="relative">
              <button
                onClick={() => setShowExportMenu(p => !p)}
                disabled={selectedDossiers.length === 0}
                className="btn btn-ghost btn-sm"
                style={{ borderRadius: 8 }}
              >
                <Download size={14} />
                <span className="hidden sm:inline">Exporter</span>
                <ChevronDown size={12} />
              </button>
              <AnimatePresence>
                {showExportMenu && (
                  <motion.div
                    initial={{ opacity: 0, y: -6, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -6, scale: 0.97 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-full mt-1 z-20"
                    style={{
                      background: 'white',
                      border: '1px solid var(--n-150)',
                      borderRadius: 10,
                      boxShadow: 'var(--shadow-lg)',
                      minWidth: 140, overflow: 'hidden',
                    }}
                  >
                    {['CSV', 'Excel', 'PDF'].map(fmt => (
                      <button
                        key={fmt}
                        onClick={() => setShowExportMenu(false)}
                        className="w-full text-left px-3 py-2.5 text-sm transition-colors hover:bg-neutral-50"
                        style={{ color: 'var(--n-700)' }}
                      >
                        {fmt}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <button
              disabled={selectedDossiers.length === 0}
              className="btn btn-primary btn-sm"
              style={{ borderRadius: 8 }}
            >
              <Send size={13} />
              Envoyer ({selectedDossiers.length})
            </button>
          </div>
        </div>

        {/* ─── Tableau ─── */}
        <motion.div
          initial={{ y: 16, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="card"
          style={{ padding: 0, overflow: 'hidden' }}
        >
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 44, textAlign: 'center' }}>
                    <button onClick={selectAll}>
                      {selectedDossiers.length === filtered.length && filtered.length > 0
                        ? <CheckSquare size={16} style={{ color: 'var(--ci-orange)' }} />
                        : <Square size={16} style={{ color: 'var(--n-300)' }} />
                      }
                    </button>
                  </th>
                  <th>N° Dossier</th>
                  <th>Bénéficiaire</th>
                  <th>Type</th>
                  <th>Statut</th>
                  <th>Date</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d, i) => (
                  <motion.tr
                    key={d.num}
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2, delay: i * 0.04 }}
                    style={{
                      background: selectedDossiers.includes(d.num)
                        ? 'var(--ci-orange-pale)' : undefined,
                    }}
                  >
                    <td style={{ textAlign: 'center' }}>
                      <button onClick={() => toggleSelect(d.num)}>
                        {selectedDossiers.includes(d.num)
                          ? <CheckSquare size={16} style={{ color: 'var(--ci-orange)' }} />
                          : <Square size={16} style={{ color: 'var(--n-300)' }} />
                        }
                      </button>
                    </td>
                    <td>
                      <span className="mono font-semibold" style={{ color: 'var(--n-800)' }}>
                        {d.num}
                      </span>
                    </td>
                    <td style={{ color: 'var(--n-700)' }}>{d.nom}</td>
                    <td>
                      <span className="text-xs font-semibold" style={{ color: 'var(--n-500)' }}>
                        {d.type}
                      </span>
                    </td>
                    <td><StatusBadge statut={d.statut} /></td>
                    <td style={{ color: 'var(--n-400)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                      {d.date}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <Button variant="ghost" size="sm" style={{ borderRadius: 6 }}>
                        Voir
                      </Button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="empty-state">
                <p className="empty-state-icon">🔍</p>
                <p className="empty-state-title">Aucun résultat</p>
                <p className="empty-state-sub">Modifiez vos critères de recherche.</p>
              </div>
            )}
          </div>

          {/* Mobile cards */}
          <div className="md:hidden">
            {filtered.map((d, i) => (
              <motion.div
                key={d.num}
                layout
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.05 }}
                style={{
                  padding: '14px 16px',
                  borderBottom: '1px solid var(--n-100)',
                  background: selectedDossiers.includes(d.num) ? 'var(--ci-orange-pale)' : undefined,
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5">
                    <button className="mt-0.5" onClick={() => toggleSelect(d.num)}>
                      {selectedDossiers.includes(d.num)
                        ? <CheckSquare size={16} style={{ color: 'var(--ci-orange)' }} />
                        : <Square size={16} style={{ color: 'var(--n-300)' }} />
                      }
                    </button>
                    <div>
                      <p className="mono font-semibold text-sm" style={{ color: 'var(--n-800)' }}>{d.num}</p>
                      <p className="text-sm mt-0.5" style={{ color: 'var(--n-600)' }}>{d.nom}</p>
                    </div>
                  </div>
                  <StatusBadge statut={d.statut} />
                </div>
                <div className="flex items-center justify-between mt-2 pl-7">
                  <p className="text-xs" style={{ color: 'var(--n-400)', fontFamily: 'var(--font-mono)' }}>
                    {d.type} · {d.date}
                  </p>
                  <Button variant="ghost" size="sm" style={{ borderRadius: 6, fontSize: 12 }}>
                    Voir
                  </Button>
                </div>
              </motion.div>
            ))}
            {filtered.length === 0 && (
              <div className="empty-state">
                <p className="empty-state-icon">🔍</p>
                <p className="empty-state-title">Aucun résultat</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}