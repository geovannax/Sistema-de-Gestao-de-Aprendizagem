function limitGridRows(gridId, btnId, maxRows) {
    var grid = document.getElementById(gridId);
    if (!grid || !grid.classList.contains('turmas-grid')) return;
    var items = Array.from(grid.children);
    if (items.length === 0) return;

    // Three independent column-count methods; take the maximum so that if any
    // one is correct we use the right value, even when others undercount.

    // 1. CSS computed: resolved track sizes come back as "522px 522px 522px 522px"
    var colsCSS = 0;
    try {
        var tracks = window.getComputedStyle(grid).gridTemplateColumns.trim().split(/\s+/);
        colsCSS = tracks.filter(function(t) { return /^\d/.test(t); }).length;
    } catch (e) {}

    // 2. Top-position: items in the same grid row share the same top offset
    //    (CSS grid stretches them). 20 px tolerance absorbs sub-pixel rendering
    //    noise (~1-2 px) while staying well below the minimum row height (~60 px).
    var colsTop = 0;
    var firstTop = items[0].getBoundingClientRect().top;
    for (var i = 0; i < items.length; i++) {
        if (items[i].getBoundingClientRect().top > firstTop + 20) break;
        colsTop = i + 1;
    }

    // 3. Left-position: within a row, left always increases by ~columnWidth (360px+).
    //    When it decreases the next row has started.
    var colsLeft = 1;
    var prevLeft = items[0].getBoundingClientRect().left;
    for (var i = 1; i < items.length; i++) {
        var curLeft = items[i].getBoundingClientRect().left;
        if (curLeft < prevLeft) break;
        prevLeft = curLeft;
        colsLeft++;
    }

    var cols = Math.max(colsCSS, colsTop, colsLeft, 1);

    var maxVisible = cols * maxRows;
    if (items.length <= maxVisible) return;

    items.slice(maxVisible).forEach(function(el) {
        el.classList.add('grid-extra', 'd-none');
    });

    var btn = document.getElementById(btnId);
    if (btn) btn.classList.remove('d-none');
}

function expandGrid(gridId, btnId) {
    document.querySelectorAll('#' + gridId + ' .grid-extra').forEach(function(el) {
        el.classList.remove('d-none');
    });
    var btn = document.getElementById(btnId);
    if (btn) btn.remove();
}
