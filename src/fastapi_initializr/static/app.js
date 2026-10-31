"use strict";

(() => {
  const form = document.getElementById("project-form");
  const nameInput = document.getElementById("project-name");
  const packageInput = document.getElementById("package");
  const descriptionInput = document.getElementById("description");
  const pythonSelect = document.getElementById("python");
  const dependencyGroups = document.getElementById("dependency-groups");
  const errorBox = document.getElementById("error");
  const previewStatus = document.getElementById("preview-status");
  const projectLabel = document.getElementById("project-label");
  const fileList = document.getElementById("file-list");
  const treeEmpty = document.getElementById("tree-empty");
  const selectedFileLabel = document.getElementById("selected-file");
  const fileSizeLabel = document.getElementById("file-size");
  const fileContent = document.getElementById("file-content");
  const refreshButton = document.getElementById("refresh-preview");

  if (
    !form ||
    !nameInput ||
    !packageInput ||
    !descriptionInput ||
    !pythonSelect ||
    !dependencyGroups ||
    !errorBox ||
    !previewStatus ||
    !projectLabel ||
    !fileList ||
    !treeEmpty ||
    !selectedFileLabel ||
    !fileSizeLabel ||
    !fileContent ||
    !refreshButton
  ) {
    return;
  }

  const PREVIEW_DEBOUNCE_MS = 250;
  const DEFAULT_FILE_MESSAGE =
    "Choose a file to inspect its rendered content.";

  /** @type {Metadata | null} */
  let metadata = null;
  /** @type {Map<string, Dependency>} */
  const dependenciesById = new Map();
  /** @type {Map<string, Set<string>>} */
  const conflictsById = new Map();
  /** @type {Map<string, HTMLElement>} */
  const notesById = new Map();
  /** @type {string[]} */
  let dependencyOrder = [];
  /** @type {PreviewFile[]} */
  let files = [];
  /** @type {string | null} */
  let selectedPath = null;
  let previewTimer = 0;
  let previewToken = 0;
  /** @type {AbortController | null} */
  let previewController = null;
  let packageTouched = false;

  function setError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function clearError() {
    errorBox.textContent = "";
    errorBox.hidden = true;
  }

  function messageFromError(payload, fallback) {
    if (!payload || typeof payload !== "object") {
      return fallback;
    }
    const detail = payload.detail;
    if (typeof detail === "string" && detail.trim() !== "") {
      return detail;
    }
    if (Array.isArray(detail)) {
      const parts = detail.map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item.msg === "string") {
          const location = Array.isArray(item.loc)
            ? item.loc
                .filter(
                  (part) =>
                    part !== "body" && part !== "query" && part !== "path",
                )
                .join(".")
            : "";
          return location ? `${location}: ${item.msg}` : item.msg;
        }
        return "";
      });
      const message = parts.filter((part) => part !== "").join(" ");
      if (message !== "") {
        return message;
      }
    }
    if (
      detail &&
      typeof detail === "object" &&
      typeof detail.message === "string"
    ) {
      return detail.message;
    }
    return fallback;
  }

  async function responseError(response) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    const status = `${response.status} ${response.statusText}`.trim();
    return messageFromError(payload, `Request failed (${status}).`);
  }

  function getCheckedIds() {
    return Array.from(
      form.querySelectorAll('input[name="dependencies"]:checked'),
    ).map((input) => input.value);
  }

  function currentState() {
    return {
      name: nameInput.value,
      package: packageInput.value,
      description: descriptionInput.value,
      python: pythonSelect.value,
      dependencies: getCheckedIds(),
    };
  }

  function stateParams(state) {
    const params = new URLSearchParams();
    params.set("name", state.name);
    params.set("package", state.package);
    params.set("description", state.description);
    params.set("python", state.python);
    const seen = new Set();
    for (const dependencyId of [...state.dependencies].sort()) {
      if (!seen.has(dependencyId)) {
        seen.add(dependencyId);
        params.append("dependencies", dependencyId);
      }
    }
    return params;
  }

  function updateUrl() {
    const query = stateParams(currentState()).toString();
    const nextUrl = `${window.location.pathname}?${query}${window.location.hash}`;
    window.history.replaceState(null, "", nextUrl);
  }

  function dependencyName(dependencyId) {
    const dependency = dependenciesById.get(dependencyId);
    return dependency ? dependency.name : dependencyId;
  }

  function expandRequirements(selected) {
    const result = new Set(selected);
    let changed = true;
    let passes = 0;
    while (changed && passes < dependencyOrder.length + 1) {
      changed = false;
      passes += 1;
      for (const dependencyId of Array.from(result)) {
        const dependency = dependenciesById.get(dependencyId);
        if (!dependency) {
          continue;
        }
        for (const requirement of dependency.requires) {
          if (dependenciesById.has(requirement) && !result.has(requirement)) {
            result.add(requirement);
            changed = true;
          }
        }
      }
    }
    return result;
  }

  function removeDependents(selected, removedId) {
    const result = new Set(selected);
    const removed = new Set([removedId]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const dependencyId of Array.from(result)) {
        const dependency = dependenciesById.get(dependencyId);
        if (!dependency) {
          continue;
        }
        if (
          !removed.has(dependencyId) &&
          dependency.requires.some((id) => removed.has(id))
        ) {
          removed.add(dependencyId);
        }
      }
    }
    for (const dependencyId of removed) {
      result.delete(dependencyId);
    }
    return result;
  }

  function reconcileSelection(selected, preferredId) {
    let result = expandRequirements(selected);
    let passes = 0;
    let changed = true;
    while (changed && passes < dependencyOrder.length + 1) {
      changed = false;
      passes += 1;
      const priority = [
        ...(preferredId !== null && result.has(preferredId) ? [preferredId] : []),
        ...dependencyOrder.filter((id) => id !== preferredId && result.has(id)),
      ];
      for (const dependencyId of priority) {
        if (!result.has(dependencyId)) {
          continue;
        }
        const conflicts = conflictsById.get(dependencyId);
        if (!conflicts) {
          continue;
        }
        for (const conflictId of conflicts) {
          if (conflictId !== dependencyId && result.has(conflictId)) {
            result.delete(conflictId);
            changed = true;
          }
        }
      }
      const expanded = expandRequirements(result);
      if (expanded.size !== result.size) {
        result = expanded;
        changed = true;
      }
    }
    return result;
  }

  function applySelection(selected) {
    for (const input of form.querySelectorAll(
      'input[name="dependencies"]',
    )) {
      input.checked = selected.has(input.value);
    }
  }

  function syncDependencyState() {
    const selected = new Set(getCheckedIds());
    for (const input of form.querySelectorAll(
      'input[name="dependencies"]',
    )) {
      const dependencyId = input.value;
      const dependency = dependenciesById.get(dependencyId);
      if (!dependency) {
        continue;
      }
      const conflicts = Array.from(conflictsById.get(dependencyId) ?? []).filter(
        (id) => selected.has(id),
      );
      const requiring = Array.from(selected)
        .filter((id) => id !== dependencyId)
        .filter((id) =>
          dependenciesById.get(id)?.requires.includes(dependencyId),
        )
        .map(dependencyName);

      const note = notesById.get(dependencyId);
      const option = input.closest(".dependency-option");
      if (input.checked) {
        input.disabled = false;
        if (note) {
          note.textContent =
            requiring.length > 0
              ? `Required by ${requiring.join(", ")}`
              : "";
          note.hidden = requiring.length === 0;
        }
        if (option) {
          option.classList.toggle("is-required", requiring.length > 0);
          option.classList.remove("is-disabled");
        }
      } else {
        input.disabled = conflicts.length > 0;
        if (note) {
          note.textContent =
            conflicts.length > 0
              ? `Conflicts with ${conflicts.map(dependencyName).join(", ")}`
              : "";
          note.hidden = conflicts.length === 0;
        }
        if (option) {
          option.classList.toggle("is-disabled", conflicts.length > 0);
          option.classList.remove("is-required");
        }
      }
    }
  }

  function renderDependencies(selected, preferredId) {
    dependencyGroups.replaceChildren();
    notesById.clear();

    const resolved = reconcileSelection(selected, preferredId);
    const fragment = document.createDocumentFragment();

    for (const [groupIndex, group] of metadata.dependencies.groups.entries()) {
      const groupSection = document.createElement("section");
      groupSection.className = "dependency-group";
      const headingId = `dependency-group-${groupIndex}-${group.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")}`;
      groupSection.setAttribute("aria-labelledby", headingId);

      const heading = document.createElement("h3");
      heading.id = headingId;
      heading.className = "dependency-group-title";
      heading.textContent = group.name;
      groupSection.append(heading);

      const list = document.createElement("div");
      list.className = "dependency-list";

      for (const dependency of group.values) {
        const option = document.createElement("label");
        option.className = "dependency-option";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.name = "dependencies";
        input.value = dependency.id;
        input.id = `dependency-${dependency.id}`;
        input.checked = resolved.has(dependency.id);

        const body = document.createElement("span");
        body.className = "dependency-body";

        const title = document.createElement("span");
        title.className = "dependency-title";
        title.textContent = dependency.name;

        const description = document.createElement("span");
        description.className = "dependency-description";
        description.textContent = dependency.description;

        const note = document.createElement("span");
        note.className = "dependency-note";
        note.id = `dependency-note-${dependency.id}`;
        note.hidden = true;

        body.append(title, description, note);
        input.setAttribute("aria-describedby", note.id);
        option.append(input, body);
        list.append(option);
        notesById.set(dependency.id, note);
      }

      groupSection.append(list);
      fragment.append(groupSection);
    }

    dependencyGroups.append(fragment);
    applySelection(resolved);
    syncDependencyState();
  }

  function renderPythonOption(values, selectedId) {
    pythonSelect.replaceChildren();
    for (const value of values) {
      const option = document.createElement("option");
      option.value = value.id;
      option.textContent = value.name;
      pythonSelect.append(option);
    }
    pythonSelect.value = selectedId;
  }

  function initialValue(params, key, fallback) {
    return params.has(key) ? params.get(key) ?? "" : fallback;
  }

  function initialDependencies(params) {
    const selected = new Set();
    let preferredId = null;
    for (const rawValue of params.getAll("dependencies")) {
      for (const dependencyId of rawValue.split(",")) {
        const trimmed = dependencyId.trim();
        if (dependenciesById.has(trimmed)) {
          selected.add(trimmed);
          preferredId = trimmed;
        }
      }
    }
    return { selected, preferredId };
  }

  function configureMetadata(nextMetadata, params) {
    metadata = nextMetadata;

    dependenciesById.clear();
    conflictsById.clear();
    dependencyOrder = [];
    for (const group of metadata.dependencies.groups) {
      for (const dependency of group.values) {
        dependenciesById.set(dependency.id, dependency);
        dependencyOrder.push(dependency.id);
        if (!conflictsById.has(dependency.id)) {
          conflictsById.set(dependency.id, new Set());
        }
      }
    }
    for (const dependency of dependenciesById.values()) {
      const conflicts = conflictsById.get(dependency.id);
      if (!conflicts) {
        continue;
      }
      for (const conflictId of dependency.conflicts) {
        conflicts.add(conflictId);
        const reverse = conflictsById.get(conflictId);
        if (reverse) {
          reverse.add(dependency.id);
        }
      }
    }

    nameInput.maxLength = metadata.project.name.maxLength;
    packageInput.maxLength = metadata.project.package.maxLength;
    descriptionInput.maxLength = metadata.project.description.maxLength;

    nameInput.value = initialValue(
      params,
      "name",
      metadata.project.name.default,
    );
    packageInput.value = initialValue(
      params,
      "package",
      metadata.project.package.default,
    );
    packageTouched = params.has("package");
    descriptionInput.value = initialValue(
      params,
      "description",
      metadata.project.description.default,
    );

    const pythonValues = metadata.python.values.map((value) => ({
      id: value.id,
      name: value.name,
    }));
    const requestedPython = params.get("python");
    const pythonIsKnown = pythonValues.some(
      (value) => value.id === requestedPython,
    );
    renderPythonOption(
      pythonValues,
      pythonIsKnown ? requestedPython : metadata.python.default,
    );

    const initial = initialDependencies(params);
    renderDependencies(initial.selected, initial.preferredId);
    projectLabel.textContent = nameInput.value;
  }

  function formatBytes(size) {
    if (!Number.isFinite(size) || size < 0) {
      return "";
    }
    if (size < 1024) {
      return `${size} B`;
    }
    const units = ["KB", "MB", "GB"];
    let value = size / 1024;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex += 1;
    }
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unitIndex]}`;
  }

  function updatePreviewSelection() {
    for (const button of fileList.querySelectorAll("button.file-button")) {
      if (button.dataset.path === selectedPath) {
        button.setAttribute("aria-current", "true");
      } else {
        button.removeAttribute("aria-current");
      }
    }
  }

  function renderFileContent() {
    const file = files.find((candidate) => candidate.path === selectedPath);
    if (!file) {
      selectedPath = null;
      selectedFileLabel.textContent = "No file selected";
      fileSizeLabel.textContent = "";
      fileContent.textContent = DEFAULT_FILE_MESSAGE;
      updatePreviewSelection();
      return;
    }
    selectedFileLabel.textContent = file.path;
    fileSizeLabel.textContent = formatBytes(file.size);
    fileContent.textContent =
      file.content === "" ? "(empty file)" : file.content;
    updatePreviewSelection();
  }

  function selectFile(path) {
    selectedPath = path;
    renderFileContent();
  }

  function renderFiles() {
    fileList.replaceChildren();
    const fragment = document.createDocumentFragment();

    for (const file of files) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "file-button";
      button.dataset.path = file.path;

      const path = document.createElement("span");
      path.className = "file-path";
      path.textContent = file.path;

      const size = document.createElement("span");
      size.className = "file-size";
      size.textContent = formatBytes(file.size);

      button.append(path, size);
      button.addEventListener("click", () => {
        selectFile(file.path);
      });
      item.append(button);
      fragment.append(item);
    }

    fileList.append(fragment);
    fileList.hidden = files.length === 0;
    treeEmpty.hidden = files.length > 0;

    if (!files.some((file) => file.path === selectedPath)) {
      selectedPath = files.length > 0 ? files[0].path : null;
    }
    renderFileContent();
  }

  function renderPreview(projectName) {
    projectLabel.textContent = projectName;
    previewStatus.textContent = `${files.length} file${
      files.length === 1 ? "" : "s"
    } · updates automatically`;
    renderFiles();
  }

  function normalizePreview(payload) {
    if (!payload || !Array.isArray(payload.files)) {
      return [];
    }
    return payload.files
      .filter((file) => file && typeof file.path === "string" && file.path !== "")
      .map((file) => {
        const size = Number(file.size);
        return {
          path: file.path,
          content: typeof file.content === "string" ? file.content : "",
          size: Number.isFinite(size) && size >= 0 ? size : 0,
        };
      });
  }

  async function loadPreview() {
    if (!metadata) {
      return;
    }
    window.clearTimeout(previewTimer);
    previewTimer = 0;

    if (previewController) {
      previewController.abort();
    }
    const controller = new AbortController();
    previewController = controller;
    previewToken += 1;
    const token = previewToken;
    const state = currentState();
    const params = stateParams(state);

    previewStatus.textContent = "Updating preview…";
    projectLabel.textContent = state.name;

    try {
      const response = await fetch(`/api/preview?${params.toString()}`, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (token !== previewToken) {
        return;
      }
      if (!response.ok) {
        setError(await responseError(response));
        previewStatus.textContent = "Preview unavailable";
        return;
      }
      const payload = await response.json();
      if (token !== previewToken) {
        return;
      }
      clearError();
      files = normalizePreview(payload);
      const projectName =
        payload && typeof payload.name === "string" ? payload.name : state.name;
      renderPreview(projectName);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      if (token !== previewToken) {
        return;
      }
      setError("Could not load the preview. Check your connection and try again.");
      previewStatus.textContent = "Preview unavailable";
    }
  }

  function schedulePreview() {
    window.clearTimeout(previewTimer);
    previewTimer = window.setTimeout(() => {
      void loadPreview();
    }, PREVIEW_DEBOUNCE_MS);
  }

  function stateChanged() {
    clearError();
    updateUrl();
    schedulePreview();
  }

  function downloadProject() {
    updateUrl();
    window.clearTimeout(previewTimer);
    const anchor = document.createElement("a");
    anchor.href = `/api/generate?${stateParams(currentState()).toString()}`;
    anchor.rel = "noopener";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
  }

  form.addEventListener("input", (event) => {
    if (!metadata) {
      return;
    }
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target === nameInput) {
      projectLabel.textContent = nameInput.value;
      if (!packageTouched) {
        packageInput.value = nameInput.value.toLowerCase().replace(/-/g, "_");
      }
    }
    if (target === packageInput) {
      packageTouched = true;
    }
    stateChanged();
  });

  form.addEventListener("change", (event) => {
    if (!metadata) {
      return;
    }
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) {
      return;
    }
    if (target.name !== "dependencies") {
      return;
    }
    const selected = new Set(getCheckedIds());
    const nextSelected = target.checked
      ? reconcileSelection(selected, target.value)
      : reconcileSelection(removeDependents(selected, target.value), null);
    applySelection(nextSelected);
    syncDependencyState();
    stateChanged();
  });

  form.addEventListener("submit", (event) => {
    if (!metadata) {
      return;
    }
    event.preventDefault();
    downloadProject();
  });

  refreshButton.addEventListener("click", () => {
    if (!metadata) {
      return;
    }
    void loadPreview();
  });

  async function loadMetadata() {
    const params = new URLSearchParams(window.location.search);
    try {
      const response = await fetch("/api/metadata", {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        setError(await responseError(response));
        previewStatus.textContent = "Options unavailable";
        return;
      }
      const payload = await response.json();
      if (
        !payload ||
        !payload.project ||
        !payload.python ||
        !Array.isArray(payload.python.values) ||
        !payload.dependencies ||
        !Array.isArray(payload.dependencies.groups)
      ) {
        setError("The server returned invalid project metadata.");
        previewStatus.textContent = "Options unavailable";
        return;
      }
      configureMetadata(payload, params);
      updateUrl();
      await loadPreview();
    } catch {
      setError("Could not load project options. Check your connection and reload.");
      previewStatus.textContent = "Options unavailable";
    }
  }

  void loadMetadata();
})();
