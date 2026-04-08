import React, { useMemo, useState } from "react";

export default function App() {
  const [items, setItems] = useState([
    { id: 1, title: "Wire browser prompt to backend request", done: true },
    { id: 2, title: "Generate preview artifact", done: false }
  ]);
  const [filter, setFilter] = useState("all");
  const [title, setTitle] = useState("");

  const visible = useMemo(() => items.filter((item) => {
    if (filter === "done") return item.done;
    if (filter === "open") return !item.done;
    return true;
  }), [items, filter]);

  function addItem(event) {
    event.preventDefault();
    const clean = title.trim();
    if (!clean) return;
    setItems((current) => [...current, { id: Date.now(), title: clean, done: false }]);
    setTitle("");
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white p-6">
      <section className="mx-auto max-w-2xl rounded-lg border border-slate-800 bg-slate-900 p-6">
        <p className="text-sm uppercase tracking-wide text-cyan-300">CrucibAI Golden Path Proof</p>
        <h1 className="mt-2 text-3xl font-bold">Task Tracker</h1>
        <p className="mt-3 text-slate-300">Prompt: Build a simple task tracker with add, complete, and filter actions.</p>
        <form onSubmit={addItem} className="mt-6 flex gap-2">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Add a task"
            className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-2"
          />
          <button className="rounded bg-cyan-400 px-4 py-2 font-semibold text-slate-950">Add</button>
        </form>
        <div className="mt-4 flex gap-2">
          {["all", "open", "done"].map((name) => (
            <button key={name} onClick={() => setFilter(name)} className="rounded border border-slate-700 px-3 py-1">
              {name}
            </button>
          ))}
        </div>
        <ul className="mt-5 space-y-2">
          {visible.map((item) => (
            <li key={item.id} className="flex items-center justify-between rounded border border-slate-800 p-3">
              <span className={item.done ? "line-through text-slate-500" : ""}>{item.title}</span>
              <button onClick={() => setItems((current) => current.map((next) => next.id === item.id ? { ...next, done: !next.done } : next))}>
                {item.done ? "Reopen" : "Complete"}
              </button>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
