function toggleEmptyState() {
    const aside = document.getElementById('page-aside');
    const emptyState = document.getElementById('empty-state-aside');
    const finishAction = document.getElementById('finish-activity-action');
    const totalSummary = document.getElementById('exercise-total-summary');

    if (!aside || !emptyState || !finishAction || !totalSummary) return;

    const hasContent = aside.children.length > 0 || aside.textContent.trim().length > 0;

    if (hasContent) {
        emptyState.classList.add('d-none');
        finishAction.classList.remove('d-none');
        totalSummary.classList.remove('d-none');
    } else {
        emptyState.classList.remove('d-none');
        finishAction.classList.add('d-none');
        totalSummary.classList.add('d-none');
    }
}

function updateTotalPoints() {
    const totalPoints = document.getElementById('exercise-total-points');
    const pointElements = document.querySelectorAll('#page-aside .exercise-points-value');

    if (!totalPoints) return;

    const total = Array.from(pointElements).reduce((sum, element) => {
        const value = Number.parseFloat(element.dataset.points || '0');
        return Number.isNaN(value) ? sum : sum + value;
    }, 0);

    totalPoints.textContent = new Intl.NumberFormat('pt-BR', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(total);
}

function updateAsideState() {
    toggleEmptyState();
    updateTotalPoints();
}

document.addEventListener('DOMContentLoaded', updateAsideState);

document.body.addEventListener('htmx:oobAfterSwap', () => {
    requestAnimationFrame(updateAsideState);
});

document.body.addEventListener('htmx:afterSwap', () => {
    requestAnimationFrame(updateAsideState);
});

const observer = new MutationObserver(() => {
    updateAsideState();
});

const pageAside = document.getElementById('page-aside');
if (pageAside) {
    observer.observe(pageAside, {
        childList: true,
        subtree: true,
    });
}
