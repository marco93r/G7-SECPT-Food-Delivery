import type { PropsWithChildren } from "react";
import "./layout.css";

export function PageShell({ children }: PropsWithChildren) {
  return (
    <div className="page-shell">
      <header className="page-shell__hero">
        <div>
          <p className="eyebrow">miFOS</p>
          <h1>Food Delivery Control Center</h1>
          <p className="lead">
            Verwalte Menüs, stelle Orders zusammen und beobachte Saga-Status in
            Echtzeit – alles in einer modernen Oberfläche.
          </p>
          <div className="page-shell__actions">
            <a
              className="page-shell__link-button"
              href="https://localhost:8080/logs"
              target="_blank"
              rel="noreferrer"
            >
              📄 Logs (admin/admin)
            </a>
          </div>
        </div>
      </header>
      <main className="page-shell__content">{children}</main>
      <footer className="page-shell__footer">
        <small>© {new Date().getFullYear()} miFOS Demo – built with React + Vite</small>
      </footer>
    </div>
  );
}
