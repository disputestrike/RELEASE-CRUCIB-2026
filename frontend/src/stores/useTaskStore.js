/**
 * PHASE 7 — Single task state authority.
 * Build completion writes here; Home reads from here. Persist to localStorage.
 */
import { createContext, useContext, useState, useCallback, useEffect } from 'react';

const TASKS_STORAGE_KEY = 'crucibai_tasks';

const TaskContext = createContext(null);

function loadTasks() {
  try {
    const raw = localStorage.getItem(TASKS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveTasks(tasks) {
  try {
    localStorage.setItem(TASKS_STORAGE_KEY, JSON.stringify(tasks));
  } catch (_) {}
}

export function TaskProvider({ children }) {
  const [tasks, setTasks] = useState(loadTasks);

  useEffect(() => {
    setTasks(loadTasks());
  }, []);

  useEffect(() => {
    if (tasks.length > 0 || localStorage.getItem(TASKS_STORAGE_KEY)) saveTasks(tasks);
  }, [tasks]);

  const addTask = useCallback((task) => {
    const entry = {
      id: task.id || `task_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`,
      name: task.name || task.prompt?.slice(0, 120) || 'Build',
      prompt: task.prompt || '',
      status: task.status || 'completed',
      createdAt: task.createdAt ?? Date.now(),
      ...task,
    };
    setTasks(prev => {
      const next = [entry, ...prev].slice(0, 200);
      saveTasks(next);
      return next;
    });
    return entry.id;
  }, []);

  const persist = useCallback(() => {
    setTasks(prev => {
      saveTasks(prev);
      return prev;
    });
  }, []);

  const value = { tasks, addTask, setTasks, persist };

  return (
    <TaskContext.Provider value={value}>
      {children}
    </TaskContext.Provider>
  );
}

export function useTaskStore() {
  const ctx = useContext(TaskContext);
  if (!ctx) {
    return {
      tasks: [],
      addTask: () => {},
      setTasks: () => {},
      persist: () => {},
    };
  }
  return ctx;
}
