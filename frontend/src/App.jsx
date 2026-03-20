import { useState } from "react";

const API =
  import.meta.env.VITE_API_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000`;

export default function App() {
  const [courses, setCourses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [assignmentFilter, setAssignmentFilter] = useState("all");
  const [language, setLanguage] = useState("python");
  const [routeMode, setRouteMode] = useState("auto");
  const [notionContentMode, setNotionContentMode] = useState("structured");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");

  async function parseResponse(res) {
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return res.json();
    }
    return {};
  }

  function getErrorDetail(data, fallback) {
    if (typeof data?.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    return fallback;
  }

  async function fetchCourses() {
    setLoading("courses"); setError(""); setCourses([]); setAssignments([]); setResult(null);
    try {
      const res = await fetch(`${API}/courses`);
      const data = await parseResponse(res);
      if (!res.ok) {
        throw new Error(getErrorDetail(data, "Failed to fetch courses."));
      }
      setCourses(data.courses || []);
    } catch (e) {
      setError(`❌ ${e.message || "Could not connect to backend. Is api.py running?"}`);
    }
    setLoading("");
  }

  async function fetchAssignments(courseId) {
    setSelectedCourse(courseId); setAssignments([]); setSelectedAssignment(null); setResult(null);
    setAssignmentFilter("all");
    setLoading("assignments"); setError("");
    try {
      const res = await fetch(`${API}/courses/${courseId}/assignments`);
      const data = await parseResponse(res);
      if (!res.ok) {
        throw new Error(getErrorDetail(data, "Failed to fetch assignments."));
      }
      setAssignments(data.assignments || []);
    } catch (e) {
      setError(`❌ ${e.message || "Failed to fetch assignments."}`);
    }
    setLoading("");
  }

  function isUpcomingAssignment(assignment) {
    if (!assignment?.due_at) return false;
    const dueDate = new Date(assignment.due_at);
    return !Number.isNaN(dueDate.getTime()) && dueDate > new Date();
  }

  function isCompletedAssignment(assignment) {
    return Boolean(
      assignment?.is_completed ||
      assignment?.has_submitted_submissions ||
      assignment?.submitted_at ||
      ["submitted", "graded", "pending_review"].includes(assignment?.workflow_state)
    );
  }

  const filteredAssignments = assignments.filter((assignment) => {
    if (assignmentFilter === "upcoming") return isUpcomingAssignment(assignment);
    if (assignmentFilter === "completed") return isCompletedAssignment(assignment);
    return true;
  });

  async function handleCreate() {
    if (!selectedCourse) return;
    setLoading("create"); setError(""); setResult(null);
    const assignmentType =
      routeMode === "auto"
        ? undefined
        : routeMode === "github"
          ? "coding"
          : "writing";

    try {
      const res = await fetch(`${API}/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          course_id: selectedCourse,
          assignment_id: selectedAssignment || undefined,
          language: routeMode === "notion" ? undefined : language,
          assignment_type: assignmentType,
          notion_content_mode: routeMode === "notion" ? notionContentMode : undefined,
        }),
      });
      const data = await parseResponse(res);
      if (!res.ok) throw new Error(getErrorDetail(data, "Unknown error"));
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
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: "0.9rem" }}>
              {[
                { key: "all", label: `All (${assignments.length})` },
                { key: "upcoming", label: `Upcoming (${assignments.filter(isUpcomingAssignment).length})` },
                { key: "completed", label: `Completed (${assignments.filter(isCompletedAssignment).length})` },
              ].map((filter) => (
                <button
                  key={filter.key}
                  onClick={() => setAssignmentFilter(filter.key)}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 999,
                    border: "1px solid",
                    borderColor: assignmentFilter === filter.key ? "#6366f1" : "#334155",
                    background: assignmentFilter === filter.key ? "#1e1b4b" : "#0f172a",
                    color: "#e2e8f0",
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  {filter.label}
                </button>
              ))}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {assignmentFilter !== "completed" && (
                <button onClick={() => setSelectedAssignment(null)}
                  style={{
                    textAlign: "left", padding: "10px 14px", borderRadius: 8, border: "1px solid",
                    borderColor: selectedAssignment === null ? "#6366f1" : "#334155",
                    background: selectedAssignment === null ? "#1e1b4b" : "#1e293b",
                    color: "#e2e8f0", cursor: "pointer", fontSize: 14
                  }}>
                  ⏭ Next upcoming assignment (auto)
                </button>
              )}
              {filteredAssignments.map(a => (
                <button key={a.id} onClick={() => setSelectedAssignment(a.id)}
                  style={{
                    textAlign: "left", padding: "10px 14px", borderRadius: 8, border: "1px solid",
                    borderColor: selectedAssignment === a.id ? "#6366f1" : "#334155",
                    background: selectedAssignment === a.id ? "#1e1b4b" : "#1e293b",
                    color: "#e2e8f0", cursor: "pointer", fontSize: 14
                  }}>
                  <span style={{ color: "#94a3b8", marginRight: 8 }}>#{a.id}</span>{a.name}
                  {a.due_at && <span style={{ color: "#64748b", marginLeft: 8, fontSize: 12 }}>Due: {new Date(a.due_at).toLocaleDateString()}</span>}
                  {isCompletedAssignment(a) && <span style={{ color: "#86efac", marginLeft: 8, fontSize: 12 }}>Completed</span>}
                </button>
              ))}
              {filteredAssignments.length === 0 && (
                <div style={{ padding: "0.8rem 0.2rem", color: "#94a3b8", fontSize: 13 }}>
                  No assignments match the current filter.
                </div>
              )}
            </div>
          </Section>
        )}

        {/* Step 3 - Route */}
        {selectedCourse && (
          <Section title="Step 3 — Choose Destination">
            <p style={{ marginTop: 0, marginBottom: "0.9rem", color: "#94a3b8", fontSize: 14 }}>
              Pick how this assignment should be routed.
            </p>

            <div style={{ display: "grid", gap: "0.7rem", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
              {[
                { key: "auto", title: "Auto Route", subtitle: "Infer coding vs writing" },
                { key: "github", title: "GitHub", subtitle: "Force coding destination" },
                { key: "notion", title: "Notion", subtitle: "Force writing destination" },
              ].map((option) => (
                <button
                  key={option.key}
                  onClick={() => setRouteMode(option.key)}
                  style={{
                    textAlign: "left",
                    borderRadius: 10,
                    border: "1px solid",
                    borderColor: routeMode === option.key ? "#6366f1" : "#334155",
                    background: routeMode === option.key ? "#1e1b4b" : "#1e293b",
                    padding: "0.8rem 0.9rem",
                    color: "#e2e8f0",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{option.title}</div>
                  <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{option.subtitle}</div>
                </button>
              ))}
            </div>

            {routeMode !== "notion" && (
              <div style={{ marginTop: "1rem" }}>
                <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>
                  Starter Language (GitHub path)
                </label>
                <select
                  value={language}
                  onChange={e => setLanguage(e.target.value)}
                  style={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", padding: "8px 12px", borderRadius: 8, fontSize: 14 }}
                >
                  {["python", "java", "javascript", "cpp"].map(l => <option key={l}>{l}</option>)}
                </select>
              </div>
            )}

            {routeMode === "notion" && (
              <div style={{ marginTop: "0.8rem" }}>
                <p style={{ marginTop: 0, marginBottom: "0.7rem", color: "#94a3b8", fontSize: 13 }}>
                  Language is skipped for Notion page creation.
                </p>
                <div style={{ display: "grid", gap: "0.6rem", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
                  {[
                    { key: "structured", title: "Structured Page", subtitle: "Title, due date, and formatted assignment notes" },
                    { key: "text", title: "Text Only", subtitle: "Just paste the assignment text into the page body" },
                  ].map((option) => (
                    <button
                      key={option.key}
                      onClick={() => setNotionContentMode(option.key)}
                      style={{
                        textAlign: "left",
                        borderRadius: 10,
                        border: "1px solid",
                        borderColor: notionContentMode === option.key ? "#14b8a6" : "#334155",
                        background: notionContentMode === option.key ? "#0f3b3a" : "#1e293b",
                        padding: "0.75rem 0.85rem",
                        color: "#e2e8f0",
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ fontSize: 14, fontWeight: 600 }}>{option.title}</div>
                      <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{option.subtitle}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div style={{ marginTop: "1rem", fontSize: 13, color: "#94a3b8" }}>
              Route summary: {routeMode === "auto" ? "Auto-detect destination" : routeMode === "github" ? "GitHub (coding)" : `Notion (${notionContentMode === "text" ? "text only" : "structured"})`}
            </div>

            <button onClick={handleCreate} disabled={!!loading}
              style={{ marginTop: "1.2rem", background: "#10b981", color: "white", padding: "10px 24px", borderRadius: 8, border: "none", fontSize: 15, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1 }}>
              {loading === "create"
                ? "⏳ Creating..."
                : routeMode === "github"
                  ? "🚀 Create GitHub Repository"
                  : routeMode === "notion"
                    ? "📝 Create Notion Page"
                    : "🚀 Create Destination"}
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