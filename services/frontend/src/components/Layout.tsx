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
        </div>
      </header>
      <main className="page-shell__content">{children}</main>
      <footer className="page-shell__footer">
        <small>© {new Date().getFullYear()} miFOS Demo – built with React + Vite</small>
      </footer>
    </div>
  );
}
