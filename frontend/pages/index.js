import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const EXAMPLES = [
  "What conditions does this patient have?",
  "Summarize patients diagnosed with diabetes.",
  "Which patients are located in California?",
  "List all conditions with onset after 2020.",
];

export default function Home() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState(null);

  async function handleQuery(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 5, run_evaluation: true }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Query failed");
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleIngest() {
    setIngesting(true);
    setIngestMsg(null);
    try {
      const res = await fetch(`${API}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ingest failed");
      setIngestMsg(`Ingested ${data.chunks_stored} chunks (MLflow run: ${data.mlflow_run_id})`);
    } catch (err) {
      setIngestMsg(`Error: ${err.message}`);
    } finally {
      setIngesting(false);
    }
  }

  const scoreColor = (v) => {
    if (v === undefined || v === null) return "#6b7280";
    if (v >= 0.8) return "#4ade80";
    if (v >= 0.5) return "#facc15";
    return "#f87171";
  };

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Healthcare RAG</h1>
        <p style={styles.subtitle}>
          Retrieval-Augmented Generation over synthetic patient data (Synthea)
        </p>
        <button style={styles.ingestBtn} onClick={handleIngest} disabled={ingesting}>
          {ingesting ? "Ingesting..." : "Run Ingestion Pipeline"}
        </button>
        {ingestMsg && <p style={styles.ingestMsg}>{ingestMsg}</p>}
      </header>

      <main style={styles.main}>
        <form onSubmit={handleQuery} style={styles.form}>
          <label style={styles.label}>Ask a clinical question</label>
          <textarea
            style={styles.textarea}
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What conditions does patient John Smith have?"
          />
          <div style={styles.examples}>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                style={styles.exampleChip}
                onClick={() => setQuestion(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
          <button type="submit" style={styles.submitBtn} disabled={loading}>
            {loading ? "Searching..." : "Ask"}
          </button>
        </form>

        {error && <div style={styles.errorBox}>{error}</div>}

        {result && (
          <div style={styles.resultContainer}>
            <section style={styles.answerBox}>
              <h2 style={styles.sectionTitle}>Answer</h2>
              <p style={styles.answerText}>{result.answer}</p>
            </section>

            {result.ragas_scores && !result.ragas_scores.error && (
              <section style={styles.scoresBox}>
                <h2 style={styles.sectionTitle}>RAGAS Evaluation</h2>
                <div style={styles.badgeRow}>
                  {Object.entries(result.ragas_scores).map(([k, v]) => (
                    <div key={k} style={styles.badge}>
                      <span style={styles.badgeLabel}>{k.replace("_", " ")}</span>
                      <span style={{ ...styles.badgeValue, color: scoreColor(v) }}>
                        {typeof v === "number" ? v.toFixed(3) : v}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {result.sources && result.sources.length > 0 && (
              <section style={styles.sourcesBox}>
                <h2 style={styles.sectionTitle}>Sources ({result.sources.length})</h2>
                {result.sources.map((src, i) => (
                  <div key={i} style={styles.sourceCard}>
                    <div style={styles.sourceHeader}>
                      <span style={styles.sourceTag}>
                        {src.patient_name || src.patient_id}
                      </span>
                      <span style={styles.scoreTag}>score: {src.score}</span>
                    </div>
                    <p style={styles.sourceText}>{src.text}</p>
                  </div>
                ))}
              </section>
            )}

            <p style={styles.usageNote}>
              Tokens used: {result.usage?.input_tokens} in / {result.usage?.output_tokens} out
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    backgroundColor: "#1a1f1a",
    color: "#d4d9cc",
    fontFamily: "'Segoe UI', system-ui, sans-serif",
    padding: "0 0 4rem",
  },
  header: {
    background: "linear-gradient(135deg, #2d3a2d 0%, #1a2a1a 100%)",
    borderBottom: "1px solid #3a4a3a",
    padding: "2.5rem 2rem 2rem",
    textAlign: "center",
  },
  title: {
    margin: 0,
    fontSize: "2.2rem",
    fontWeight: 700,
    color: "#8fbc6e",
    letterSpacing: "0.04em",
  },
  subtitle: {
    color: "#8a9a80",
    marginTop: "0.5rem",
    fontSize: "0.95rem",
  },
  ingestBtn: {
    marginTop: "1rem",
    background: "#3a5a2a",
    color: "#b8d4a0",
    border: "1px solid #5a7a4a",
    borderRadius: "6px",
    padding: "0.5rem 1.4rem",
    cursor: "pointer",
    fontSize: "0.9rem",
    fontWeight: 600,
  },
  ingestMsg: {
    marginTop: "0.6rem",
    fontSize: "0.85rem",
    color: "#8fbc6e",
  },
  main: {
    maxWidth: "860px",
    margin: "2.5rem auto 0",
    padding: "0 1.5rem",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "0.8rem",
  },
  label: {
    fontSize: "0.95rem",
    fontWeight: 600,
    color: "#a0b890",
  },
  textarea: {
    background: "#232b23",
    border: "1px solid #3a4a3a",
    borderRadius: "8px",
    color: "#d4d9cc",
    fontSize: "1rem",
    padding: "0.8rem",
    resize: "vertical",
    outline: "none",
  },
  examples: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.5rem",
  },
  exampleChip: {
    background: "#2a3a2a",
    border: "1px solid #4a5a3a",
    borderRadius: "20px",
    color: "#9ab88a",
    cursor: "pointer",
    fontSize: "0.8rem",
    padding: "0.3rem 0.8rem",
  },
  submitBtn: {
    alignSelf: "flex-start",
    background: "#4a7a30",
    border: "none",
    borderRadius: "8px",
    color: "#fff",
    cursor: "pointer",
    fontSize: "1rem",
    fontWeight: 700,
    padding: "0.7rem 2rem",
  },
  errorBox: {
    marginTop: "1.5rem",
    background: "#3a1a1a",
    border: "1px solid #7a2a2a",
    borderRadius: "8px",
    color: "#f87171",
    padding: "1rem",
  },
  resultContainer: {
    marginTop: "2rem",
    display: "flex",
    flexDirection: "column",
    gap: "1.5rem",
  },
  answerBox: {
    background: "#1e271e",
    border: "1px solid #3a5a2a",
    borderRadius: "10px",
    padding: "1.4rem",
  },
  sectionTitle: {
    margin: "0 0 0.8rem",
    fontSize: "1rem",
    fontWeight: 700,
    color: "#8fbc6e",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  answerText: {
    lineHeight: 1.7,
    margin: 0,
    whiteSpace: "pre-wrap",
  },
  scoresBox: {
    background: "#1e271e",
    border: "1px solid #3a4a2a",
    borderRadius: "10px",
    padding: "1.2rem 1.4rem",
  },
  badgeRow: {
    display: "flex",
    gap: "1rem",
    flexWrap: "wrap",
  },
  badge: {
    background: "#252f25",
    border: "1px solid #3a4a3a",
    borderRadius: "8px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "0.6rem 1rem",
    minWidth: "120px",
  },
  badgeLabel: {
    fontSize: "0.75rem",
    color: "#8a9a80",
    textTransform: "capitalize",
    marginBottom: "0.2rem",
  },
  badgeValue: {
    fontSize: "1.4rem",
    fontWeight: 700,
  },
  sourcesBox: {
    display: "flex",
    flexDirection: "column",
    gap: "0.8rem",
  },
  sourceCard: {
    background: "#1e271e",
    border: "1px solid #2a3a2a",
    borderRadius: "8px",
    padding: "0.9rem 1.1rem",
  },
  sourceHeader: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "0.5rem",
  },
  sourceTag: {
    background: "#2d3d20",
    borderRadius: "4px",
    color: "#8fbc6e",
    fontSize: "0.8rem",
    fontWeight: 600,
    padding: "0.2rem 0.6rem",
  },
  scoreTag: {
    color: "#6b7a5b",
    fontSize: "0.8rem",
  },
  sourceText: {
    fontSize: "0.88rem",
    lineHeight: 1.6,
    margin: 0,
    color: "#b0baa0",
  },
  usageNote: {
    color: "#505a48",
    fontSize: "0.8rem",
    textAlign: "right",
  },
};
