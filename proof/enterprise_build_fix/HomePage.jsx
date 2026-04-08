import React from 'react';
import { Link } from 'react-router-dom';

export default function HomePage() {
  return (
    <section className="panel">
      <div className="eyebrow">Launch surface</div>
      <h2>Mission control</h2>
      <p className="lead">Helios Aegis Command unifies CRM, quoting, project delivery, policy review, audit visibility, and operator assist without rendering the raw prompt as product content.</p>
      <div className="button-row">
        <Link className="primary-button" to="/dashboard">Open command view</Link>
        <Link className="ghost-button" to="/quotes">Review protected quotes</Link>
        <Link className="ghost-button" to="/policy">Inspect policy approvals</Link>
      </div>
    </section>
  );
}
