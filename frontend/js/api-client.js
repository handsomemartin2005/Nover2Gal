class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...options, headers });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = payload?.detail || payload?.message || `请求失败（${response.status}）`;
    throw new ApiError(message, response.status, payload);
  }
  return payload;
}

export const api = {
  request,
  listProjects: () => request("/api/projects"),
  getProject: (id) => request(`/api/projects/${encodeURIComponent(id)}`),
  createProject: (payload) => request("/api/projects", { method: "POST", body: JSON.stringify(payload) }),
  updateProject: (id, payload) => request(`/api/projects/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: (id) => request(`/api/projects/${encodeURIComponent(id)}`, { method: "DELETE" }),
  duplicateProject: (id) => request(`/api/projects/${encodeURIComponent(id)}/duplicate`, { method: "POST" }),
  listVersions: (id) => request(`/api/projects/${encodeURIComponent(id)}/versions`),
  rollbackVersion: (id, versionId) => request(`/api/projects/${encodeURIComponent(id)}/versions/${encodeURIComponent(versionId)}/rollback`, { method: "POST" }),
  listSamples: () => request("/api/samples"),
  getSample: (id) => request(`/api/samples/${encodeURIComponent(id)}`),
  publishSample: (projectId, payload) => request(`/api/projects/${encodeURIComponent(projectId)}/samples`, { method: "POST", body: JSON.stringify(payload) }),
  cloneSample: (id) => request(`/api/samples/${encodeURIComponent(id)}/clone`, { method: "POST" }),
  deleteSample: (id) => request(`/api/samples/${encodeURIComponent(id)}`, { method: "DELETE" }),
};

export { ApiError };

