import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Send, Save, ChevronLeft, CheckSquare, Square } from 'lucide-react'
import { getDossiers, updateScvaa } from '../api/dossiers'
import { MOTIFS_INCONFORMITE } from '../utils/mockData'
import DossierCard from '../components/DossierCard'
import DossierDetail from '../components/DossierDetail'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Alert from '../components/ui/Alert'
import { motion, AnimatePresence } from 'framer-motion'

const INIT = { superficie_ha: '', date_bornage: '', geometre_expert: '', contact_geometre: '', decision_conformite: '', motifs_inconformite: [], envoi_sms: false }

export default function Scvaa() {
  const [dossiers, setDossiers] = useState([])
  const [active,   setActive]   = useState(null)
  const [form,     setForm]     = useState(INIT)
  const [selected, setSelected] = useState(null)
  const [saving,   setSaving]   = useState(false)
  const [sending,  setSending]  = useState(false)
  const [success,  setSuccess]  = useState('')
  const [error,    setError]    = useState('')
  const [selectedDossiers, setSelectedDossiers] = useState([])

  const load = () => getDossiers('SCVAA').then(setDossiers)
  useEffect(() => { load() }, [])

  const handleOpen = d => { setActive(d); setForm({ ...INIT, ...d, motifs_inconformite: [], envoi_sms: false }) }

  const toggleSelectDossier = (id) => {
    setSelectedDossiers(prev => {
      if (prev.includes(id)) {
        return prev.filter(item => item !== id)
      } else {
        return [...prev, id]
      }
    })
  }

  const selectAllDossiers = () => {
    if (selectedDossiers.length === dossiers.length) {
      setSelectedDossiers([])
    } else {
      setSelectedDossiers(dossiers.map(d => d.id))
    }
  }

  const sendSelectedDossiers = async () => {
    if (selectedDossiers.length === 0) return

    setSending(true)
    try {
      console.log(`Envoi de ${selectedDossiers.length} dossiers`)
      await new Promise(resolve => setTimeout(resolve, 1000))

      setSuccess(`${selectedDossiers.length} dossier(s) envoyé(s) avec succès`)
      setSelectedDossiers([])
      setTimeout(() => setSuccess(''), 4000)
    } catch (err) {
      setError("Erreur lors de l'envoi des dossiers")
    } finally {
      setSending(false)
    }
  }

  const handleChange = e => {
    const { name, value } = e.target
    setForm(f => ({ ...f, [name]: value, ...(name === 'decision_conformite' ? { motifs_inconformite: [] } : {}) }))
  }
  const toggleMotif = m => setForm(f => ({
    ...f, motifs_inconformite: f.motifs_inconformite.includes(m)
      ? f.motifs_inconformite.filter(x => x !== m)
      : [...f.motifs_inconformite, m],
  }))

  const handleSubmit = async e => {
    e.preventDefault()
    if (!form.decision_conformite)  { setError('Veuillez sélectionner une décision.'); return }
    if (!form.superficie_ha)        { setError('La superficie est obligatoire.'); return }
    if (form.decision_conformite === 'NON_CONFORME' && form.motifs_inconformite.length === 0) {
      setError('Sélectionnez au moins un motif d\'inconformité.'); return
    }
    setSaving(true); setError('')
    try {
      await updateScvaa(active.id, form)

      let successMessage = 'Dossier enregistré avec succès.'
      if (form.envoi_sms) {
        successMessage = form.decision_conformite === 'CONFORME'
          ? 'Dossier conforme transmis au SPFEI pour attribution du titre.'
          : 'Dossier non conforme. SMS envoyé au propriétaire.'
      }

      setSuccess(successMessage)
      setActive(null); await load()
      setTimeout(() => setSuccess(''), 4000)
    } finally { setSaving(false) }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="w-full min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
      <span className="section-label green">Service SCVAA</span>
      <h1 className="font-display font-bold text-2xl sm:text-3xl lg:text-4xl text-neutral-900 mb-2">
        Contrôle <span style={{ color: 'var(--ci-green)' }}>technique</span>
      </h1>
      <p className="text-sm text-neutral-500 mb-6">
        Vérifiez la conformité cadastrale et topographique de chaque dossier.
      </p>

      {success && <Alert variant="success" className="mb-4">{success}</Alert>}

      <AnimatePresence>
        {active && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="bg-white rounded-lg p-6 mb-6"
            style={{ boxShadow: 'var(--shadow-md)', borderLeft: '4px solid var(--ci-green)' }}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-display font-bold text-base text-neutral-800 mb-1">Contrôle : {active.numero_dossier}</h2>
                <p className="text-sm text-neutral-500">{active.demandeur}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setActive(null)}
                className="flex items-center gap-1"
              >
                <ChevronLeft size={16} />
                Retour
              </Button>
            </div>

            {error && <Alert variant="error" className="mb-4">{error}</Alert>}
            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Superficie (ha)"  name="superficie_ha"    required value={form.superficie_ha}    onChange={handleChange} type="number" step="0.01" placeholder="ex : 2.5" />
              <Input label="Date de bornage"  name="date_bornage"              value={form.date_bornage}      onChange={handleChange} type="date" />
              <Input label="Géomètre Expert"  name="geometre_expert"           value={form.geometre_expert}   onChange={handleChange} placeholder="Nom du géomètre" />
              <Input label="Contact géomètre" name="contact_geometre"          value={form.contact_geometre}  onChange={handleChange} type="tel" />
            </div>

            {/* Décision */}
            <div>
              <p className="text-[0.78rem] font-bold text-neutral-700 mb-2">
                Décision <span style={{ color: 'var(--ci-orange)' }}>*</span>
              </p>
              <div className="flex gap-3">
                {[
                  { val: 'CONFORME',     label: 'Conforme',     Icon: CheckCircle, c: 'green' },
                  { val: 'NON_CONFORME', label: 'Non Conforme', Icon: XCircle,     c: 'red'   },
                ].map(({ val, label, Icon, c }) => (
                  <button key={val} type="button"
                    onClick={() => setForm(f => ({ ...f, decision_conformite: val, motifs_inconformite: [] }))}
                    className="flex-1 flex items-center justify-center gap-2 py-3 rounded-md border-2 font-bold text-sm transition-all"
                    style={{
                      borderColor: form.decision_conformite === val ? (c === 'green' ? 'var(--ci-green)' : '#EF4444') : 'var(--neutral-200)',
                      background:  form.decision_conformite === val ? (c === 'green' ? 'var(--ci-green-pale)' : '#FEF2F2') : 'var(--neutral-100)',
                      color:       form.decision_conformite === val ? (c === 'green' ? 'var(--ci-green-dark)' : '#991B1B') : 'var(--neutral-500)',
                    }}
                  >
                    <Icon size={16} />{label}
                  </button>
                ))}
              </div>
            </div>

            {form.decision_conformite === 'NON_CONFORME' && (
              <div>
                <p className="text-[0.78rem] font-bold text-neutral-700 mb-2">
                  Motifs d'inconformité <span style={{ color: 'var(--ci-orange)' }}>*</span>
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {MOTIFS_INCONFORMITE.map(m => (
                    <label key={m} className="flex items-start gap-2 cursor-pointer p-2.5 rounded-md hover:bg-neutral-100 transition-colors">
                      <input type="checkbox" checked={form.motifs_inconformite.includes(m)} onChange={() => toggleMotif(m)} className="mt-0.5 w-4 h-4 accent-red-500" />
                      <span className="text-sm text-neutral-700">{m}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Option d'envoi SMS */}
            <div className="flex items-center gap-2 cursor-pointer" onClick={() => setForm(f => ({ ...f, envoi_sms: !f.envoi_sms }))}>
              {form.envoi_sms ? (
                <CheckSquare size={18} className="text-ci-green" />
              ) : (
                <Square size={18} className="text-neutral-400" />
              )}
              <span className="text-sm text-neutral-700">
                Envoyer notification SMS au propriétaire
              </span>
            </div>

            <div className="flex flex-wrap gap-3 justify-end pt-2">
              <Button type="button" variant="ghost" onClick={() => setActive(null)}>Annuler</Button>
              <Button
                type="submit"
                variant={form.decision_conformite === 'CONFORME' ? 'secondary' : 'danger'}
                disabled={saving}
                className="flex items-center gap-2"
              >
                {saving ? 'Enregistrement…' : (
                  <>
                    <Save size={16} />
                    {form.envoi_sms ? (
                      form.decision_conformite === 'NON_CONFORME' ? 'Enregistrer et notifier' : 'Enregistrer et transmettre'
                    ) : 'Enregistrer uniquement'}
                  </>
                )}
              </Button>
            </div>
          </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Actions en lot */}
      {selectedDossiers.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-lg p-4 mb-4 flex flex-wrap items-center justify-between gap-3"
          style={{ boxShadow: 'var(--shadow-sm)', borderLeft: '4px solid var(--ci-green)' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-neutral-700">
              {selectedDossiers.length} dossier(s) sélectionné(s)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline-green"
              size="sm"
              onClick={() => setSelectedDossiers([])}
            >
              Désélectionner tout
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={sendSelectedDossiers}
              disabled={sending}
              className="flex items-center gap-2"
            >
              <Send size={14} />
              {sending ? 'Envoi...' : 'Envoyer'}
            </Button>
          </div>
        </motion.div>
      )}

      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <p className="text-sm text-neutral-500 font-semibold">{dossiers.length} dossier(s) à contrôler</p>
          {dossiers.length > 0 && (
            <div
              className="flex items-center gap-1 cursor-pointer text-sm text-neutral-500 hover:text-ci-green transition-colors"
              onClick={selectAllDossiers}
            >
              {selectedDossiers.length === dossiers.length && dossiers.length > 0 ? (
                <>
                  <CheckSquare size={16} className="text-ci-green" />
                  <span>Tout désélectionner</span>
                </>
              ) : (
                <>
                  <Square size={16} />
                  <span>Tout sélectionner</span>
                </>
              )}
            </div>
          )}
        </div>

        {dossiers.map(d => (
          <motion.div
            key={d.id}
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <DossierCard
              dossier={d}
              onClick={() => setSelected(d)}
              action={
                <div className="flex items-center gap-2">
                  <div
                    className="cursor-pointer p-1 hover:bg-neutral-100 rounded-md transition-colors"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleSelectDossier(d.id)
                    }}
                  >
                    {selectedDossiers.includes(d.id) ? (
                      <CheckSquare size={18} className="text-ci-green" />
                    ) : (
                      <Square size={18} className="text-neutral-400" />
                    )}
                  </div>
                  <Button
                    variant="outline-green"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleOpen(d)
                    }}
                  >
                    Contrôler
                  </Button>
                </div>
              }
            />
          </motion.div>
        ))}
        {dossiers.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-center py-16 text-neutral-400"
          >
            <p className="text-4xl mb-3">✅</p>
            <p className="font-semibold">Aucun dossier à contrôler</p>
          </motion.div>
        )}
      </div>
      <DossierDetail dossier={selected} onClose={() => setSelected(null)} />
      </div>
    </motion.div>
  )
}
