import { useState } from 'react'
import { ChevronLeft, Save } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button, Input, Alert } from '../components/ui'

export default function NouveauDossier() {
  const [form, setForm] = useState({ nom: '', prenom: '', type: '', reference: '' })
  const [saved, setSaved] = useState(false)

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = e => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="max-w-[700px] mx-auto px-4 sm:px-6 py-8">

      {/* Retour */}
      <Link to="/dossiers" className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-orange mb-6 no-underline transition-colors" style={{ '--tw-text-opacity': 1 }}>
        <ChevronLeft size={16} />
        Retour aux dossiers
      </Link>

      <span className="section-label">Création</span>
      <h1 className="font-display font-bold text-2xl sm:text-3xl text-neutral-900 mb-2">
        Nouveau <span style={{ color: 'var(--ci-orange)' }}>dossier</span>
      </h1>
      <p className="text-neutral-500 text-sm mb-8">
        Remplissez les informations pour créer un nouveau dossier.
      </p>

      {saved && (
        <Alert variant="success" className="mb-6">
          Dossier créé avec succès !
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="bg-white rounded-lg p-6 sm:p-8 flex flex-col gap-5" style={{ boxShadow: 'var(--shadow-md)' }}>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <Input
            label="Nom"
            name="nom"
            required
            placeholder="ex : Kouassi"
            value={form.nom}
            onChange={handleChange}
          />
          <Input
            label="Prénom"
            name="prenom"
            required
            placeholder="ex : Emmanuel"
            value={form.prenom}
            onChange={handleChange}
          />
        </div>

        <div>
          <label className="text-[0.78rem] font-bold text-neutral-700 block mb-1">
            Type de dossier <span style={{ color: 'var(--ci-orange)' }}>*</span>
          </label>
          <select
            name="type"
            value={form.type}
            onChange={handleChange}
            required
            className="input-field"
          >
            <option value="">Sélectionner un type…</option>
            <option value="SPFEI">SPFEI</option>
            <option value="SCVAA">SCVAA</option>
            <option value="COURRIER">Courrier</option>
          </select>
        </div>

        <Input
          label="Référence"
          name="reference"
          placeholder="ex : REF-2026-0001"
          hint="Laissez vide pour générer automatiquement"
          value={form.reference}
          onChange={handleChange}
        />

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <Button type="submit" variant="primary" className="flex-1 justify-center">
            <Save size={16} />
            Enregistrer le dossier
          </Button>
          <Link to="/dossiers" className="flex-1 sm:flex-none">
            <Button type="button" variant="ghost" className="w-full justify-center">
              Annuler
            </Button>
          </Link>
        </div>
      </form>
    </div>
  )
}
