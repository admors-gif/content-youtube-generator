"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Icon from "@/components/Icon";
import { isAdminUser } from "@/lib/admin";
import { authedFetch, getApiBase } from "@/lib/apiClient";
import { useAuth } from "@/context/AuthContext";

const KNOWLEDGE_ENABLED = process.env.NEXT_PUBLIC_CONTENT_FACTORY_KNOWLEDGE_ENABLED !== "false";

const TABS = [
  { id: "books", label: "Libros" },
  { id: "search", label: "Buscar" },
  { id: "detail", label: "Detalle" },
  { id: "ingest", label: "Ingesta" },
];

function compactNumber(value) {
  return new Intl.NumberFormat("es-MX", { notation: "compact", maximumFractionDigits: 1 }).format(Number(value || 0));
}

function formatDate(value) {
  if (!value) return "Sin datos";
  try {
    return new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  } catch {
    return String(value);
  }
}

function buttonStyle(active) {
  return {
    borderColor: active ? "var(--ember)" : "var(--rule-1)",
    background: active ? "var(--ember-tint)" : "var(--ink-1)",
    color: active ? "var(--ember)" : "var(--paper-dim)",
  };
}

function Notice({ error, notice }) {
  if (!error && !notice) return null;
  return (
    <div
      className="cf-card"
      style={{
        padding: "var(--s-4)",
        marginBottom: "var(--s-5)",
        borderColor: error ? "var(--bad)" : "var(--ok)",
        color: error ? "var(--bad)" : "var(--ok)",
      }}
    >
      {error || notice}
    </div>
  );
}

function StatCard({ label, value, sub }) {
  return (
    <div className="cf-card" style={{ padding: "var(--s-4)" }}>
      <div className="cf-mono-sm" style={{ marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: "var(--font-display)", fontSize: 34, fontWeight: 800, lineHeight: 1 }}>
        {value}
      </div>
      {sub && <div className="cf-caption" style={{ marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function BookCard({ book, selected, onSelect }) {
  return (
    <article
      className="cf-card"
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect();
        }
      }}
      style={{
        padding: "var(--s-5)",
        cursor: "pointer",
        borderColor: selected ? "var(--ember)" : "var(--rule-1)",
        boxShadow: selected ? "var(--shadow-ember)" : "var(--shadow-1)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
            <span className="cf-badge cf-badge--neutral">{book.category || "General"}</span>
            <span className="cf-badge cf-badge--ok">{compactNumber(book.chunksCount)} chunks</span>
          </div>
          <h2 className="cf-h3" style={{ margin: "0 0 8px", lineHeight: 1.2 }}>
            {book.title}
          </h2>
          <p className="cf-body" style={{ margin: 0, lineHeight: 1.5 }}>
            {book.sample || "Sin muestra disponible. Sincroniza el indice para refrescar datos."}
          </p>
        </div>
        <Icon name="chevronRight" size={18} style={{ color: "var(--paper-mute)" }} />
      </div>
    </article>
  );
}

function ChunkCard({ item, showScore = false }) {
  return (
    <article className="cf-card" style={{ padding: "var(--s-5)" }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <span className="cf-badge cf-badge--neutral">{item.category || "General"}</span>
        {showScore && item.score != null && (
          <span className="cf-badge cf-badge--starter">score {Number(item.score).toFixed(3)}</span>
        )}
      </div>
      <h3 className="cf-h4" style={{ marginBottom: 10 }}>{item.title || "Fragmento"}</h3>
      <p className="cf-body" style={{ margin: 0, lineHeight: 1.6 }}>{item.content}</p>
    </article>
  );
}

export default function KnowledgePage() {
  const { user, profile, loading: authLoading } = useAuth();
  const admin = isAdminUser(user, profile);
  const [activeTab, setActiveTab] = useState("books");
  const [summary, setSummary] = useState(null);
  const [books, setBooks] = useState([]);
  const [selectedBook, setSelectedBook] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [nextCursor, setNextCursor] = useState("");
  const [categories, setCategories] = useState([]);
  const [filters, setFilters] = useState({ q: "", category: "all" });
  const [search, setSearch] = useState({ query: "", category: "all", bookTitle: "", limit: 6 });
  const [searchResults, setSearchResults] = useState([]);
  const [ingest, setIngest] = useState({ title: "", category: "General", reindex: false, file: null });
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const pollRef = useRef(null);

  const loadSummary = useCallback(async () => {
    const res = await authedFetch(user, `${getApiBase()}/knowledge/summary`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.error || "No se pudo leer la base de conocimiento.");
    setSummary(data);
    setCategories(data.categories || []);
  }, [user]);

  const loadBooks = useCallback(async () => {
    const params = new URLSearchParams();
    if (filters.category !== "all") params.set("category", filters.category);
    if (filters.q.trim()) params.set("q", filters.q.trim());
    params.set("limit", "120");
    const res = await authedFetch(user, `${getApiBase()}/knowledge/books?${params.toString()}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron leer los libros.");
    setBooks(data.books || []);
  }, [user, filters.category, filters.q]);

  const loadAll = useCallback(async () => {
    if (!user || !admin || !KNOWLEDGE_ENABLED) return;
    setLoading(true);
    setError("");
    try {
      await loadSummary();
      await loadBooks();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user, admin, loadSummary, loadBooks]);

  useEffect(() => {
    if (authLoading || !user || !admin || !KNOWLEDGE_ENABLED) return;
    const timeout = setTimeout(() => {
      loadAll();
    }, 0);
    return () => clearTimeout(timeout);
  }, [authLoading, user, admin, loadAll]);

  useEffect(() => {
    if (!user || !admin || !KNOWLEDGE_ENABLED) return;
    const timeout = setTimeout(() => {
      loadBooks().catch((err) => setError(err.message));
    }, 250);
    return () => clearTimeout(timeout);
  }, [filters, user, admin, loadBooks]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const totals = useMemo(() => ({
    books: summary?.booksCount || books.length,
    chunks: summary?.chunksCount || 0,
    categories: categories.length,
    qdrant: summary?.qdrant?.ok ? "online" : "revisar",
  }), [summary, books.length, categories.length]);

  const syncIndex = async () => {
    setSyncing(true);
    setError("");
    setNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/knowledge/sync-index`, { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo sincronizar Qdrant.");
      setNotice(`Indice sincronizado: ${data.booksCount || 0} libros.`);
      await loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  const openBook = async (book, append = false) => {
    setSelectedBook(book);
    setActiveTab("detail");
    setError("");
    try {
      const params = new URLSearchParams({ limit: "12" });
      if (append && nextCursor) params.set("cursor", nextCursor);
      const res = await authedFetch(user, `${getApiBase()}/knowledge/books/${book.bookId}/chunks?${params.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudieron leer fragmentos.");
      setChunks((current) => (append ? [...current, ...(data.chunks || [])] : data.chunks || []));
      setNextCursor(data.nextCursor || "");
    } catch (err) {
      setError(err.message);
    }
  };

  const runSearch = async () => {
    if (search.query.trim().length < 3) {
      setError("Escribe un tema de al menos 3 caracteres.");
      return;
    }
    setSearching(true);
    setError("");
    setNotice("");
    try {
      const res = await authedFetch(user, `${getApiBase()}/knowledge/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: search.query,
          category: search.category,
          bookTitle: search.bookTitle,
          limit: Number(search.limit || 6),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo buscar en Qdrant.");
      setSearchResults(data.items || []);
      setNotice(`${data.items?.length || 0} fragmento(s) encontrados.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSearching(false);
    }
  };

  const pollJob = (jobId) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await authedFetch(user, `${getApiBase()}/knowledge/ingest/${jobId}`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || data.error || "No se pudo leer el job.");
        setJob(data.job);
        if (["completed", "failed"].includes(data.job?.status)) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          if (data.job.status === "completed") {
            setNotice(data.job.duplicate ? "El libro ya existia; no se duplico." : "Libro indexado en Qdrant.");
            await loadAll();
          } else {
            setError(data.job.error || "La ingesta fallo.");
          }
        }
      } catch (err) {
        setError(err.message);
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }, 2500);
  };

  const submitIngest = async (event) => {
    event.preventDefault();
    if (!ingest.file) {
      setError("Selecciona un PDF.");
      return;
    }
    setUploading(true);
    setError("");
    setNotice("");
    try {
      const form = new FormData();
      form.append("file", ingest.file);
      form.append("title", ingest.title);
      form.append("category", ingest.category || "General");
      form.append("reindex", ingest.reindex ? "true" : "false");
      const res = await authedFetch(user, `${getApiBase()}/knowledge/ingest/pdf`, {
        method: "POST",
        body: form,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || "No se pudo iniciar ingesta.");
      setJob(data.job);
      setNotice("Ingesta en cola.");
      pollJob(data.job.jobId);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  if (!KNOWLEDGE_ENABLED) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
        <Icon name="lock" size={30} style={{ margin: "0 auto 16px", color: "var(--paper-mute)" }} />
        <h1 className="cf-h2" style={{ margin: 0 }}>Base de conocimiento desactivada</h1>
      </div>
    );
  }

  if (!authLoading && !admin) {
    return (
      <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
        <Icon name="lock" size={30} style={{ margin: "0 auto 16px", color: "var(--paper-mute)" }} />
        <h1 className="cf-h2" style={{ margin: 0 }}>Acceso admin</h1>
      </div>
    );
  }

  return (
    <div>
      <header className="cf-fade" style={{ marginBottom: "var(--s-6)" }}>
        <div className="cf-eyebrow" style={{ color: "var(--ember)", marginBottom: 10 }}>
          BASE DE CONOCIMIENTO
        </div>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 18, flexWrap: "wrap" }}>
          <div>
            <h1 className="cf-h1" style={{ margin: 0 }}>Libros y Qdrant</h1>
            <p className="cf-body" style={{ maxWidth: 720, margin: "12px 0 0" }}>
              Visualiza libros vectorizados, busca fragmentos por tema e ingesta PDFs para enriquecer futuros agentes.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button className="cf-btn cf-btn--secondary" onClick={loadAll} disabled={loading} type="button">
              <Icon name="refresh" size={16} />
              {loading ? "Cargando" : "Actualizar"}
            </button>
            <button className="cf-btn cf-btn--primary" onClick={syncIndex} disabled={syncing} type="button">
              <Icon name="download" size={16} />
              {syncing ? "Sincronizando" : "Sincronizar indice"}
            </button>
          </div>
        </div>
      </header>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: "var(--s-5)" }}>
        <StatCard label="Libros" value={compactNumber(totals.books)} sub="indexados" />
        <StatCard label="Chunks" value={compactNumber(totals.chunks)} sub={summary?.collection || "valtyk_knowledge"} />
        <StatCard label="Categorias" value={compactNumber(totals.categories)} sub="detectadas" />
        <StatCard label="Qdrant" value={totals.qdrant} sub={summary?.qdrant?.status || summary?.qdrant?.error || ""} />
      </section>

      <Notice error={error} notice={notice} />

      <section className="cf-card cf-fade cf-fade--1" style={{ padding: "var(--s-5)", marginBottom: "var(--s-5)" }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className="cf-btn cf-btn--sm"
              style={buttonStyle(activeTab === tab.id)}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "books" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Categoria</div>
              <select
                className="cf-input"
                value={filters.category}
                onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}
              >
                <option value="all">Todas</option>
                {categories.map((category) => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
            </label>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Buscar libro</div>
              <input
                className="cf-input"
                value={filters.q}
                placeholder="Titulo, categoria o muestra"
                onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))}
              />
            </label>
          </div>
        )}

        {activeTab === "search" && (
          <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 1fr) repeat(auto-fit, minmax(180px, 220px))", gap: 12, alignItems: "end" }}>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Tema</div>
              <input
                className="cf-input"
                value={search.query}
                placeholder="apego evitativo, contacto cero, liderazgo..."
                onChange={(event) => setSearch((current) => ({ ...current, query: event.target.value }))}
                onKeyDown={(event) => {
                  if (event.key === "Enter") runSearch();
                }}
              />
            </label>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Categoria</div>
              <select className="cf-input" value={search.category} onChange={(event) => setSearch((current) => ({ ...current, category: event.target.value }))}>
                <option value="all">Todas</option>
                {categories.map((category) => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
            </label>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Libro exacto</div>
              <input
                className="cf-input"
                value={search.bookTitle}
                placeholder="Opcional"
                onChange={(event) => setSearch((current) => ({ ...current, bookTitle: event.target.value }))}
              />
            </label>
            <button className="cf-btn cf-btn--primary" onClick={runSearch} disabled={searching} type="button">
              <Icon name="search" size={16} />
              {searching ? "Buscando" : "Buscar"}
            </button>
          </div>
        )}

        {activeTab === "ingest" && (
          <form onSubmit={submitIngest} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, alignItems: "end" }}>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>PDF</div>
              <input
                className="cf-input"
                type="file"
                accept="application/pdf,.pdf"
                onChange={(event) => setIngest((current) => ({ ...current, file: event.target.files?.[0] || null }))}
              />
            </label>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Titulo</div>
              <input
                className="cf-input"
                value={ingest.title}
                placeholder="Nombre del libro"
                onChange={(event) => setIngest((current) => ({ ...current, title: event.target.value }))}
              />
            </label>
            <label>
              <div className="cf-mono-sm" style={{ marginBottom: 8 }}>Categoria</div>
              <input
                className="cf-input"
                value={ingest.category}
                placeholder="Ej. Psicologia y Relaciones"
                onChange={(event) => setIngest((current) => ({ ...current, category: event.target.value }))}
              />
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 10, minHeight: 46 }}>
              <input
                type="checkbox"
                checked={ingest.reindex}
                onChange={(event) => setIngest((current) => ({ ...current, reindex: event.target.checked }))}
              />
              <span className="cf-caption">Reindexar si ya existe</span>
            </label>
            <button className="cf-btn cf-btn--primary" type="submit" disabled={uploading}>
              <Icon name="uploadCloud" size={16} />
              {uploading ? "Subiendo" : "Subir PDF"}
            </button>
          </form>
        )}
      </section>

      {activeTab === "books" && (
        <section style={{ display: "grid", gap: 14 }}>
          {loading && (
            <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
              <Icon name="refresh" size={24} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
              <div className="cf-body">Cargando libros.</div>
            </div>
          )}
          {!loading && books.length === 0 && (
            <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
              <Icon name="bookOpen" size={28} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
              <h2 className="cf-h3" style={{ margin: 0 }}>Sin libros en el indice</h2>
            </div>
          )}
          {books.map((book) => (
            <BookCard key={book.bookId} book={book} selected={selectedBook?.bookId === book.bookId} onSelect={() => openBook(book)} />
          ))}
        </section>
      )}

      {activeTab === "detail" && (
        <section style={{ display: "grid", gap: 14 }}>
          {!selectedBook && (
            <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
              <Icon name="bookOpen" size={28} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
              <h2 className="cf-h3" style={{ margin: 0 }}>Selecciona un libro</h2>
            </div>
          )}
          {selectedBook && (
            <>
              <div className="cf-card" style={{ padding: "var(--s-5)" }}>
                <div className="cf-mono-sm" style={{ marginBottom: 10 }}>DETALLE</div>
                <h2 className="cf-h2" style={{ margin: 0 }}>{selectedBook.title}</h2>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
                  <span className="cf-badge cf-badge--neutral">{selectedBook.category}</span>
                  <span className="cf-badge cf-badge--ok">{compactNumber(selectedBook.chunksCount)} chunks</span>
                  <span className="cf-badge cf-badge--neutral">Sync {formatDate(selectedBook.lastSyncedAt)}</span>
                </div>
              </div>
              {chunks.map((chunk) => <ChunkCard key={chunk.pointId} item={chunk} />)}
              {nextCursor && (
                <button className="cf-btn cf-btn--secondary" onClick={() => openBook(selectedBook, true)} type="button">
                  <Icon name="chevronDown" size={16} />
                  Cargar mas fragmentos
                </button>
              )}
            </>
          )}
        </section>
      )}

      {activeTab === "search" && (
        <section style={{ display: "grid", gap: 14 }}>
          {searchResults.length === 0 && (
            <div className="cf-card" style={{ padding: "var(--s-7)", textAlign: "center" }}>
              <Icon name="search" size={28} style={{ margin: "0 auto 14px", color: "var(--paper-mute)" }} />
              <h2 className="cf-h3" style={{ margin: 0 }}>Busca un tema dentro de tus libros</h2>
            </div>
          )}
          {searchResults.map((item) => <ChunkCard key={item.pointId} item={item} showScore />)}
        </section>
      )}

      {activeTab === "ingest" && job && (
        <section className="cf-card" style={{ padding: "var(--s-5)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
            <div>
              <div className="cf-mono-sm" style={{ marginBottom: 10 }}>JOB DE INGESTA</div>
              <h2 className="cf-h3" style={{ margin: 0 }}>{job.title}</h2>
              <div className="cf-caption" style={{ marginTop: 8 }}>{job.fileName}</div>
            </div>
            <span className={`cf-badge ${job.status === "failed" ? "cf-badge--bad" : job.status === "completed" ? "cf-badge--ok" : "cf-badge--warn"}`}>
              {job.status}
            </span>
          </div>
          <div style={{ height: 8, borderRadius: 999, overflow: "hidden", background: "var(--ink-3)", marginTop: 18 }}>
            <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, Number(job.progress || 0)))}%`, background: "var(--ember)" }} />
          </div>
          <div className="cf-caption" style={{ marginTop: 10 }}>
            {job.progress || 0}% · {compactNumber(job.chunksCount || 0)} chunks
          </div>
          {job.error && <div className="cf-caption" style={{ color: "var(--bad)", marginTop: 10 }}>{job.error}</div>}
        </section>
      )}
    </div>
  );
}
