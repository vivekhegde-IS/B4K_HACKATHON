import './index.css'

function App() {
  return (
    <main className="app-shell">
      <section className="welcome-panel">
        <p className="eyebrow">RetailMate</p>
        <h1>Your multilingual retail assistant</h1>
        <p className="intro">The kiosk experience is ready for the next integration step.</p>
        <div className="status-row" role="status">
          <span className="status-dot" />
          Services are being connected
        </div>
      </section>
    </main>
  )
}

export default App