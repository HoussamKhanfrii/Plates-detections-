const qs = (selector, scope = document) => scope.querySelector(selector);
const qsa = (selector, scope = document) => [...scope.querySelectorAll(selector)];

function showToast(message) {
    const toast = qs("#toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 4200);
}

function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("lp-theme", theme);
}

function initTheme() {
    const saved = localStorage.getItem("lp-theme") || "light";
    setTheme(saved);
    const toggle = qs("[data-theme-toggle]");
    if (toggle) {
        toggle.addEventListener("click", () => {
            setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
        });
    }
}

function setupDropZones() {
    qsa("[data-drop-zone]").forEach((zone) => {
        const input = qs("input[type='file']", zone);
        if (!input) return;

        ["dragenter", "dragover"].forEach((eventName) => {
            zone.addEventListener(eventName, (event) => {
                event.preventDefault();
                zone.classList.add("drag-over");
            });
        });

        ["dragleave", "drop"].forEach((eventName) => {
            zone.addEventListener(eventName, (event) => {
                event.preventDefault();
                zone.classList.remove("drag-over");
            });
        });

        zone.addEventListener("drop", (event) => {
            input.files = event.dataTransfer.files;
            input.dispatchEvent(new Event("change"));
        });
    });
}

function confidencePercent(value) {
    return `${Math.round((Number(value) || 0) * 100)}%`;
}

function detectionCard(record) {
    const crop = record.plate_crop_path || "";
    const resultUrl = record.id ? `/result/${record.id}` : "#";
    return `
        <article class="detection-card">
            <img src="${crop}" alt="Plate crop">
            <div>
                <strong class="plate-title">${record.plate_number || "UNREADABLE"}</strong>
                <p>Detection ${confidencePercent(record.detection_confidence)} | OCR ${confidencePercent(record.ocr_confidence)}</p>
                <p>Model: ${record.detector_name || record.detector || "Unknown detector"}</p>
                <p>Raw OCR: ${record.raw_ocr_text || "No text"}</p>
                ${record.id ? `<a class="btn small" href="${resultUrl}"><i data-lucide="eye"></i>View result</a>` : ""}
            </div>
        </article>
    `;
}

function renderImageResult(data) {
    const target = qs("#imageResult");
    if (!target) return;

    if (!data.detections || data.detections.length === 0) {
        target.className = "empty-state";
        target.innerHTML = `<i data-lucide="circle-alert"></i><p>${data.message || "No plate detected."}</p>`;
    } else {
        target.className = "result-card-list";
        const resultImage = data.result_image_path
            ? `<img class="result-image" src="${data.result_image_path}" alt="Detected plate result">`
            : "";
        target.innerHTML = `${resultImage}${data.detections.map(detectionCard).join("")}`;
    }
    lucide.createIcons();
}

function renderVideoResult(data) {
    const target = qs("#videoResult");
    if (!target) return;

    const video = data.processed_video_path
        ? `<video class="media-preview" style="display:block" controls src="${data.processed_video_path}"></video>`
        : "";
    const detections = data.detections && data.detections.length
        ? `<div class="result-card-list">${data.detections.map(detectionCard).join("")}</div>`
        : `<div class="empty-state"><i data-lucide="circle-alert"></i><p>No plates were detected in sampled frames.</p></div>`;

    target.className = "result-card-list";
    target.innerHTML = `${video}${detections}`;
    lucide.createIcons();
}

function initImageUpload() {
    const form = qs("#imageUploadForm");
    const input = qs("#imageInput");
    const preview = qs("#imagePreview");
    const loader = qs("#imageLoader");
    if (!form || !input) return;

    input.addEventListener("change", () => {
        const file = input.files[0];
        if (!file || !preview) return;
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!input.files[0]) {
            showToast("Choose an image first.");
            return;
        }

        const formData = new FormData();
        formData.append("image", input.files[0]);
        loader?.classList.remove("hidden");

        try {
            const response = await fetch("/api/detect/image", { method: "POST", body: formData });
            const data = await response.json();
            if (!data.success) throw new Error(data.error || "Image detection failed.");
            renderImageResult(data);
            showToast(data.message || "Detection complete.");
        } catch (error) {
            showToast(error.message);
        } finally {
            loader?.classList.add("hidden");
        }
    });
}

function initVideoUpload() {
    const form = qs("#videoUploadForm");
    const input = qs("#videoInput");
    const preview = qs("#videoPreview");
    const loader = qs("#videoLoader");
    if (!form || !input) return;

    input.addEventListener("change", () => {
        const file = input.files[0];
        if (!file || !preview) return;
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!input.files[0]) {
            showToast("Choose a video first.");
            return;
        }

        const formData = new FormData();
        formData.append("video", input.files[0]);
        loader?.classList.remove("hidden");

        try {
            const response = await fetch("/api/detect/video", { method: "POST", body: formData });
            const data = await response.json();
            if (!data.success) throw new Error(data.error || "Video processing failed.");
            renderVideoResult(data);
            showToast(`Processed ${data.frames_processed || 0} frames.`);
        } catch (error) {
            showToast(error.message);
        } finally {
            loader?.classList.add("hidden");
        }
    });
}

function initWebcam() {
    const start = qs("#startWebcamBtn");
    const stop = qs("#stopWebcamBtn");
    const stream = qs("#webcamStream");
    const placeholder = qs("#webcamPlaceholder");
    const latest = qs("#latestWebcamDetection");
    let pollTimer = null;

    if (!start || !stop || !stream) return;

    const pollLatest = async () => {
        try {
            const response = await fetch("/api/webcam/latest");
            const data = await response.json();
            const detection = data.latest_detection;
            if (detection && latest) {
                latest.innerHTML = `
                    <span class="plate-number">${detection.plate_number}</span>
                    <small>Detection ${confidencePercent(detection.detection_confidence)} | OCR ${confidencePercent(detection.ocr_confidence)}</small>
                    <small>Model: ${detection.detector_name || detection.detector || "Unknown detector"}</small>
                `;
            }
        } catch (_error) {
            window.clearInterval(pollTimer);
        }
    };

    start.addEventListener("click", () => {
        stream.src = `/video_feed?ts=${Date.now()}`;
        stream.style.display = "block";
        placeholder?.classList.add("hidden");
        window.clearInterval(pollTimer);
        pollTimer = window.setInterval(pollLatest, 1500);
        showToast("Webcam stream started.");
    });

    stop.addEventListener("click", async () => {
        await fetch("/api/webcam/stop", { method: "POST" });
        stream.removeAttribute("src");
        stream.style.display = "none";
        placeholder?.classList.remove("hidden");
        window.clearInterval(pollTimer);
        showToast("Webcam stream stopped.");
    });
}

function buildHistoryRow(item) {
    return `
        <tr>
            <td><strong>${item.plate_number || "UNREADABLE"}</strong></td>
            <td><img class="table-thumb" src="${item.plate_crop_path || ""}" alt="Plate crop"></td>
            <td><span class="source-badge">${item.source_type || ""}</span></td>
            <td>${item.detector_name || "Unknown detector"}</td>
            <td>${confidencePercent(item.detection_confidence)}</td>
            <td>${confidencePercent(item.ocr_confidence)}</td>
            <td>${item.created_at || ""}</td>
            <td class="table-actions">
                <a class="icon-btn" href="/result/${item.id}" title="View"><i data-lucide="eye"></i></a>
                <button class="icon-btn danger" type="button" data-delete-id="${item.id}" title="Delete"><i data-lucide="trash-2"></i></button>
            </td>
        </tr>
    `;
}

function initHistory() {
    const form = qs("#historyFilters");
    const body = qs("#historyTableBody");
    const count = qs("#historyCount");
    const exportCsv = qs("#exportCsvBtn");
    const exportPdf = qs("#exportPdfBtn");
    if (!form || !body) return;

    const updateExports = (params) => {
        exportCsv.href = `/api/export?format=csv&${params.toString()}`;
        exportPdf.href = `/api/export?format=pdf&${params.toString()}`;
    };

    const loadHistory = async () => {
        const params = new URLSearchParams(new FormData(form));
        updateExports(params);
        const response = await fetch(`/api/history?${params.toString()}`);
        const data = await response.json();
        if (!data.success) return;
        body.innerHTML = data.detections.map(buildHistoryRow).join("");
        count.textContent = `${data.detections.length} rows`;
        lucide.createIcons();
    };

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        loadHistory();
    });

    body.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-delete-id]");
        if (!button) return;
        const id = button.dataset.deleteId;
        if (!confirm("Delete this detection record?")) return;
        const response = await fetch(`/api/history/${id}`, { method: "DELETE" });
        const data = await response.json();
        if (!data.success) {
            showToast(data.error || "Delete failed.");
            return;
        }
        showToast("Detection deleted.");
        loadHistory();
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    setupDropZones();
    initImageUpload();
    initVideoUpload();
    initWebcam();
    initHistory();
});
