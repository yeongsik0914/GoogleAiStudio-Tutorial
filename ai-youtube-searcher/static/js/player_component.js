            var segments = window.__PLAYER_CONFIG__.segments || [];
            var chapters = window.__PLAYER_CONFIG__.chapters || [];
            var player;
            var currentActiveIdx = -1;
            var isUserScrolling = false;
            var scrollTimeout;
            var apiKey = window.__PLAYER_CONFIG__.apiKey || "";
            var isExpandedView = false;
            var isTheaterMode = false;
            var isMuted = false;
            var lastVolume = 100;
            var videoTitleSafe = window.__PLAYER_CONFIG__.videoTitleSafe || "";

            // YouTube IFrame API 로드
            var tag = document.createElement('script');
            tag.src = "https://www.youtube.com/iframe_api";
            var firstScriptTag = document.getElementsByTagName('script')[0];
            firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

            function onYouTubeIframeAPIReady() {
                player = new YT.Player('yt-player', {
                    videoId: window.__PLAYER_CONFIG__.videoId,
                    playerVars: {
                        'autoplay': 1,
                        'playsinline': 1,
                        'rel': 0,
                        'modestbranding': 1
                    },
                    events: {
                        'onReady': onPlayerReady
                    }
                });
            }

            function fmtSec(sec) {
                var total = Math.floor(Math.max(0, sec));
                var h = Math.floor(total / 3600);
                var m = Math.floor((total % 3600) / 60);
                var s = total % 60;
                if (h > 0) {
                    return (h < 10 ? "0" + h : h) + ":" + (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
                }
                return (m < 10 ? "0" + m : m) + ":" + (s < 10 ? "0" + s : s);
            }

            function onPlayerReady(event) {
                event.target.setVolume(100);
                event.target.playVideo();
                renderTranscriptList(segments);
                renderChapters(chapters);

                var dur = event.target.getDuration();
                if (dur > 0) {
                    document.getElementById('time-total').innerText = fmtSec(dur);
                }

                // 150ms 고속 정밀 싱크 타이머
                setInterval(syncPlaybackAndTranscript, 150);
            }

            function changeVol(v) {
                if (player && player.setVolume) {
                    player.setVolume(v);
                    lastVolume = v;
                    document.getElementById('vol-badge').innerText = v + "%";
                    if (v > 0 && isMuted) {
                        isMuted = false;
                        player.unMute();
                    }
                }
            }

            function toggleMute() {
                if (!player) return;
                var slider = document.querySelector('.yt-vol-slider');
                var badge = document.getElementById('vol-badge');
                if (isMuted) {
                    player.unMute();
                    player.setVolume(lastVolume);
                    slider.value = lastVolume;
                    badge.innerText = lastVolume + "%";
                    isMuted = false;
                } else {
                    lastVolume = player.getVolume() || 100;
                    player.mute();
                    slider.value = 0;
                    badge.innerText = "0%";
                    isMuted = true;
                }
            }

            function skipRelative(delta) {
                if (player && player.getCurrentTime && player.seekTo) {
                    var cur = player.getCurrentTime();
                    var dur = player.getDuration() || 0;
                    var next = Math.max(0, Math.min(dur, cur + delta));
                    player.seekTo(next, true);
                }
            }

            function changeSpeed(rate) {
                if (player && player.setPlaybackRate) {
                    player.setPlaybackRate(parseFloat(rate));
                }
            }

            function jumpTo(sec) {
                if (player && player.seekTo) {
                    player.seekTo(sec, true);
                    player.playVideo();
                }
            }

            function copyLiveCaption() {
                var txt = document.getElementById('live-text-display').innerText;
                if (!txt) return;
                var btn = document.getElementById('copy-cap-btn');
                navigator.clipboard.writeText(txt).then(function() {
                    btn.innerText = "복사됨";
                    setTimeout(function() { btn.innerText = "복사"; }, 1500);
                }).catch(function() {
                    btn.innerText = "실패";
                    setTimeout(function() { btn.innerText = "복사"; }, 1500);
                });
            }

            // ----------------------------------------------------
            // 파일 다운로드 기능 (다운로드 탭 연동)
            // ----------------------------------------------------
            function downloadTranscriptTxt(withTimestamp) {
                if (!segments || segments.length === 0) {
                    alert("다운로드할 대본 데이터가 없습니다.");
                    return;
                }
                var textLines;
                if (withTimestamp) {
                    textLines = segments.map(function(s) {
                        return "[" + s.time_str + "] " + s.text;
                    });
                } else {
                    textLines = segments.map(function(s) {
                        return s.text;
                    });
                }
                var fullText = textLines.join("\\n");
                var blob = new Blob([fullText], { type: "text/plain;charset=utf-8" });
                var url = URL.createObjectURL(blob);
                var a = document.createElement("a");
                a.href = url;
                a.download = videoTitleSafe + (withTimestamp ? "_timestamps.txt" : "_transcript.txt");
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }

            function copyAllTranscript() {
                if (!segments || segments.length === 0) return;
                var fullText = segments.map(function(s) {
                    return "[" + s.time_str + "] " + s.text;
                }).join("\\n");
                navigator.clipboard.writeText(fullText).then(function() {
                    var btn = document.getElementById('copy-all-btn');
                    if (btn) {
                        btn.innerText = "전체 복사 완료";
                        setTimeout(function() { btn.innerText = "전체 복사"; }, 1500);
                    }
                });
            }

            function downloadAudioFile() {
                var b64Data = window.__PLAYER_CONFIG__.audioB64 || "";
                if (!b64Data) {
                    alert("오디오 데이터가 준비되지 않았습니다.");
                    return;
                }
                try {
                    var byteCharacters = atob(b64Data);
                    var byteNumbers = new Array(byteCharacters.length);
                    for (var i = 0; i < byteCharacters.length; i++) {
                        byteNumbers[i] = byteCharacters.charCodeAt(i);
                    }
                    var byteArray = new Uint8Array(byteNumbers);
                    var blob = new Blob([byteArray], { type: "audio/m4a" });
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement("a");
                    a.href = url;
                    a.download = videoTitleSafe + ".m4a";
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                } catch(e) {
                    alert("오디오 다운로드 중 오류: " + e.message);
                }
            }

            // ----------------------------------------------------
            // [핵심 1] 유튜브 마우스 호버 타임라인 & 썸네일/시간대 툴팁
            // ----------------------------------------------------
            var timelineContainer = document.getElementById('timeline-container');
            var hoverTooltip = document.getElementById('hover-tooltip');
            var tooltipTime = document.getElementById('tooltip-time');
            var hoverBar = document.getElementById('hover-bar');
            var playBar = document.getElementById('play-bar');
            var scrubberHandle = document.getElementById('scrubber-handle');

            timelineContainer.addEventListener('mousemove', function(e) {
                if (!player || !player.getDuration) return;
                var dur = player.getDuration();
                if (!dur || dur <= 0) return;

                var rect = timelineContainer.getBoundingClientRect();
                var clickX = e.clientX - rect.left;
                var ratio = Math.max(0, Math.min(1, clickX / rect.width));
                var hoverSeconds = ratio * dur;

                hoverBar.style.width = (ratio * 100) + "%";
                hoverTooltip.style.display = 'block';
                var clampedX = Math.max(70, Math.min(rect.width - 70, clickX));
                hoverTooltip.style.left = clampedX + "px";
                tooltipTime.innerText = fmtSec(hoverSeconds);
            });

            timelineContainer.addEventListener('mouseleave', function() {
                hoverTooltip.style.display = 'none';
                hoverBar.style.width = "0%";
            });

            timelineContainer.addEventListener('click', function(e) {
                if (!player || !player.getDuration) return;
                var dur = player.getDuration();
                if (!dur || dur <= 0) return;

                var rect = timelineContainer.getBoundingClientRect();
                var ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                jumpTo(ratio * dur);
            });

            // ----------------------------------------------------
            // [핵심 2] 정확히 5칸 크기 뷰포트 & 3번째 칸 실시간 음성 대본 고정 싱크
            // ----------------------------------------------------
            var tContainer = document.getElementById('transcript-container');
            var isUserScrolling = false;
            var scrollTimeout;

            tContainer.addEventListener('wheel', function() {
                isUserScrolling = true;
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {
                    isUserScrolling = false;
                }, 2500);
            }, { passive: true });

            tContainer.addEventListener('touchmove', function() {
                isUserScrolling = true;
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(function() {
                    isUserScrolling = false;
                }, 2500);
            }, { passive: true });

            function syncPlaybackAndTranscript(forceSync) {
                if (!player || !player.getCurrentTime) return;
                var cur = player.getCurrentTime();
                var dur = player.getDuration() || 1;

                // 1. 타임라인 진행률 바 업데이트
                var pct = Math.max(0, Math.min(100, (cur / dur) * 100));
                playBar.style.width = pct + "%";
                scrubberHandle.style.left = pct + "%";
                document.getElementById('time-current').innerText = fmtSec(cur);

                if (dur > 1) {
                    document.getElementById('time-total').innerText = fmtSec(dur);
                }

                // 2. 현재 발화 세그먼트 탐색
                var targetIdx = -1;
                for (var i = 0; i < segments.length; i++) {
                    if (cur >= segments[i].start && cur <= (segments[i].end + 0.35)) {
                        targetIdx = i;
                        break;
                    }
                }
                if (targetIdx === -1) {
                    for (var j = segments.length - 1; j >= 0; j--) {
                        if (cur >= segments[j].start) {
                            targetIdx = j;
                            break;
                        }
                    }
                }

                // 3. 3번째 칸 현재 음성 대본 동기화
                if (targetIdx !== -1) {
                    var curSeg = segments[targetIdx];
                    var liveTimeEl = document.getElementById('live-time-display');
                    if (liveTimeEl) liveTimeEl.innerText = curSeg.time_str;
                    var liveTextEl = document.getElementById('live-text-display');
                    if (liveTextEl) liveTextEl.innerText = curSeg.text;

                    if (targetIdx !== currentActiveIdx || forceSync) {
                        currentActiveIdx = targetIdx;

                        var prev = document.querySelector('.t-slot-card.active');
                        if (prev) prev.classList.remove('active');

                        var activeEl = document.getElementById('t-card-' + targetIdx);
                        if (activeEl) {
                            activeEl.classList.add('active');

                            if (!isUserScrolling || forceSync) {
                                var slotH = activeEl.offsetHeight;
                                var gap = 7;
                                var targetScrollTop = targetIdx * (slotH + gap);
                                tContainer.scrollTo({
                                    top: targetScrollTop,
                                    behavior: 'smooth'
                                });
                            }
                        }
                    }
                }

                // 4. 챕터 활성 하이라이트 동기화
                if (chapters && chapters.length > 0) {
                    for (var k = 0; k < chapters.length; k++) {
                        var ch = chapters[k];
                        var chEl = document.getElementById('ch-card-' + k);
                        if (chEl) {
                            var nextStart = (k + 1 < chapters.length) ? chapters[k+1].start_seconds : (dur + 1);
                            if (cur >= ch.start_seconds && cur < nextStart) {
                                chEl.classList.add('active');
                            } else {
                                chEl.classList.remove('active');
                            }
                        }
                    }
                }
            }

            // 대본 목록 렌더링 (첫 번째 대본이 3번째 칸에서 시작되도록 상하단에 2칸 빈 공간 배치)
            function renderTranscriptList(list) {
                tContainer.innerHTML = "";
                var countBadge = document.getElementById('t-count-badge');
                if (countBadge) {
                    countBadge.innerText = (list ? list.length : 0) + "개 발화";
                }

                if (!list || list.length === 0) {
                    tContainer.innerHTML = "<div style='color: #888; font-size: 0.9rem; text-align: center; padding: 60px;'>검색 결과가 없습니다.</div>";
                    return;
                }

                // 상단 2칸 빈 공간 (아무 텍스트도 없는 투명 빈 박스)
                var topEmpty1 = document.createElement('div');
                topEmpty1.className = 't-empty-spacer';
                tContainer.appendChild(topEmpty1);

                var topEmpty2 = document.createElement('div');
                topEmpty2.className = 't-empty-spacer';
                tContainer.appendChild(topEmpty2);

                // 발화 카드 목록 (5칸 크기에 맞춘 큼직한 카드)
                list.forEach(function(s, idx) {
                    var card = document.createElement('div');
                    card.className = 't-slot-card';
                    var realIdx = (s.orig_index !== undefined ? s.orig_index : idx);
                    card.id = 't-card-' + realIdx;
                    card.dataset.index = realIdx;
                    card.onclick = function() {
                        jumpTo(s.start);
                    };

                    card.innerHTML = 
                        '<div class="t-slot-header">' +
                            '<span class="t-time-btn">' + s.time_str + '</span>' +
                            '<span class="t-live-badge"><span class="t-pulse-dot"></span>현재 음성 대본</span>' +
                        '</div>' +
                        '<div class="t-content">' + s.text + '</div>';

                    tContainer.appendChild(card);
                });

                // 하단 2칸 빈 공간 (마지막 대본들도 3번째 칸까지 위로 올라갈 수 있도록 여유 공간 제공)
                var btmEmpty1 = document.createElement('div');
                btmEmpty1.className = 't-empty-spacer';
                tContainer.appendChild(btmEmpty1);

                var btmEmpty2 = document.createElement('div');
                btmEmpty2.className = 't-empty-spacer';
                tContainer.appendChild(btmEmpty2);
            }

            // 대본 검색 필터
            var indexedSegments = segments.map(function(s, idx) {
                return { orig_index: idx, start: s.start, end: s.end, time_str: s.time_str, text: s.text };
            });

            function onFilterTranscript(q) {
                var val = (q || '').trim().toLowerCase();
                var filtered = indexedSegments;
                if (val) {
                    filtered = indexedSegments.filter(function(s) {
                        return s.text.toLowerCase().indexOf(val) !== -1;
                    });
                }
                renderTranscriptList(filtered);
                var countBadge = document.getElementById('t-count-badge');
                if (countBadge) {
                    countBadge.innerText = val ? filtered.length + '개 구간' : '';
                }
                if (currentActiveIdx !== -1 && !val) {
                    syncPlaybackAndTranscript(true);
                }
            }

            // 탭 전환
            function switchTab(name) {
                document.querySelectorAll('.tab-chip').forEach(function(el) { el.classList.remove('active'); });
                document.querySelectorAll('.tab-panel').forEach(function(el) { el.classList.remove('active'); });

                var btn = document.getElementById('tab-btn-' + name);
                var panel = document.getElementById('panel-' + name);
                if (btn) btn.classList.add('active');
                if (panel) panel.classList.add('active');
            }

            // ----------------------------------------------------
            // 챗봇 비동기 질의응답 (무중단 실시간 답변)
            // ----------------------------------------------------
            function askPreset(q) {
                document.getElementById('chat-input-field').value = q;
                sendChatQuestion();
            }

            async function sendChatQuestion() {
                var inputEl = document.getElementById('chat-input-field');
                var question = inputEl.value.trim();
                if (!question) return;

                var chatBox = document.getElementById('chat-box');

                var uMsg = document.createElement('div');
                uMsg.className = 'chat-bubble-u';
                uMsg.innerHTML = '<b>질문:</b> ' + question;
                chatBox.appendChild(uMsg);
                inputEl.value = "";

                var loadMsg = document.createElement('div');
                loadMsg.className = 'chat-bubble-a';
                loadMsg.id = 'chat-loading-item';
                loadMsg.innerHTML = '<b>Gemini AI:</b> 답변을 생성하고 있습니다...';
                chatBox.appendChild(loadMsg);
                chatBox.scrollTop = chatBox.scrollHeight;

                if (!apiKey) {
                    loadMsg.innerHTML = '좌측 사이드바에서 Gemini API 키를 먼저 입력해주세요.';
                    return;
                }

                try {
                    var nl = String.fromCharCode(10);
                    var timelineScript = segments.slice(0, 120).map(function(s) {
                        return "[" + s.time_str + "] " + s.text;
                    }).join(nl);

                    var promptText = [
                        "당신은 유튜브 영상 분석 전문가 AI입니다.",
                        "제공된 시간대별 영상 트랜스크립트를 확인하고 질문에 명쾌하고 친절하게 답변하세요.",
                        "답변과 가장 밀접한 영상 속 구간(시작 시간 예: 01:23 및 초 단위)을 찾아 반드시 아래 JSON으로만 응답하세요.",
                        "",
                        "[대본]",
                        timelineScript,
                        "",
                        "[질문]",
                        question,
                        "",
                        "[응답 형식]",
                        "```json",
                        "{",
                        '  "answer": "답변 내용...",',
                        '  "relevant_timestamp": "00:02",',
                        '  "relevant_seconds": 2.0',
                        "}",
                        "```"
                    ].join(nl);

                    var modelsToTry = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview", "gemini-3.8-flash"];
                    var data = null;
                    var lastErrorMsg = "";

                    for (var m = 0; m < modelsToTry.length; m++) {
                        var modelName = modelsToTry[m];
                        try {
                            var resp = await fetch("https://generativelanguage.googleapis.com/v1beta/models/" + modelName + ":generateContent?key=" + apiKey, {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    contents: [{ parts: [{ text: promptText }] }]
                                })
                            });

                            var resJson = await resp.json();
                            if (resp.ok && resJson && resJson.candidates && resJson.candidates.length > 0 && resJson.candidates[0].content) {
                                data = resJson;
                                break;
                            } else if (resJson && resJson.error) {
                                lastErrorMsg = resJson.error.message || ("오류 코드 " + resJson.error.code);
                            }
                        } catch(netErr) {
                            lastErrorMsg = netErr.message;
                        }
                    }

                    if (!data || !data.candidates || data.candidates.length === 0 || !data.candidates[0].content) {
                        throw new Error(lastErrorMsg || "API 응답을 수신하지 못했습니다. 잠시 후 다시 시도해주세요.");
                    }

                    var parts = data.candidates[0].content.parts || [];
                    var rawText = "";
                    for (var p = 0; p < parts.length; p++) {
                        if (parts[p].text) {
                            rawText += parts[p].text;
                        }
                    }

                    if (!rawText.trim()) {
                        throw new Error("답변 텍스트를 추출할 수 없습니다.");
                    }
                    
                    var answerText = rawText;
                    var relTs = "00:00";
                    var relSec = 0;

                    var firstBrace = rawText.indexOf("{");
                    var lastBrace = rawText.lastIndexOf("}");
                    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
                        try {
                            var jsonStr = rawText.substring(firstBrace, lastBrace + 1);
                            var parsed = JSON.parse(jsonStr);
                            answerText = parsed.answer || rawText;
                            relTs = parsed.relevant_timestamp || "00:00";
                            relSec = parseFloat(parsed.relevant_seconds) || 0;
                        } catch(e) {}
                    }

                    loadMsg.remove();
                    var aMsg = document.createElement('div');
                    aMsg.className = 'chat-bubble-a';

                    var tsButton = "";
                    if (relSec > 0 || relTs !== "00:00") {
                        tsButton = '<div style="margin-top: 6px;">' +
                            '<button onclick="jumpTo(' + relSec + ')" style="background: #0f2b4c; border: 1px solid #3ea6ff; color: #3ea6ff; font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; cursor: pointer;">' +
                            '구간 바로가기: [' + relTs + '] (' + Math.floor(relSec) + '초)</button></div>';
                    }

                    aMsg.innerHTML = '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">' +
                        '<span><b>Gemini AI:</b></span>' +
                        '<button onclick="copyChatText(this)" style="background: transparent; border: none; color: #888; font-size: 0.7rem; cursor: pointer;">복사</button>' +
                        '</div>' +
                        '<div class="chat-text-content">' + answerText.split(nl).join('<br>') + '</div>' + tsButton;
                    chatBox.appendChild(aMsg);
                    chatBox.scrollTop = chatBox.scrollHeight;

                } catch(err) {
                    loadMsg.remove();
                    var errMsg = document.createElement('div');
                    errMsg.className = 'chat-bubble-a';
                    errMsg.style.borderColor = '#ff4b4b';
                    errMsg.innerHTML = '답변 생성 중 오류가 발생했습니다: ' + err.message;
                    chatBox.appendChild(errMsg);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
            }

            function copyChatText(btn) {
                var parent = btn.closest('.chat-bubble-a');
                var contentEl = parent.querySelector('.chat-text-content');
                if (contentEl) {
                    navigator.clipboard.writeText(contentEl.innerText).then(function() {
                        btn.innerText = "완료";
                        setTimeout(function() { btn.innerText = "복사"; }, 1500);
                    });
                }
            }

            // ----------------------------------------------------
            // 챕터 렌더링
            // ----------------------------------------------------
            function renderChapters(list) {
                var container = document.getElementById('chapters-container');
                container.innerHTML = "";
                if (!list || list.length === 0) {
                    container.innerHTML = "<div style='color: #888; font-size: 0.8rem; text-align: center; padding: 30px;'>추출된 주제 챕터가 없습니다.</div>";
                    return;
                }
                list.forEach(function(ch, idx) {
                    var card = document.createElement('div');
                    card.className = 'ch-card';
                    card.id = 'ch-card-' + idx;
                    card.onclick = function() { jumpTo(ch.start_seconds); };
                    card.innerHTML = 
                        '<div class="ch-header">' +
                            '<span class="ch-time">' + ch.time_str + '</span>' +
                            '<span class="ch-title">' + ch.title + '</span>' +
                        '</div>' +
                        '<div class="ch-desc">' + ch.summary + '</div>';
                    container.appendChild(card);
                });
            }

            //  유튜브 공식 영화관 모드 (Theater Mode) 토글 함수
            function toggleTheaterMode() {
                isTheaterMode = !isTheaterMode;
                var container = document.querySelector('.app-container');
                var enterIcon = document.getElementById('theater-icon-enter');
                var exitIcon = document.getElementById('theater-icon-exit');
                var btn = document.getElementById('theater-toggle-btn');
                
                if (isTheaterMode) {
                    if (container) container.classList.add('theater-mode');
                    document.body.classList.add('theater-active');
                    if (enterIcon) enterIcon.style.display = 'none';
                    if (exitIcon) exitIcon.style.display = 'block';
                    if (btn) {
                        btn.title = "기본 보기 (t)";
                        btn.classList.add('active');
                    }
                    try { localStorage.setItem('yt_ai_theater_mode', 'true'); } catch(e) {}
                } else {
                    if (container) {
                        container.classList.remove('theater-mode');
                    }
                    document.body.classList.remove('theater-active');
                    if (enterIcon) enterIcon.style.display = 'block';
                    if (exitIcon) exitIcon.style.display = 'none';
                    if (btn) {
                        btn.title = "영화관 모드 (t)";
                        btn.classList.remove('active');
                    }
                    try { localStorage.setItem('yt_ai_theater_mode', 'false'); } catch(e) {}
                }
                
                syncParentFrameHeight();
                setTimeout(syncParentFrameHeight, 150);
                setTimeout(syncParentFrameHeight, 350);
            }

            //  전체화면 토글 함수
            function toggleFullscreen() {
                var elem = document.querySelector('.player-wrapper') || document.documentElement;
                if (!document.fullscreenElement) {
                    if (elem.requestFullscreen) {
                        elem.requestFullscreen();
                    } else if (elem.webkitRequestFullscreen) {
                        elem.webkitRequestFullscreen();
                    } else if (elem.msRequestFullscreen) {
                        elem.msRequestFullscreen();
                    }
                } else {
                    if (document.exitFullscreen) {
                        document.exitFullscreen();
                    }
                }
            }

            //  키보드 단축키 (t: 영화관 모드, f: 전체화면, m: 음소거)
            document.addEventListener('keydown', function(e) {
                var target = e.target;
                if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
                    return;
                }
                if (e.key === 't' || e.key === 'T') {
                    e.preventDefault();
                    toggleTheaterMode();
                } else if (e.key === 'f' || e.key === 'F') {
                    e.preventDefault();
                    toggleFullscreen();
                } else if (e.key === 'm' || e.key === 'M') {
                    e.preventDefault();
                    toggleMute();
                }
            });

            //  뷰 모드 및 반응형 화면 너비에 따른 최적 iframe 높이 정밀 계산 (중간 빈 공간/늘어짐 현상 원천 차단)
            function calculateOptimalHeight() {
                if (isTheaterMode) {
                    var leftCol = document.querySelector('.left-column');
                    var rightCol = document.querySelector('.right-column');
                    var hLeft = leftCol ? leftCol.getBoundingClientRect().height : 0;
                    var hRight = rightCol ? rightCol.getBoundingClientRect().height : 580;
                    return Math.max(Math.round(hLeft + hRight + 32), 1160);
                }
                
                if (window.innerWidth <= 900) {
                    var leftCol = document.querySelector('.left-column');
                    var rightCol = document.querySelector('.right-column');
                    var hLeft = leftCol ? leftCol.getBoundingClientRect().height : 0;
                    var hRight = rightCol ? rightCol.getBoundingClientRect().height : 540;
                    return Math.max(Math.round(hLeft + hRight + 24), 980);
                }
                
                // 데스크톱 기본 2열 모드: 645px 고정 (화면을 줄였다가 되돌아왔을 때 공백 없이 즉시 완벽 밀착)
                return 645;
            }

            // 브라우저 리사이즈 및 영화관 모드 전환 시 Streamlit iframe 높이 자동 동기화
            function syncParentFrameHeight() {
                try {
                    var targetH = calculateOptimalHeight();
                    window.parent.postMessage({ type: "streamlit:setFrameHeight", height: targetH }, "*");
                    if (window.frameElement) {
                        window.frameElement.style.height = targetH + "px";
                        if (window.frameElement.parentElement) {
                            window.frameElement.parentElement.style.height = targetH + "px";
                        }
                    }
                    if (window.parent && window.parent.document) {
                        var iframes = window.parent.document.querySelectorAll('iframe');
                        iframes.forEach(function(f) {
                            try {
                                if (f.contentWindow === window || f === window.frameElement) {
                                    f.style.height = targetH + "px";
                                    if (f.parentElement) {
                                        f.parentElement.style.height = targetH + "px";
                                    }
                                }
                            } catch(err) {}
                        });
                    }
                } catch (e) {}
            }
            window.addEventListener('resize', function() {
                syncParentFrameHeight();
            });
            window.addEventListener('load', function() {
                try {
                    if (localStorage.getItem('yt_ai_theater_mode') === 'true') {
                        toggleTheaterMode();
                    }
                } catch(e) {}
                setTimeout(syncParentFrameHeight, 200);
            });
