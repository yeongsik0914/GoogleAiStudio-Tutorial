(function() {
    try {
        const pDoc = window.parent.document;
        if (!pDoc) return;
        
        window.parent.openDrawer = function() {
            const bd = pDoc.getElementById('yt-drawer-backdrop');
            const pn = pDoc.getElementById('yt-drawer-panel');
            if (bd) bd.classList.add('open');
            if (pn) pn.classList.add('open');
        };
        window.parent.closeDrawer = function() {
            const bd = pDoc.getElementById('yt-drawer-backdrop');
            const pn = pDoc.getElementById('yt-drawer-panel');
            if (bd) bd.classList.remove('open');
            if (pn) pn.classList.remove('open');
        };
        window.parent.toggleDrawer = function() {
            const pn = pDoc.getElementById('yt-drawer-panel');
            if (pn && pn.classList.contains('open')) {
                window.parent.closeDrawer();
            } else {
                window.parent.openDrawer();
            }
        };

        window.parent.filterDrawerVideos = function(query) {
            const q = (query || '').toLowerCase().trim();
            const cards = pDoc.querySelectorAll('.d-video-card');
            let matchCount = 0;
            cards.forEach(function(card) {
                const title = (card.getAttribute('data-title') || '').toLowerCase();
                const uploader = (card.getAttribute('data-uploader') || '').toLowerCase();
                if (!q || title.includes(q) || uploader.includes(q)) {
                    card.style.display = 'flex';
                    matchCount++;
                } else {
                    card.style.display = 'none';
                }
            });
            const emptyNotice = pDoc.getElementById('d-filter-empty');
            if (emptyNotice) {
                emptyNotice.style.display = (matchCount === 0 && cards.length > 0) ? 'block' : 'none';
            }
        };

        window.parent.filterDrawerCategory = function(cat, btnElem) {
            if (btnElem) {
                const chips = pDoc.querySelectorAll('.d-cat-chip');
                chips.forEach(c => c.classList.remove('active'));
                btnElem.classList.add('active');
            }
            const input = pDoc.getElementById('d-drawer-search-input');
            if (cat === 'all') {
                if (input) input.value = '';
                window.parent.filterDrawerVideos('');
            } else {
                if (input) input.value = cat;
                window.parent.filterDrawerVideos(cat);
            }
        };

        // 기존 이벤트 리스너 중복 방지 정리
        if (pDoc.__yt_drawer_click_handler) {
            pDoc.removeEventListener('click', pDoc.__yt_drawer_click_handler, true);
        }
        if (pDoc.__yt_drawer_key_handler) {
            pDoc.removeEventListener('keydown', pDoc.__yt_drawer_key_handler);
        }

        pDoc.__yt_drawer_click_handler = function(e) {
            // 1. 햄버거 메뉴바 버튼 클릭 시: 토글 동작 (열려있으면 닫고, 닫혀있으면 엶)
            const hamBtn = e.target.closest('#yt-hamburger-btn');
            if (hamBtn) {
                e.preventDefault();
                e.stopPropagation();
                window.parent.toggleDrawer();
                return;
            }

            // 2. 드로어 상단 닫기 버튼 클릭 시: 닫기
            const closeBtn = e.target.closest('#d-close-drawer-btn, .d-close-drawer-btn');
            if (closeBtn) {
                e.preventDefault();
                e.stopPropagation();
                window.parent.closeDrawer();
                return;
            }

            // 3. 드로어 바깥 배경(Backdrop) 클릭 시: 닫기
            if (e.target.id === 'yt-drawer-backdrop' || e.target.classList.contains('yt-drawer-backdrop')) {
                e.preventDefault();
                e.stopPropagation();
                window.parent.closeDrawer();
                return;
            }

            // 4. 드로어가 열려있는 상태에서 카테고리/드로어 패널 영역 밖을 클릭한 경우: 닫기
            const pn = pDoc.getElementById('yt-drawer-panel');
            if (pn && pn.classList.contains('open')) {
                if (!pn.contains(e.target)) {
                    window.parent.closeDrawer();
                }
            }
        };

        pDoc.__yt_drawer_key_handler = function(e) {
            if (e.key === 'Escape') {
                window.parent.closeDrawer();
            }
        };

        // 캡처 단계에서 등록하여 어디서든 안정적으로 동작 보장
        pDoc.addEventListener('click', pDoc.__yt_drawer_click_handler, true);
        pDoc.addEventListener('keydown', pDoc.__yt_drawer_key_handler);

    } catch(err) {
        console.warn("[Drawer Script Warning]", err);
    }
})();
