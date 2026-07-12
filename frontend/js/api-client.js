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
  const response = await fetch(path, { credentials: "same-origin", ...options, headers });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new CustomEvent("novel2gal:auth-required"));
    const message = payload?.detail || payload?.message || `请求失败（${response.status}）`;
    throw new ApiError(message, response.status, payload);
  }
  return payload;
}

export const api = {
  request,
  getMe: () => request("/api/auth/me"),
  register: (payload) => request("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) => request("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  updateProfile: (payload) => request("/api/auth/profile", { method: "PATCH", body: JSON.stringify(payload) }),
  changePassword: (payload) => request("/api/auth/password", { method: "POST", body: JSON.stringify(payload) }),
  getApiConfigs: () => request("/api/account/api-configs"),
  saveApiConfig: (service, payload) => request(`/api/account/api-configs/${encodeURIComponent(service)}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteApiConfig: (service) => request(`/api/account/api-configs/${encodeURIComponent(service)}`, { method: "DELETE" }),
  getUsage: (days = 30) => request(`/api/account/usage?days=${encodeURIComponent(days)}`),
  listProjects: () => request("/api/projects"),
  getProject: (id) => request(`/api/projects/${encodeURIComponent(id)}`),
  createProject: (payload) => request("/api/projects", { method: "POST", body: JSON.stringify(payload) }),
  updateProject: (id, payload) => request(`/api/projects/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  generateCharacterImage: (id, characterId, payload = {}) => request(`/api/projects/${encodeURIComponent(id)}/characters/${encodeURIComponent(characterId)}/generate-image`, { method: "POST", body: JSON.stringify(payload) }),
  deleteProject: (id) => request(`/api/projects/${encodeURIComponent(id)}`, { method: "DELETE" }),
  duplicateProject: (id) => request(`/api/projects/${encodeURIComponent(id)}/duplicate`, { method: "POST" }),
  listVersions: (id) => request(`/api/projects/${encodeURIComponent(id)}/versions`),
  rollbackVersion: (id, versionId) => request(`/api/projects/${encodeURIComponent(id)}/versions/${encodeURIComponent(versionId)}/rollback`, { method: "POST" }),
  listSamples: () => request("/api/samples"),
  getSample: (id) => request(`/api/samples/${encodeURIComponent(id)}`),
  publishSample: (projectId, payload) => request(`/api/projects/${encodeURIComponent(projectId)}/samples`, { method: "POST", body: JSON.stringify(payload) }),
  updateSample: (id, payload) => request(`/api/samples/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  cloneSample: (id) => request(`/api/samples/${encodeURIComponent(id)}/clone`, { method: "POST" }),
  deleteSample: (id) => request(`/api/samples/${encodeURIComponent(id)}`, { method: "DELETE" }),
  adminOverview: () => request("/api/admin/overview"),
  adminUsers: () => request("/api/admin/users"),
  adminUsage: (days = 30) => request(`/api/admin/usage?days=${encodeURIComponent(days)}`),
  adminUpdateUser: (id, payload) => request(`/api/admin/users/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  adminProjects: () => request("/api/admin/projects"),
  adminAssignProject: (id, ownerId) => request(`/api/admin/projects/${encodeURIComponent(id)}/owner`, { method: "PATCH", body: JSON.stringify({ owner_id: ownerId }) }),
  adminDeleteProject: (id) => request(`/api/admin/projects/${encodeURIComponent(id)}`, { method: "DELETE" }),
  adminSamples: () => request("/api/admin/samples"),
  adminUpdateSample: (id, payload) => request(`/api/admin/samples/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  adminAssignSample: (id, ownerId) => request(`/api/admin/samples/${encodeURIComponent(id)}/owner`, { method: "PATCH", body: JSON.stringify({ owner_id: ownerId }) }),
  adminDeleteSample: (id) => request(`/api/admin/samples/${encodeURIComponent(id)}`, { method: "DELETE" }),
};

export { ApiError };
