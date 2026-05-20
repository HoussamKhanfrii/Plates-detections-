let detectionsChart = null;
let sourceChart = null;

function percent(value) {
    return `${Math.round((Number(value) || 0) * 100)}%`;
}

function chartColors() {
    const styles = getComputedStyle(document.documentElement);
    return {
        text: styles.getPropertyValue("--text").trim(),
        muted: styles.getPropertyValue("--muted").trim(),
        line: styles.getPropertyValue("--line").trim(),
        primary: styles.getPropertyValue("--primary").trim(),
        accent: styles.getPropertyValue("--accent").trim(),
        success: styles.getPropertyValue("--success").trim(),
        danger: styles.getPropertyValue("--danger").trim(),
    };
}

function renderRecent(rows) {
    const body = document.querySelector("#recentDetectionsBody");
    if (!body) return;

    if (!rows.length) {
        body.innerHTML = `<tr><td colspan="6">No detections yet.</td></tr>`;
        return;
    }

    body.innerHTML = rows.map((row) => `
        <tr>
            <td><strong>${row.plate_number || "UNREADABLE"}</strong></td>
            <td><span class="source-badge">${row.source_type || ""}</span></td>
            <td>${row.detector_name || "Unknown detector"}</td>
            <td>${percent(row.detection_confidence)}</td>
            <td>${percent(row.ocr_confidence)}</td>
            <td>${row.created_at || ""}</td>
        </tr>
    `).join("");
}

function renderCharts(stats) {
    const colors = chartColors();
    const dayCanvas = document.querySelector("#detectionsByDayChart");
    const sourceCanvas = document.querySelector("#sourceDistributionChart");

    if (detectionsChart) detectionsChart.destroy();
    if (sourceChart) sourceChart.destroy();

    detectionsChart = new Chart(dayCanvas, {
        type: "line",
        data: {
            labels: stats.detections_by_day.map((item) => item.day),
            datasets: [{
                label: "Detections",
                data: stats.detections_by_day.map((item) => item.count),
                borderColor: colors.primary,
                backgroundColor: "rgba(35, 100, 210, 0.16)",
                borderWidth: 3,
                tension: 0.35,
                fill: true,
                pointRadius: 4,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: colors.muted }, grid: { color: colors.line } },
                y: { beginAtZero: true, ticks: { color: colors.muted, precision: 0 }, grid: { color: colors.line } },
            },
        },
    });

    sourceChart = new Chart(sourceCanvas, {
        type: "doughnut",
        data: {
            labels: stats.source_distribution.map((item) => item.source_type),
            datasets: [{
                data: stats.source_distribution.map((item) => item.count),
                backgroundColor: [colors.primary, colors.accent, colors.success, colors.danger],
                borderColor: colors.line,
                borderWidth: 2,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: colors.text },
                },
            },
        },
    });
}

async function loadDashboard() {
    const response = await fetch("/api/dashboard/stats");
    const data = await response.json();
    if (!data.success) return;

    const stats = data.stats;
    document.querySelector("#totalDetections").textContent = stats.total_detections;
    document.querySelector("#detectionsToday").textContent = stats.detections_today;
    document.querySelector("#avgDetectionConfidence").textContent = percent(stats.avg_detection_confidence);
    document.querySelector("#avgOcrConfidence").textContent = percent(stats.avg_ocr_confidence);

    renderCharts(stats);
    renderRecent(stats.recent_detections);
    lucide.createIcons();
}

document.addEventListener("DOMContentLoaded", loadDashboard);
