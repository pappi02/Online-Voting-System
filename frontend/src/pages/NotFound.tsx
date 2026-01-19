import React from 'react'

export default function NotFound() {
  return (
    <div className="page not-found-page">
      <div className="content-container">
        <div className="page-header">
          <h1 className="page-title">Page Not Found</h1>
          <p className="page-subtitle">The page you're looking for doesn't exist or may have been moved</p>
        </div>

        <div className="card">
          <div className="card-body">
            <p className="text-muted">Use the navigation above to return to the home page or visit the voting section.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
