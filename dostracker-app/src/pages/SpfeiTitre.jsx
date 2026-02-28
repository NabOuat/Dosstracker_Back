import { useEffect, useState } from 'react'
import { Award } from 'lucide-react'
import { getDossiers, updateSpfeiTitre } from '../api/dossiers'
import DossierCard from '../components/DossierCard'
import DossierDetail from '../components/DossierDetail'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Alert from '../components/ui/Alert'

export default function SpfeiTitre() {
  const [dossiers, setDossiers] = useState([])
  const [active,   setActive]   = useState(null)
  const [form,     setForm]     = useState({ conservation: '', numero_tf: '' })
  const [selected, setSelected] = useState(null)
  const [saving,   setSaving]   = useState(false)
  const [success,  setSuccess]  = useState('')
  const [error,    setError]    = useState('')

  const load = () => getDossiers('SPFEI_TITRE').then(setDossiers)
  useEffect(() => { load() }, [])

  const handleOpen = d => { setActive(d); setForm({ conservation: d.conservation ?? '', numero_tf: d.numero_tf ?? '' }) }
  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async e => {
    e.preventDefault()
    if (!form.conservation.trim() || !form.numero_tf.trim()) {
      setError('La conservation et le numéro de titre sont obligatoires.'); return
    }
    setSaving(true); setError('')
    try {
      await updateSpfeiTitre(active.id, form)
      setSuccess('Titre Foncier attribué. Dossier transmis à la Conservation. SMS envoyé au propriétaire.')
      setActive(null); await load()
      setTimeout(() => setSuccess(''), 5000)
    } finally { setSaving(false) }
  }

  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
      <span className="section-label">Service SPFEI</span>
      <h1 className="font-display font-bold text-2xl sm:text-3xl lg:text-4xl text-neutral-900 mb-2">
        Attribution du <span style={{ color: 'var(--ci-orange)' }}>Titre Foncier</span>
      </h1>
      <p className="text-sm text-neutral-500 mb-6">
        Attribuez le numéro de titre foncier et transmettez à la Conservation Foncière.
      </p>

      {success && <Alert variant="success" className="mb-4">{success}</Alert>}

      {active && (
        <div className="bg-white rounded-lg p-6 mb-6" style={{ boxShadow: 'var(--shadow-md)', borderLeft: '4px solid var(--ci-orange)' }}>
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-md flex items-center justify-center" style={{ background: 'var(--ci-orange-pale)' }}>
              <Award size={20} style={{ color: 'var(--ci-orange)' }} />
            </div>
            <div>
              <h2 className="font-display font-bold text-base text-neutral-800">{active.numero}</h2>
              <p className="text-sm text-neutral-500">{active.demandeur}</p>
            </div>
          </div>
          {error && <Alert variant="error" className="mb-4">{error}</Alert>}
          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Conservation"    name="conservation" required value={form.conservation} onChange={handleChange} placeholder="ex : Conservation d'Abidjan" />
            <Input label="N° Titre Foncier" name="numero_tf"    required value={form.numero_tf}    onChange={handleChange} placeholder="ex : TF-2026-0001" />
            <div className="sm:col-span-2 flex gap-3 justify-end pt-2">
              <Button type="button" variant="ghost" onClick={() => setActive(null)}>Annuler</Button>
              <Button type="submit" variant="primary" disabled={saving}>
                <Award size={15} /> {saving ? 'Attribution…' : 'Attribuer et envoyer à la Conservation'}
              </Button>
            </div>
          </form>
        </div>
      )}

      <div className="flex flex-col gap-3">
        <p className="text-sm text-neutral-500 font-semibold">{dossiers.length} dossier(s) conforme(s) en attente</p>
        {dossiers.map(d => (
          <DossierCard key={d.id} dossier={d} onClick={() => setSelected(d)}
            action={<Button variant="primary" size="sm" onClick={() => handleOpen(d)}><Award size={13} /> Attribuer</Button>}
          />
        ))}
        {dossiers.length === 0 && (
          <div className="text-center py-16 text-neutral-400">
            <p className="text-4xl mb-3">🏆</p><p className="font-semibold">Aucun dossier en attente d'attribution</p>
          </div>
        )}
      </div>
      <DossierDetail dossier={selected} onClose={() => setSelected(null)} />
      </div>
    </div>
  )
}
