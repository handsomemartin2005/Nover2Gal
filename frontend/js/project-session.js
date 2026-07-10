import { api } from "/static/js/api-client.js?v=20260710-auth3";

const DB_NAME = "novel2gal-studio";
const DB_VERSION = 1;
const SNAPSHOT_STORE = "project-snapshots";

class ProjectSession extends EventTarget {
  constructor() {
    super();
    this.projectId = null;
    this.project = null;
    this.pending = {};
    this.timer = null;
    this.state = "idle";
    this.onlineHandler = () => this.retry();
    window.addEventListener("online", this.onlineHandler);
  }

  async restore() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("new") === "1") return null;
    const urlId = params.get("project_id");
    const lastId = localStorage.getItem("novel2gal.last_project_id");
    const projectId = urlId || lastId;
    if (!projectId) return null;
    this.projectId = projectId;
    try {
      this.project = await api.getProject(projectId);
      this.remember(this.project);
      await this.writeSnapshot(this.project);
      this.setState("saved");
      return { project: this.project, source: "server" };
    } catch (error) {
      const snapshot = await this.readSnapshot(projectId);
      if (snapshot) {
        this.project = snapshot;
        this.setState(navigator.onLine ? "failed" : "offline");
        return { project: snapshot, source: "snapshot", error };
      }
      this.projectId = null;
      return null;
    }
  }

  markDirty(payload) {
    this.pending = { ...this.pending, ...payload };
    this.setState("dirty");
    window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => this.save(), 800);
  }

  async save(payload = {}) {
    window.clearTimeout(this.timer);
    this.pending = { ...this.pending, ...payload };
    if (!Object.keys(this.pending).length && this.projectId) return this.project;
    const data = { ...this.pending };
    this.pending = {};
    this.setState("saving");
    try {
      if (!this.projectId) {
        this.project = await api.createProject({
          title: data.title || "未命名企划",
          source_text: data.source_text || "",
          filename: data.filename || "",
          pov_character: data.pov_character || "",
          max_scenes: data.max_scenes || null,
          llm_model: data.llm_model || null,
        });
        this.projectId = this.project.project_id;
        const url = new URL(window.location.href);
        url.pathname = "/create";
        url.searchParams.set("project_id", this.projectId);
        window.history.replaceState({}, "", `${url.pathname}${url.search}`);
        const remaining = { ...data };
        delete remaining.source_text;
        if (remaining.result || remaining.status || remaining.ui_state) {
          this.project = await api.updateProject(this.projectId, remaining);
        }
      } else {
        this.project = await api.updateProject(this.projectId, data);
      }
      this.remember(this.project);
      await this.writeSnapshot(this.project);
      this.setState("saved");
      return this.project;
    } catch (error) {
      this.pending = { ...data, ...this.pending };
      const snapshot = { ...(this.project || {}), ...data, project_id: this.projectId, updated_at: Date.now() / 1000 };
      if (this.projectId) await this.writeSnapshot(snapshot);
      this.setState(navigator.onLine ? "failed" : "offline", error);
      throw error;
    }
  }

  async retry() {
    if (!Object.keys(this.pending).length) return;
    try { await this.save(); } catch (_) { /* state event already reports failure */ }
  }

  remember(project) {
    if (!project?.project_id) return;
    localStorage.setItem("novel2gal.last_project_id", project.project_id);
    localStorage.setItem("novel2gal.lastProjectTitle", project.title || "未命名企划");
  }

  setState(state, error = null) {
    this.state = state;
    this.dispatchEvent(new CustomEvent("statechange", { detail: { state, error, project: this.project } }));
    window.dispatchEvent(new CustomEvent("novel2gal:save-state", { detail: { state, error, project: this.project } }));
  }

  async writeSnapshot(project) {
    if (!project?.project_id || !window.indexedDB) return;
    const db = await openDatabase();
    await transactionPromise(db, "readwrite", (store) => store.put({ ...project, snapshot_at: Date.now() }, project.project_id));
    db.close();
  }

  async readSnapshot(projectId) {
    if (!window.indexedDB) return null;
    const db = await openDatabase();
    const value = await transactionPromise(db, "readonly", (store) => store.get(projectId));
    db.close();
    return value || null;
  }

  destroy() {
    window.clearTimeout(this.timer);
    window.removeEventListener("online", this.onlineHandler);
  }
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(SNAPSHOT_STORE)) request.result.createObjectStore(SNAPSHOT_STORE);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function transactionPromise(db, mode, operation) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(SNAPSHOT_STORE, mode);
    const request = operation(transaction.objectStore(SNAPSHOT_STORE));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export { ProjectSession };
