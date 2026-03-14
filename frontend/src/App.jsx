import { useState } from "react";

const API = "http://localhost:8000";

export default function App() {
  const [courses, setCourses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [language, setLanguage] = useState("python");
  const [assignmentType, setAssignmentType] = useState("auto");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");

  async function fetchCourses() {
    setLoading("courses"); setError(""); setCourses([]); setAssignments([]); setResult(null);
    try {
      const res = await fetch(`${API}/courses`);
      const data = await res.json();
      setCourses(data.courses || []);
    } catch { setError("❌ Could not connect to backend. Is api.py running?"); }
    setLoading("");
  }

  async function fetchAssignments(courseId) {
    setSelectedCourse(courseId); setAssignments([]); setSelectedAssignment(null); setResult(null);
    setLoading("assignments"); setError("");
    try {
      const res = await fetch(`${API}/courses/${courseId}/assignments`);
      const data = await res.json();
      setAssignments(data.assignments || []);
    } catch { setError("❌ Failed to fetch assignments."); }
    setLoading("");
  }

  async function handleCreate() {
    if (!selectedCourse) return;
    setLoading("create"); setError(""); setResult(null);
    try {
      const res = await fetch(`${API}/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          course_id: selectedCourse,
          assignment_id: selectedAssignment || undefined,
          language,
          assignment_type: assignmentType === "auto" ? undefined : assignmentType,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Unknown error");
      setResult(data);
    } catch (e) { setError(`❌ ${e.message}`); }
    setLoading("");
  }

  const btn = "px-4 py-2 rounded-lg font-medium text-sm transition-all";

  return (
    <div style={{ fontFamily: "Inter, sans-serif", background: "#0f172a", minHeight: "100vh", color: "#e2e8f0", padding: "2rem" }}>
      <div style={{ maxWidth: 640, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ marginBottom: "2rem" }}>
          <h1 style={{ fontSize: "1.8rem", fontWeight: 700, color: "#f8fafc", margin: 0 }}>
            🎓 Canvas Assignment Agent
          </h1>
          <p style={{ color: "#94a3b8", marginTop: 6 }}>
            Automatically create GitHub repos or Notion pages from your Canvas assignments.
          </p>
        </div>

        {/* Step 1 - Load Courses */}
        <Section title="Step 1 — Load Your Courses">
          <button className={btn} onClick={fetchCourses} disabled={!!loading}
            style={{ background: "#6366f1", color: "white", opacity: loading ? 0.6 : 1, border: "none", cursor: "pointer", padding: "10px 20px", borderRadius: 8 }}>
            {loading === "courses" ? "Loading..." : "🔄 Fetch Courses"}
          </button>
          {courses.length > 0 && (
            <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: 8 }}>
              {courses.map(c => (
                <button key={c.id} onClick={() => fetchAssignments(c.id)}
                  style={{
                    textAlign: "left", padding: "10px 14px", borderRadius: 8, border: "1px solid",
                    borderColor: selectedCourse === c.id ? "#6366f1" : "#334155",
                    background: selectedCourse === c.id ? "#1e1b4b" : "#1e293b",
                    color: "#e2e8f0", cursor: "pointer", fontSize: 14
                  }}>
                  <span style={{ color: "#94a3b8", marginRight: 8 }}>#{c.id}</span>{c.name}
                </button>
              ))}
            </div>
          )}
        </Section>

        {/* Step 2 - Pick Assignment */}
        {assignments.length > 0 && (
          <Section title="Step 2 — Pick an Assignment">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <button onClick={() => setSelectedAssignment(null)}
                style={{
                  textAlign: "left", padding: "10px 14px", borderRadius: 8, border: "1px solid",
                  borderColor: selectedAssignment === null ? "#6366f1" : "#334155",
                  background: selectedAssignment === null ? "#1e1b4b" : "#1e293b",
                  color: "#e2e8f0", cursor: "pointer", fontSize: 14
                }}>
                ⏭ Next upcoming assignment (auto)
              </button>
              {assignments.map(a => (
                <button key={a.id} onClick={() => setSelectedAssignment(a.id)}
                  style={{
                    textAlign: "left", padding: "10px 14px", borderRadius: 8, border: "1px solid",
                    borderColor: selectedAssignment === a.id ? "#6366f1" : "#334155",
                    background: selectedAssignment === a.id ? "#1e1b4b" : "#1e293b",
                    color: "#e2e8f0", cursor: "pointer", fontSize: 14
                  }}>
                  <span style={{ color: "#94a3b8", marginRight: 8 }}>#{a.id}</span>{a.name}
                  {a.due_at && <span style={{ color: "#64748b", marginLeft: 8, fontSize: 12 }}>Due: {new Date(a.due_at).toLocaleDateString()}</span>}
                </button>
              ))}
            </div>
          </Section>
        )}

        {/* Step 3 - Options */}
        {selectedCourse && (
          <Section title="Step 3 — Options">
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <div>
                <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Language</label>
                <select value={language} onChange={e => setLanguage(e.target.value)}
                  style={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", padding: "8px 12px", borderRadius: 8, fontSize: 14 }}>
                  {["python", "java", "javascript", "cpp"].map(l => <option key={l}>{l}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Assignment Type</label>
                <select value={assignmentType} onChange={e => setAssignmentType(e.target.value)}
                  style={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", padding: "8px 12px", borderRadius: 8, fontSize: 14 }}>
                  <option value="auto">Auto-detect</option>
                  <option value="coding">Coding → GitHub</option>
                  <option value="writing">Writing → Notion</option>
                </select>
              </div>
            </div>

            <button onClick={handleCreate} disabled={!!loading}
              style={{ marginTop: "1.2rem", background: "#10b981", color: "white", padding: "10px 24px", borderRadius: 8, border: "none", fontSize: 15, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1 }}>
              {loading === "create" ? "⏳ Creating..." : "🚀 Create Destination"}
            </button>
          </Section>
        )}

        {/* Error */}
        {error && (
          <div style={{ background: "#450a0a", border: "1px solid #7f1d1d", borderRadius: 8, padding: "12px 16px", color: "#fca5a5", marginTop: "1rem" }}>
            {error}
          </div>
        )}

        {/* Result */}
        {result && (
          <Section title="✅ Done!">
            <div style={{ background: "#052e16", border: "1px solid #166534", borderRadius: 8, padding: "1rem" }}>
              {result.destination === "github" ? (
                <>
                  <p style={{ margin: 0, color: "#86efac" }}>🐙 GitHub repo created!</p>
                  {result.repository?.html_url && (
                    <a href={result.repository.html_url} target="_blank" rel="noreferrer"
                      style={{ color: "#6ee7b7", fontSize: 14 }}>{result.repository.html_url}</a>
                  )}
                </>
              ) : (
                <>
                  <p style={{ margin: 0, color: "#86efac" }}>📝 Notion page created!</p>
                  {result.page?.url && (
                    <a href={result.page.url} target="_blank" rel="noreferrer"
                      style={{ color: "#6ee7b7", fontSize: 14 }}>{result.page.url}</a>
                  )}
                </>
              )}
            </div>
          </Section>
        )}

      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 12, padding: "1.2rem 1.4rem", marginBottom: "1.2rem", border: "1px solid #334155" }}>
      <h2 style={{ margin: "0 0 1rem", fontSize: "0.95rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</h2>
      {children}
    </div>
  );
}