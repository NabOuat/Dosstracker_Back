import { useEffect, useState } from 'react'
import { Send } from 'lucide-react'
import { getDossiers, updateSpfeiAdmin } from '../api/dossiers'
import DossierCard from '../components/DossierCard'
import DossierDetail from '../components/DossierDetail'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Alert from '../components/ui/Alert'

const INIT = {
  nationalite: '', genre: '', type_cf: '',
  date_enquete_officielle: '', date_valid_enq: '',
  date_etab_cf: '', date_demande_immat: '',
}

export default function SpfeiAdmin() {
  const [dossiers, setDossiers] = useState([])
  const [active,   setActive]   = useState(null)
  const [form,     setForm]     = useState(INIT)
  const [selected, setSelected] = useState(null)
  const [saving,   setSaving]   = useState(false)
  const [success,  setSuccess]  = useState('')

  const load = () => getDossiers('SPFEI_ADMIN').then(setDossiers)
  useEffect(() => { load() }, [])

  const handleOpen = d => { setActive(d); setForm({ ...INIT, ...d }) }
  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    setSaving(true)
    try {
      await updateSpfeiAdmin(active.id, form)
      setSuccess('Dossier transmis au SERVICE SCVAA.')
      setActive(null); await load()
      setTimeout(() => setSuccess(''), 3000)
    } finally { setSaving(false) }
  }

  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
      <span className="section-label">Service SPFEI</span>
      <h1 className="font-display font-bold text-2xl sm:text-3xl lg:text-4xl text-neutral-900 mb-2">
        Contrôle <span style={{ color: 'var(--ci-orange)' }}>administratif</span>
      </h1>
      <p className="text-sm text-neutral-500 mb-6">
        Complétez les informations administratives puis transmettez au SERVICE SCVAA.
      </p>

      {success && <Alert variant="success" className="mb-4">{success}</Alert>}

      {active && (
        <div className="bg-white rounded-lg p-6 mb-6" style={{ boxShadow: 'var(--shadow-md)', borderLeft: '4px solid var(--ci-orange)' }}>
          <h2 className="font-display font-bold text-base text-neutral-800 mb-1">Traitement : {active.numero_dossier}</h2>
          <p className="text-sm text-neutral-500 mb-5">{active.demandeur}</p>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-[0.78rem] font-bold text-neutral-700">Nationalité <span style={{ color: 'var(--ci-orange)' }}>*</span></label>
              <input name="nationalite" required value={form.nationalite} onChange={handleChange} className="input-field" placeholder="ex : Ivoirienne" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[0.78rem] font-bold text-neutral-700">Genre <span style={{ color: 'var(--ci-orange)' }}>*</span></label>
              <select name="genre" required value={form.genre} onChange={handleChange} className="input-field">
                <option value="">Sélectionner…</option>
                <option value="Masculin">Masculin</option>
                <option value="Féminin">Féminin</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[0.78rem] font-bold text-neutral-700">Type CF <span style={{ color: 'var(--ci-orange)' }}>*</span></label>
              <select name="type_cf" required value={form.type_cf} onChange={handleChange} className="input-field">
                <option value="">Sélectionner…</option>
                <option value="Rural">Rural</option>
                <option value="Urbain">Urbain</option>
              </select>
            </div>
            <Input label="Date enquête officielle"           name="date_enquete_officielle" value={form.date_enquete_officielle} onChange={handleChange} type="date" />
            <Input label="Date validation enquête"           name="date_valid_enq"          value={form.date_valid_enq}          onChange={handleChange} type="date" />
            <Input label="Date d'établissement du CF"        name="date_etab_cf"            value={form.date_etab_cf}            onChange={handleChange} type="date" />
            <Input label="Date de demande d'immatriculation" name="date_demande_immat"      value={form.date_demande_immat}      onChange={handleChange} type="date" />
            <div className="sm:col-span-2 flex gap-3 justify-end pt-2">
              <Button type="button" variant="ghost" onClick={() => setActive(null)}>Annuler</Button>
              <Button type="submit" variant="secondary" disabled={saving}>
                <Send size={14} /> {saving ? 'Envoi…' : 'Transmettre au SCVAA'}
              </Button>
            </div>
          </form>
        </div>
      )}

      <div className="flex flex-col gap-3">
        <p className="text-sm text-neutral-500 font-semibold">{dossiers.length} dossier(s) à traiter</p>
        {dossiers.map(d => (
          <DossierCard key={d.id} dossier={d} onClick={() => setSelected(d)}
            action={<Button variant="primary" size="sm" onClick={() => handleOpen(d)}>Traiter</Button>}
          />
        ))}
        {dossiers.length === 0 && (
          <div className="text-center py-16 text-neutral-400">
            <p className="text-4xl mb-3">✅</p>
            <p className="font-semibold">Aucun dossier en attente de contrôle</p>
          </div>
        )}
      </div>
      <DossierDetail dossier={selected} onClose={() => setSelected(null)} />
      </div>
    </div>
  )
}
