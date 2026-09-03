/**
 * Digital Food Waste Reduction and Awareness System
 * Frontend JavaScript Utilities and Dynamic Interactivity
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Initialize Bootstrap Tooltips & Popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 2. Auto dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // 3. Client-Side Table Filter & Search helper
    setupTableFilter('inventorySearchInput', 'inventoryCategoryFilter', 'inventoryStatusFilter', 'inventoryTable');
    setupTableFilter('wasteSearchInput', 'wasteCategoryFilter', 'wasteReasonFilter', 'wasteTable');
    setupTableFilter('surveySearchInput', 'householdSizeFilter', 'wasteFreqFilter', 'surveyTable');
});

/**
 * Generic multi-criteria table filter function
 */
function setupTableFilter(searchInputId, filter1Id, filter2Id, tableId) {
    const searchInput = document.getElementById(searchInputId);
    const filter1 = document.getElementById(filter1Id);
    const filter2 = document.getElementById(filter2Id);
    const table = document.getElementById(tableId);

    if (!table) return;

    function applyFilter() {
        const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
        const f1Val = filter1 ? filter1.value.toLowerCase().trim() : '';
        const f2Val = filter2 ? filter2.value.toLowerCase().trim() : '';

        const rows = table.querySelectorAll('tbody tr');
        let visibleCount = 0;

        rows.forEach(row => {
            if (row.classList.contains('no-records-row')) return;

            const text = row.innerText.toLowerCase();
            const matchesSearch = !query || text.includes(query);

            const rowF1 = row.getAttribute('data-filter1') || '';
            const rowF2 = row.getAttribute('data-filter2') || '';

            const matchesF1 = !f1Val || rowF1.toLowerCase() === f1Val;
            const matchesF2 = !f2Val || rowF2.toLowerCase() === f2Val;

            if (matchesSearch && matchesF1 && matchesF2) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        const noMatchRow = document.getElementById(tableId + 'NoMatch');
        if (noMatchRow) {
            noMatchRow.style.display = (visibleCount === 0 && rows.length > 0) ? '' : 'none';
        }
    }

    if (searchInput) searchInput.addEventListener('input', applyFilter);
    if (filter1) filter1.addEventListener('change', applyFilter);
    if (filter2) filter2.addEventListener('change', applyFilter);
}

/**
 * Chart Creation Helpers (Chart.js)
 */
const ChartPalette = {
    emerald: '#059669',
    teal: '#0d9488',
    amber: '#f59e0b',
    red: '#ef4444',
    blue: '#3b82f6',
    purple: '#8b5cf6',
    pink: '#ec4899',
    gray: '#64748b',
    colors: [
        '#059669', '#0d9488', '#f59e0b', '#ef4444', '#3b82f6',
        '#8b5cf6', '#ec4899', '#14b8a6', '#6366f1', '#eab308'
    ]
};

function createDoughnutChart(canvasId, labels, data, title) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !data || data.length === 0 || data.reduce((a, b) => a + b, 0) === 0) return null;

    return new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ChartPalette.colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, font: { size: 12, family: 'Plus Jakarta Sans' }, padding: 15 }
                },
                title: {
                    display: !!title,
                    text: title,
                    font: { size: 14, weight: '600' }
                }
            },
            cutout: '65%'
        }
    });
}

function createBarChart(canvasId, labels, data, labelName, isHorizontal = false) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !data || data.length === 0) return null;

    return new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: labelName || 'Count',
                data: data,
                backgroundColor: ChartPalette.emerald,
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            indexAxis: isHorizontal ? 'y' : 'x',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return `${context.dataset.label}: ${context.raw}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { family: 'Plus Jakarta Sans', size: 11 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: '#f1f5f9' },
                    ticks: { precision: 0, font: { family: 'Plus Jakarta Sans', size: 11 } }
                }
            }
        }
    });
}

function createLineChart(canvasId, labels, data, labelName) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !data || data.length === 0) return null;

    return new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: labelName || 'Value',
                data: data,
                borderColor: ChartPalette.emerald,
                backgroundColor: 'rgba(5, 150, 105, 0.1)',
                borderWidth: 2.5,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: ChartPalette.emerald,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true,
                    grid: { color: '#f1f5f9' }
                }
            }
        }
    });
}
