import React, { useState } from 'react'

export default function Voting() {
  const [selections, setSelections] = useState<Record<string, string>>({})

  const positions = [
    {
      id: 'president',
      title: 'President',
      candidates: [
        { id: 'alice', name: 'Alice Johnson', gender: 'Female' },
        { id: 'bob', name: 'Bob Smith', gender: 'Male' },
        { id: 'carol', name: 'Carol Lee', gender: 'Female' }
      ]
    },
    {
      id: 'secretary',
      title: 'Secretary',
      candidates: [
        { id: 'david', name: 'David Kim', gender: 'Male' },
        { id: 'eve', name: 'Eve Martinez', gender: 'Female' }
      ]
    }
  ]

  const handleVoteChange = (positionId: string, candidateId: string) => {
    setSelections(prev => ({
      ...prev,
      [positionId]: candidateId
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Vote submitted:', selections)
  }

  return (
    <div className="page voting-page">
      <div className="content-container">
        <div className="page-header">
          <h1 className="page-title">Cast Your Vote</h1>
          <p className="page-subtitle">Select your preferred candidates for each position. Your vote is private and securely encrypted.</p>
        </div>

        <div className="card">
          <div className="card-body">
            <form onSubmit={handleSubmit} className="form-grid">
              <p className="text-muted">Please select your candidates for each position</p>

              <div className="position-list">
                {positions.map((pos) => (
                  <section className="position-section" key={pos.id} aria-labelledby={`pos-${pos.id}`}>
                    <h3 id={`pos-${pos.id}`} className="position-title">{pos.title}</h3>
                    <table className="candidate-table" role="grid" aria-label={`Candidates for ${pos.title}`}>
                      <thead>
                        <tr>
                          <th scope="col">Image</th>
                          <th scope="col">Name</th>
                          <th scope="col">Gender</th>
                          <th scope="col">Select</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pos.candidates.map((c) => {
                          const inputId = `${pos.id}-${c.id}`
                          const checked = selections[pos.id] === c.id
                          const initials = c.name.split(' ').map(n => n[0]).slice(0,2).join('').toUpperCase()
                          return (
                            <tr key={c.id} className={checked ? 'row-selected' : ''}>
                              <td className="candidate-cell-image">
                                <div className="candidate-avatar" aria-hidden="true">{initials}</div>
                              </td>
                              <td className="candidate-cell-name">
                                <span className="candidate-name">{c.name}</span>
                              </td>
                              <td className="candidate-cell-gender">
                                <span className="candidate-gender">{c.gender}</span>
                              </td>
                              <td className="candidate-cell-select">
                                <input
                                  type="checkbox"
                                  id={inputId}
                                  name={pos.id}
                                  value={c.id}
                                  checked={checked}
                                  onChange={() => handleVoteChange(pos.id, c.id)}
                                  className="voter-checkbox"
                                  aria-label={`Select ${c.name}`}
                                />
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </section>
                ))}
              </div>

              {/* Actions */}
              <div className="form-actions">
                <button type="submit" className="btn btn-primary btn-sm">Submit Vote</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
