"use strict";

(() => {
  const form = document.getElementById("project-form");
  const nameInput = document.getElementById("project-name");
  const packageInput = document.getElementById("package");
  const descriptionInput = document.getElementById("description");
  const versionInput = document.getElementById("version");
  const authorInput = document.getElementById("author");
  const baseDirInput = document.getElementById("base-dir");
  const applicationNameInput = document.getElementById("application-name");
  const pythonSelect = document.getElementById("python");
  const fastapiSelect = document.getElementById("fastapi");
  const dependencyGroups = document.getElementById("dependency-groups");
  const dependencySearch = document.getElementById("dependency-search");
  const clearSearchButton = document.getElementById("clear-search");
  const selectedCount = document.getElementById("selected-count");
  const dependencyEmpty = document.getElementById("dependency-empty");
  const errorBox = document.getElementById("error");
  const nameError = document.getElementById("name-error");
  const packageError = document.getElementById("package-error");
  const previewStatus = document.getElementById("preview-status");
  const projectLabel = document.getElementById("project-label");
  const fileList = document.getElementById("file-list");
  const treeEmpty = document.getElementById("tree-empty");
  const selectedFileLabel = document.getElementById("selected-file");
  const fileSizeLabel = document.getElementById("file-size");
  const fileLanguageLabel = document.getElementById("file-language");
  const fileContent = document.getElementById("file-content");
  const outputSelect = document.getElementById("output");
  const generateButton = document.getElementById("generate");
  const shareButton = document.getElementById("share");
  const resetButton = document.getElementById("reset");

  if (
    !form ||
    !nameInput ||
    !packageInput ||
    !descriptionInput ||
    !versionInput ||
    !authorInput ||
    !baseDirInput ||
    !applicationNameInput ||
    !pythonSelect ||
    !fastapiSelect ||
    !dependencyGroups ||
    !dependencySearch ||
    !clearSearchButton ||
    !selectedCount ||
    !dependencyEmpty ||
    !errorBox ||
    !nameError ||
    !packageError ||
    !previewStatus ||
    !projectLabel ||
    !fileList ||
    !treeEmpty ||
    !selectedFileLabel ||
    !fileSizeLabel ||
    !fileLanguageLabel ||
    !fileContent ||
    !outputSelect ||
    !generateButton ||
    !shareButton ||
    !resetButton
  ) {
    return;
  }

  const PREVIEW_DEBOUNCE_MS = 300;
  const DEFAULT_FILE_MESSAGE =
    "Choose a file to inspect its rendered content.";
  const NAME_PATTERN = /^[a-z][a-z0-9_-]*$/;
  const PACKAGE_PATTERN = /^[a-z_][a-z0-9_]*$/;
  const OUTPUTS = {
    zip: { path: "/starter.zip", extension: ".zip", filename: null },
    tgz: { path: "/starter.tgz", extension: ".tar.gz", filename: null },
    pyproject: {
      path: "/pyproject.toml",
      extension: "",
      filename: "pyproject.toml",
    },
    requirements: {
      path: "/requirements.txt",
      extension: "",
      filename: "requirements.txt",
    },
  };
  const LANGUAGE_BY_EXTENSION = {
    cfg: "Config",
    css: "CSS",
    dockerfile: "Dockerfile",
    env: "Dotenv",
    html: "HTML",
    ini: "INI",
    js: "JavaScript",
    json: "JSON",
    lock: "Lock file",
    md: "Markdown",
    mako: "Mako",
    py: "Python",
    sh: "Shell",
    sql: "SQL",
    toml: "TOML",
    txt: "Text",
    yaml: "YAML",
    yml: "YAML",
  };

  /** @type {Record<string, unknown> | null} */
  let metadata = null;
  /** @type {Map<string, any>} */
  const dependenciesById = new Map();
  /** @type {Map<string, Set<string>>} */
  const conflictsById = new Map();
  /** @type {Map<string, HTMLElement>} */
  const notesById = new Map();
  /** @type {string[]} */
  let dependencyOrder = [];
  /** @type {Array<{path: string, content: string, size: number, language: string, highlighted: string}>} */
  let files = [];
  /** @type {string | null} */
  let selectedPath = null;
  let previewTimer = 0;
  let previewToken = 0;
  /** @type {AbortController | null} */
  let previewController = null;
  let packageTouched = false;
  /** @type {string | null} */
  let lastDependencyId = null;
  let shareTimer = 0;

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

  function dependencyInputs() {
    return Array.from(
      dependencyGroups.querySelectorAll('input[name="dependencies"]'),
    );
  }

  function getCheckedIds() {
    return dependencyInputs()
      .filter((input) => input.checked)
      .map((input) => input.value);
  }

  function currentState() {
    return {
      name: nameInput.value,
      package: packageInput.value,
      description: descriptionInput.value,
      version: versionInput.value,
      author: authorInput.value,
      python: pythonSelect.value,
      fastapi: fastapiSelect.value,
      baseDir: baseDirInput.value,
      applicationName: applicationNameInput.value,
      dependencies: getCheckedIds(),
    };
  }

  function stateParams(state) {
    const params = new URLSearchParams();
    params.set("name", state.name);
    params.set("package", state.package);
    params.set("description", state.description);
    params.set("version", state.version);
    params.set("author", state.author);
    params.set("python", state.python);
    params.set("fastapi", state.fastapi);
    params.set("baseDir", state.baseDir);
    params.set("applicationName", state.applicationName);
    for (const dependencyId of [...state.dependencies].sort()) {
      params.append("dependencies", dependencyId);
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
    return dependency && typeof dependency.name === "string"
      ? dependency.name
      : dependencyId;
  }

  function dependencyRequires(dependencyId) {
    const dependency = dependenciesById.get(dependencyId);
    return dependency && Array.isArray(dependency.requires)
      ? dependency.requires
      : [];
  }

  function expandRequirements(selected) {
    const result = new Set(selected);
    const maxPasses = dependencyOrder.length + 1;
    for (let pass = 0; pass < maxPasses; pass += 1) {
      let changed = false;
      for (const dependencyId of Array.from(result)) {
        for (const requirement of dependencyRequires(dependencyId)) {
          if (dependenciesById.has(requirement) && !result.has(requirement)) {
            result.add(requirement);
            changed = true;
          }
        }
      }
      if (!changed) {
        break;
      }
    }
    return result;
  }

  function removeDependents(selected, removedIds) {
    const result = new Set(selected);
    const removed = new Set(removedIds);
    let changed = true;
    while (changed) {
      changed = false;
      for (const dependencyId of Array.from(result)) {
        const requires = dependencyRequires(dependencyId);
        if (requires.some((id) => removed.has(id))) {
          removed.add(dependencyId);
          changed = true;
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
    const maxPasses = dependencyOrder.length + 2;
    for (let pass = 0; pass < maxPasses; pass += 1) {
      let changed = false;
      for (const dependencyId of dependencyOrder) {
        if (!result.has(dependencyId)) {
          continue;
        }
        const conflicts = conflictsById.get(dependencyId);
        if (!conflicts) {
          continue;
        }
        for (const conflictId of conflicts) {
          if (conflictId === dependencyId || !result.has(conflictId)) {
            continue;
          }
          if (conflictId === preferredId) {
            result.delete(dependencyId);
          } else {
            result.delete(conflictId);
          }
          changed = true;
        }
      }
      const expanded = expandRequirements(result);
      if (expanded.size !== result.size) {
        result = expanded;
        changed = true;
      }
      if (!changed) {
        break;
      }
    }
    return result;
  }

  function applySelection(selected) {
    for (const input of dependencyInputs()) {
      input.checked = selected.has(input.value);
    }
  }

  function updateSelectedCount() {
    const count = getCheckedIds().length;
    selectedCount.textContent = `${count} selected`;
  }

  function syncDependencyState() {
    const selected = new Set(getCheckedIds());
    for (const input of dependencyInputs()) {
      const dependencyId = input.value;
      const conflicts = Array.from(conflictsById.get(dependencyId) ?? []).filter(
        (id) => selected.has(id),
      );
      const requiring = Array.from(selected)
        .filter((id) => id !== dependencyId)
        .filter((id) => dependencyRequires(id).includes(dependencyId))
        .map(dependencyName);

      const note = notesById.get(dependencyId);
      const option = input.closest(".dependency-option");
      if (option) {
        option.classList.toggle("is-selected", input.checked);
      }

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
    updateSelectedCount();
  }

  function addDependencyLink(container, link, fallbackLabel) {
    if (!link || typeof link.href !== "string" || link.href === "") {
      return;
    }
    const anchor = document.createElement("a");
    anchor.className = "dependency-link";
    anchor.href = link.href;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.textContent =
      typeof link.title === "string" && link.title !== ""
        ? link.title
        : fallbackLabel;
    container.append(anchor);
  }

  function renderDependencyDomFromMetadata() {
    dependencyGroups.replaceChildren();
    const groups =
      metadata &&
      metadata.dependencies &&
      Array.isArray(metadata.dependencies.groups)
        ? metadata.dependencies.groups
        : [];
    const fragment = document.createDocumentFragment();

    groups.forEach((group, groupIndex) => {
      const section = document.createElement("section");
      section.className = "dependency-group";
      section.dataset.groupName = group.name;
      const headingId = `dependency-group-${groupIndex}-${String(group.name)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")}`;
      section.setAttribute("aria-labelledby", headingId);

      const heading = document.createElement("h4");
      heading.id = headingId;
      heading.className = "dependency-group-title";
      const headingText = document.createElement("span");
      headingText.textContent = group.name;
      const groupCount = document.createElement("span");
      groupCount.className = "group-count";
      groupCount.dataset.groupCount = "";
      groupCount.textContent = String(group.values.length);
      heading.append(headingText, groupCount);

      const list = document.createElement("div");
      list.className = "dependency-list";

      for (const dependency of group.values) {
        const option = document.createElement("div");
        option.className = "dependency-option";
        option.dataset.dependencyId = dependency.id;
        option.dataset.search = [
          dependency.id,
          dependency.name,
          dependency.description,
          ...(dependency.packages ?? []),
          ...(dependency.devPackages ?? []),
        ]
          .join(" ")
          .toLowerCase();

        const input = document.createElement("input");
        input.id = `dependency-${dependency.id}`;
        input.type = "checkbox";
        input.name = "dependencies";
        input.value = dependency.id;

        const body = document.createElement("div");
        body.className = "dependency-body";

        const header = document.createElement("div");
        header.className = "dependency-heading";

        const title = document.createElement("label");
        title.className = "dependency-title";
        title.htmlFor = input.id;
        title.textContent = dependency.name;

        const packageCount =
          (dependency.packages?.length ?? 0) +
          (dependency.devPackages?.length ?? 0);
        const packages = document.createElement("span");
        packages.className = "dependency-packages";
        packages.textContent = `${packageCount} package${
          packageCount === 1 ? "" : "s"
        }`;

        header.append(title, packages);

        const description = document.createElement("p");
        description.className = "dependency-description";
        description.id = `dependency-description-${dependency.id}`;
        description.textContent = dependency.description;

        const meta = document.createElement("div");
        meta.className = "dependency-meta";
        if (dependency.versionRange) {
          const version = document.createElement("span");
          version.className = "dependency-version";
          version.textContent = dependency.versionRange;
          meta.append(version);
        }
        addDependencyLink(meta, dependency.links?.guide, "Guide");
        addDependencyLink(meta, dependency.links?.reference, "Reference");
        addDependencyLink(meta, dependency.links?.home, "Homepage");

        const note = document.createElement("p");
        note.id = `dependency-note-${dependency.id}`;
        note.className = "dependency-note";
        note.hidden = true;

        input.setAttribute(
          "aria-describedby",
          `${description.id} ${note.id}`,
        );
        body.append(header, description, meta, note);
        option.append(input, body);
        list.append(option);
      }

      section.append(heading, list);
      fragment.append(section);
    });

    dependencyGroups.append(fragment);
  }

  function indexDependencyDom() {
    notesById.clear();
    for (const input of dependencyInputs()) {
      const option = input.closest(".dependency-option");
      if (!option) {
        continue;
      }
      const note = option.querySelector(".dependency-note");
      if (note instanceof HTMLElement) {
        notesById.set(input.value, note);
      }
    }
  }

  function ensureDependencyDom() {
    if (dependencyInputs().length === 0) {
      renderDependencyDomFromMetadata();
    }
    indexDependencyDom();
  }

  function renderSelect(select, values, selectedId) {
    select.replaceChildren();
    for (const value of values) {
      const option = document.createElement("option");
      option.value = value.id;
      option.textContent = value.name;
      select.append(option);
    }
    select.value = selectedId;
  }

  function initialValue(params, key, fallback) {
    return params.has(key) ? params.get(key) ?? "" : fallback;
  }

  function initialSelectValue(params, keys, option) {
    for (const key of keys) {
      if (!params.has(key)) {
        continue;
      }
      const value = params.get(key);
      if (option.values.some((candidate) => candidate.id === value)) {
        return value;
      }
    }
    return option.default;
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

  function buildDependencyTables() {
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
      for (const conflictId of dependency.conflicts ?? []) {
        conflicts.add(conflictId);
        const reverse = conflictsById.get(conflictId);
        if (reverse) {
          reverse.add(dependency.id);
        }
      }
    }
  }

  function configureMetadata(nextMetadata, params) {
    metadata = nextMetadata;
    buildDependencyTables();

    nameInput.maxLength = metadata.project.name.maxLength;
    packageInput.maxLength = metadata.project.package.maxLength;
    descriptionInput.maxLength = metadata.project.description.maxLength;
    versionInput.maxLength = metadata.project.version.maxLength;
    authorInput.maxLength = metadata.project.author.maxLength;
    baseDirInput.maxLength = metadata.baseDir.maxLength;
    applicationNameInput.maxLength = metadata.applicationName.maxLength;

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
    descriptionInput.value = initialValue(
      params,
      "description",
      metadata.project.description.default,
    );
    versionInput.value = initialValue(
      params,
      "version",
      metadata.project.version.default,
    );
    authorInput.value = initialValue(
      params,
      "author",
      metadata.project.author.default,
    );
    baseDirInput.value = initialValue(
      params,
      "baseDir",
      metadata.baseDir.default,
    );
    applicationNameInput.value = initialValue(
      params,
      "applicationName",
      metadata.applicationName.default,
    );
    packageTouched = params.has("package");

    renderSelect(
      pythonSelect,
      metadata.python.values,
      initialSelectValue(params, ["python", "pythonVersion"], metadata.python),
    );
    renderSelect(
      fastapiSelect,
      metadata.fastapi.values,
      initialSelectValue(
        params,
        ["fastapi", "fastapiVersion"],
        metadata.fastapi,
      ),
    );

    ensureDependencyDom();
    const initial = initialDependencies(params);
    applySelection(reconcileSelection(initial.selected, initial.preferredId));
    syncDependencyState();
    applyFilter();
    validateInline();
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

  function languageForPath(path) {
    const fileName = path.split("/").pop() ?? path;
    const lowerName = fileName.toLowerCase();
    if (LANGUAGE_BY_EXTENSION[lowerName]) {
      return LANGUAGE_BY_EXTENSION[lowerName];
    }
    const dotIndex = lowerName.lastIndexOf(".");
    if (dotIndex <= 0) {
      return lowerName.startsWith(".") ? "Text" : "Text";
    }
    const extension = lowerName.slice(dotIndex + 1);
    return LANGUAGE_BY_EXTENSION[extension] ?? extension.toUpperCase();
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
      fileLanguageLabel.textContent = "";
      fileSizeLabel.textContent = "";
      fileContent.textContent = DEFAULT_FILE_MESSAGE;
      updatePreviewSelection();
      return;
    }
    selectedFileLabel.textContent = file.path;
    fileLanguageLabel.textContent = file.language || languageForPath(file.path);
    fileSizeLabel.textContent = formatBytes(file.size);
    if (file.content === "") {
      fileContent.textContent = "(empty file)";
    } else if (file.highlighted !== "") {
      // Pygments escapes the source server-side; never inject raw content here.
      fileContent.innerHTML = file.highlighted;
    } else {
      fileContent.textContent = file.content;
    }
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
      button.title = file.path;

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
      .filter(
        (file) => file && typeof file.path === "string" && file.path !== "",
      )
      .map((file) => {
        const size = Number(file.size);
        return {
          path: file.path,
          content: typeof file.content === "string" ? file.content : "",
          size: Number.isFinite(size) && size >= 0 ? size : 0,
          language: typeof file.language === "string" ? file.language : "",
          highlighted:
            typeof file.highlighted === "string" ? file.highlighted : "",
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
      setError(
        "Could not load the preview. Check your connection and try again.",
      );
      previewStatus.textContent = "Preview unavailable";
    }
  }

  function schedulePreview() {
    window.clearTimeout(previewTimer);
    previewTimer = window.setTimeout(() => {
      void loadPreview();
    }, PREVIEW_DEBOUNCE_MS);
  }

  function validateField(input, errorElement, pattern, message) {
    const value = input.value;
    if (input === packageInput && value === "") {
      input.removeAttribute("aria-invalid");
      errorElement.textContent = "";
      errorElement.hidden = true;
      return;
    }
    if (value === "" || !pattern.test(value)) {
      input.setAttribute("aria-invalid", "true");
      errorElement.textContent = message;
      errorElement.hidden = false;
      return;
    }
    input.removeAttribute("aria-invalid");
    errorElement.textContent = "";
    errorElement.hidden = true;
  }

  function validateInline() {
    validateField(
      nameInput,
      nameError,
      NAME_PATTERN,
      "Use lowercase letters, digits, hyphens, or underscores, starting with a letter.",
    );
    validateField(
      packageInput,
      packageError,
      PACKAGE_PATTERN,
      "Use lowercase letters, digits, and underscores, starting with a letter or underscore.",
    );
  }

  function stateChanged() {
    clearError();
    validateInline();
    updateUrl();
    schedulePreview();
  }

  function applyFilter() {
    const term = dependencySearch.value.trim().toLowerCase();
    let visibleTotal = 0;
    for (const group of dependencyGroups.querySelectorAll(
      ".dependency-group",
    )) {
      let visibleCount = 0;
      for (const option of group.querySelectorAll(".dependency-option")) {
        const haystack =
          option instanceof HTMLElement ? option.dataset.search ?? "" : "";
        const visible = term === "" || haystack.includes(term);
        if (option instanceof HTMLElement) {
          option.hidden = !visible;
        }
        if (visible) {
          visibleCount += 1;
        }
      }
      visibleTotal += visibleCount;
      if (group instanceof HTMLElement) {
        group.hidden = visibleCount === 0;
        const groupCount = group.querySelector("[data-group-count]");
        if (groupCount) {
          groupCount.textContent = String(visibleCount);
        }
      }
    }
    dependencyEmpty.hidden = visibleTotal > 0;
  }

  function generateUrl() {
    const output = OUTPUTS[outputSelect.value] ?? OUTPUTS.zip;
    return `${output.path}?${stateParams(currentState()).toString()}`;
  }

  function filenameFromResponse(response, output, projectName) {
    const disposition = response.headers.get("content-disposition") ?? "";
    const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
    if (encoded) {
      try {
        return decodeURIComponent(encoded[1].replace(/["']/g, "").trim());
      } catch {
        return encoded[1].replace(/["']/g, "").trim();
      }
    }
    const plain = /filename="?([^";]+)"?/i.exec(disposition);
    if (plain) {
      return plain[1].trim();
    }
    const safeName = projectName.replace(/[^a-z0-9._-]+/gi, "-") || "project";
    const selected = OUTPUTS[output] ?? OUTPUTS.zip;
    if (selected.filename !== null) {
      return selected.filename;
    }
    return `${safeName}${selected.extension}`;
  }

  async function downloadProject() {
    if (!metadata) {
      return;
    }
    clearError();
    updateUrl();
    window.clearTimeout(previewTimer);
    const output = outputSelect.value;
    const state = currentState();
    const url = generateUrl();
    const originalLabel = generateButton.textContent ?? "Generate";
    generateButton.disabled = true;
    generateButton.textContent = "Generating…";

    try {
      const response = await fetch(url, {
        headers: { Accept: "*/*" },
      });
      if (!response.ok) {
        setError(await responseError(response));
        return;
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filenameFromResponse(response, output, state.name);
      anchor.rel = "noopener";
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
    } catch {
      setError(
        "Could not generate the project. Check your connection and try again.",
      );
    } finally {
      generateButton.disabled = false;
      generateButton.textContent = originalLabel;
    }
  }

  function showCopiedState() {
    const originalLabel = shareButton.dataset.label ?? "Share";
    shareButton.dataset.label = originalLabel;
    shareButton.textContent = "Copied";
    shareButton.classList.add("is-copied");
    window.clearTimeout(shareTimer);
    shareTimer = window.setTimeout(() => {
      shareButton.textContent = originalLabel;
      shareButton.classList.remove("is-copied");
    }, 1600);
  }

  async function shareProject() {
    clearError();
    updateUrl();
    try {
      if (!navigator.clipboard) {
        throw new Error("Clipboard unavailable");
      }
      await navigator.clipboard.writeText(window.location.href);
      showCopiedState();
    } catch {
      setError(
        "Could not copy the share link. Copy the address bar URL manually.",
      );
    }
  }

  function resetForm() {
    if (!metadata) {
      return;
    }
    clearError();
    nameInput.value = metadata.project.name.default;
    packageInput.value = metadata.project.package.default;
    descriptionInput.value = metadata.project.description.default;
    versionInput.value = metadata.project.version.default;
    authorInput.value = metadata.project.author.default;
    baseDirInput.value = metadata.baseDir.default;
    applicationNameInput.value = metadata.applicationName.default;
    pythonSelect.value = metadata.python.default;
    fastapiSelect.value = metadata.fastapi.default;
    packageTouched = false;
    dependencySearch.value = "";
    applySelection(new Set());
    syncDependencyState();
    applyFilter();
    validateInline();
    projectLabel.textContent = nameInput.value;
    stateChanged();
    nameInput.focus();
  }

  form.addEventListener("input", (event) => {
    if (!metadata) {
      return;
    }
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target instanceof HTMLInputElement && target.name === "dependencies") {
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
    lastDependencyId = target.value;
    const selected = new Set(getCheckedIds());
    const nextSelected = target.checked
      ? reconcileSelection(selected, target.value)
      : reconcileSelection(removeDependents(selected, [target.value]), null);
    applySelection(nextSelected);
    syncDependencyState();
    stateChanged();
  });

  dependencyGroups.addEventListener("click", (event) => {
    if (!metadata) {
      return;
    }
    const target = event.target;
    if (
      !(target instanceof HTMLInputElement) ||
      target.name !== "dependencies"
    ) {
      return;
    }
    if (!event.shiftKey || lastDependencyId === null) {
      lastDependencyId = target.value;
      return;
    }

    const inputs = dependencyInputs().filter((input) => {
      const option = input.closest(".dependency-option");
      return option instanceof HTMLElement && !option.hidden;
    });
    const currentIndex = inputs.indexOf(target);
    const anchorIndex = inputs.findIndex(
      (input) => input.value === lastDependencyId,
    );
    if (currentIndex < 0 || anchorIndex < 0) {
      lastDependencyId = target.value;
      return;
    }

    event.preventDefault();
    const desired = !target.checked;
    const start = Math.min(currentIndex, anchorIndex);
    const end = Math.max(currentIndex, anchorIndex);
    const selected = new Set(getCheckedIds());
    const removed = [];
    for (let index = start; index <= end; index += 1) {
      const input = inputs[index];
      if (desired) {
        if (!input.disabled) {
          selected.add(input.value);
        }
      } else if (input.checked) {
        selected.delete(input.value);
        removed.push(input.value);
      }
    }
    const nextSelected = reconcileSelection(
      removeDependents(selected, removed),
      target.value,
    );
    applySelection(nextSelected);
    syncDependencyState();
    lastDependencyId = target.value;
    stateChanged();
  });

  dependencySearch.addEventListener("input", () => {
    applyFilter();
  });

  clearSearchButton.addEventListener("click", () => {
    dependencySearch.value = "";
    applyFilter();
    dependencySearch.focus();
  });

  form.addEventListener("submit", (event) => {
    if (!metadata) {
      return;
    }
    event.preventDefault();
    void downloadProject();
  });

  shareButton.addEventListener("click", () => {
    void shareProject();
  });

  resetButton.addEventListener("click", () => {
    resetForm();
  });

  document.addEventListener("keydown", (event) => {
    if (
      (event.ctrlKey || event.metaKey) &&
      !event.altKey &&
      event.key === "Enter"
    ) {
      if (!metadata) {
        return;
      }
      event.preventDefault();
      void downloadProject();
    }
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
        !payload.fastapi ||
        !Array.isArray(payload.fastapi.values) ||
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
      setError(
        "Could not load project options. Check your connection and reload.",
      );
      previewStatus.textContent = "Options unavailable";
    }
  }

  void loadMetadata();
})();
