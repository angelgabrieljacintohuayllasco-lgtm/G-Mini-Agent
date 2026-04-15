/**
 * G-Mini Agent — App Main Controller
 * Punto de entrada principal del frontend. Conecta todo.
 */

(function () {
    'use strict';

    // ── DOM elements ──────────────────────────────────
    const userInput = document.getElementById('user-input');
    const btnSend = document.getElementById('btn-send');
    const btnAgentStart = document.getElementById('btn-agent-start');
    const btnAgentPause = document.getElementById('btn-agent-pause');
    const btnAgentStop = document.getElementById('btn-agent-stop');
    const btnMinimize = document.getElementById('btn-minimize');
    const btnClose = document.getElementById('btn-close');
    const statusDot = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const charCount = document.getElementById('char-count');
    const subagentsBar = document.getElementById('subagents-bar');
    const terminalsBar = document.getElementById('terminals-bar');

    let isGenerating = false;
    let agentRuntimeState = 'idle';

    function pushOverlayCharacterRuntime(payload) {
        if (!window.gmini || typeof window.gmini.overlaySetCharacterRuntime !== 'function') return;
        void window.gmini.overlaySetCharacterRuntime(payload).catch((error) => {
            console.warn('[Overlay] No se pudo actualizar runtime del personaje:', error);
        });
    }

    // ── Initialize modules ────────────────────────────
    chatManager.init();
    settingsManager.init();
    historyManager.init();
    if (window.codeManager?.init) {
        window.codeManager.init();
    }

    // ── WebSocket events ──────────────────────────────

    ws.on('connected', () => {
        agentRuntimeState = 'idle';
        setStatus('idle', 'Conectado');
        updateAgentControls();
        settingsManager.updateModelLabel();
        pushOverlayCharacterRuntime({ status: 'idle', visemes: [], audioHintMs: 0 });

        // Si el catálogo no cargó aún (backend tardó en arrancar), recargarlo ahora.
        // Esto ocurre cuando el backend tarda más de 1.5s en estar listo al iniciar.
        if (Object.keys(MODEL_OPTIONS).length === 0 && settingsManager) {
            settingsManager._loadModelsCatalog().then(async () => {
                await settingsManager._syncFromBackend();
            });
        } else {
            // Catálogo ya disponible: solo verificar soporte RT con provider+modelo actuales
            ws.checkRealtimeAvailable(
                settingsManager?.currentProvider || '',
                settingsManager?.currentModel || ''
            );
        }
    });

    // Sesión anterior restaurada por el backend al reconectar
    ws.on('session:restored', (data) => {
        if (!data || !data.session_id) return;
        const messages = data.messages || [];

        // Actualizar sidebar con la sesión activa
        historyManager.currentSessionId = data.session_id;
        historyManager.loadSessions();

        // Renderizar mensajes históricos en el chat
        chatManager.clear();
        if (messages.length > 0) {
            messages.forEach(msg => {
                const meta = msg.metadata || {};
                const msgType = msg.message_type || 'text';

                // Tool calls se muestran como action cards
                if (meta.tool_name) {
                    const cardEl = chatManager.addActionCard(
                        meta.tool_name,
                        meta.params || {}
                    );
                    chatManager.updateActionCard(
                        cardEl,
                        meta.success !== false,
                        meta.result_preview || ''
                    );
                } else if (msg.role === 'display' || msgType === 'system' || msgType === 'action' || msgType === 'error' || msgType === 'warning') {
                    // Agent activity messages (system, action results, errors)
                    const cssClass = msgType === 'error' ? 'error-message'
                        : msgType === 'warning' ? 'warning-message'
                        : msgType === 'action' ? 'system-message action-result'
                        : 'system-message';
                    const el = chatManager._createMessageEl(cssClass);
                    el.innerHTML = chatManager._renderMarkdown(msg.content);
                    chatManager.messagesContainer.appendChild(el);
                } else if (msg.role === 'user') {
                    chatManager.addUserMessage(msg.content);
                } else if (msg.role === 'assistant') {
                    const el = chatManager._createMessageEl('assistant-message');
                    el.innerHTML = chatManager._renderMarkdown(msg.content);
                    chatManager.messagesContainer.appendChild(el);
                }
            });
            chatManager._scrollToBottom();
        }
    });

    ws.on('disconnected', () => {
        agentRuntimeState = 'disconnected';
        setStatus('disconnected', 'Desconectado');
        setGenerating(false);
        pendingActionCards.clear();
        updateAgentControls();
        pushOverlayCharacterRuntime({ status: 'idle', visemes: [], audioHintMs: 0 });
    });

    ws.on('error', (data) => {
        agentRuntimeState = 'error';
        setStatus('error', `Error: ${data?.message || 'Desconocido'}`);
        updateAgentControls();
        pushOverlayCharacterRuntime({ status: 'idle', visemes: [], audioHintMs: 0 });
    });

    ws.on('agent:message', (data) => {
        chatManager.handleAgentMessage(data);

        // Update overlay
        if (data.text && window.gmini) {
            window.gmini.setOverlayText(data.text);
        }

        // Refresh history when message stream ends
        if (data.done) {
            historyManager.refreshCurrentSession();
        }
    });

    ws.on('agent:approval', (data) => {
        chatManager.renderApprovalState(data);
        if (data?.pending) {
            agentRuntimeState = 'thinking';
            setStatus('thinking', 'Esperando aprobacion...');
            setGenerating(false);
        }
    });

    ws.on('agent:subagents', (data) => {
        renderSubagents(data);
    });

    ws.on('gateway:notification', (data) => {
        const title = String(data?.title || 'Notificacion');
        const body = String(data?.body || '');
        const source = String(data?.source_type || '').trim();
        const sourceLabel = source ? ` [${source}]` : '';
        const text = `Gateway${sourceLabel}: ${title}${body ? `\n${body}` : ''}`;
        chatManager.addSystemMessage(text);
        if (window.codeManager?.refreshGateway) {
            window.codeManager.refreshGateway();
        }
    });

    ws.on('agent:status', (data) => {
        const status = data?.status || 'idle';
        agentRuntimeState = status;
        pushOverlayCharacterRuntime(
            status === 'responding' || status === 'calling'
                ? { status }
                : { status, visemes: [], audioHintMs: 0 }
        );
        switch (status) {
            case 'thinking':
                setStatus('thinking', 'Pensando...');
                setGenerating(true);
                break;
            case 'responding':
                setStatus('responding', 'Respondiendo...');
                setGenerating(true);
                break;
            case 'executing':
                setStatus('responding', 'Ejecutando acción...');
                setGenerating(true);
                break;
            case 'paused':
                setStatus('paused', 'Pausado');
                setGenerating(true);
                break;
            case 'realtime_connecting':
                setStatus('responding', 'Conectando voz…');
                setGenerating(true);
                break;
            case 'realtime_active':
                setStatus('responding', 'Voz en tiempo real');
                break;
            case 'realtime_stopped':
                setStatus('idle', 'Listo');
                setGenerating(false);
                break;
            case 'idle':
            default:
                setStatus('idle', 'Listo');
                setGenerating(false);
                break;
        }
    });

    ws.on('agent:audio', (data) => {
        if (!data) return;
        // Realtime streaming audio — reproducir directamente
        if (data.stream && data.audio && typeof voiceRealtime !== 'undefined' && voiceRealtime.active) {
            const durationMs = voiceRealtime.playAudioChunk(data.audio, data.format || 'pcm16');
            if (durationMs > 0) {
                pushOverlayCharacterRuntime({
                    status: agentRuntimeState,
                    audioHintMs: Math.round(durationMs),
                });
            }
            return;
        }
        // Non-realtime TTS — solo overlay hint
        const durationMs = Number.isFinite(Number(data?.duration))
            ? Math.max(0, Math.round(Number(data.duration) * 1000))
            : 1800;
        pushOverlayCharacterRuntime({
            status: agentRuntimeState,
            audioHintMs: durationMs || 1800,
        });
    });

    ws.on('agent:lipsync', (data) => {
        pushOverlayCharacterRuntime({
            status: agentRuntimeState,
            visemes: Array.isArray(data?.visemes) ? data.visemes : [],
        });
    });

    ws.on('agent:screenshot', (data) => {
        if (data && data.image) {
            chatManager.addScreenshot(data.image, data.caption || '');
        }
    });

    // ── Action visualization events ───────────────────
    // Map para asociar action cards con su ID (para actualizar con resultado)
    const pendingActionCards = new Map();

    ws.on('agent:action', (data) => {
        if (!data) return;
        const { type, params, actionId } = data;

        // Mostrar tarjeta de actividad en el chat
        const cardEl = chatManager.addActionCard(type, params || {});
        if (actionId) {
            pendingActionCards.set(actionId, cardEl);
        }

        // Mostrar burbuja del cursor para acciones con coordenadas
        if (params && params.x !== undefined && params.y !== undefined) {
            if (window.gmini && window.gmini.showCursorBubble) {
                window.gmini.showCursorBubble(params.x, params.y);
            }
        }

        // Mostrar efectos visuales según el tipo de acción
        switch (type) {
            case 'click':
            case 'double_click':
            case 'right_click':
                if (params.x !== undefined && params.y !== undefined) {
                    overlayEffects.showClickAt(params.x, params.y, type);
                }
                break;
            case 'screenshot':
                overlayEffects.showScreenshotEffect();
                if (window.gmini && window.gmini.showScreenshotOverlay) {
                    window.gmini.showScreenshotOverlay();
                }
                break;
            case 'move':
                if (params.x !== undefined && params.y !== undefined) {
                    overlayEffects.showMove(params.x, params.y);
                }
                break;
            case 'type':
                overlayEffects.showTypingEffect(params.text || '');
                break;
            case 'press':
                overlayEffects.showKeyPress(params.key || '');
                break;
            case 'hotkey':
                overlayEffects.showHotkey(params.keys || '');
                break;
            case 'scroll':
                overlayEffects.showScroll(params.clicks || 0);
                break;
            case 'drag':
                if (params.x !== undefined && params.y !== undefined) {
                    overlayEffects.showDrag(params.x, params.y);
                }
                break;
            case 'wait':
                overlayEffects.showWait(params.seconds || 1);
                break;
        }
    });

    // ── Action result events (actualiza la card con éxito/error) ───
    ws.on('agent:action_result', (data) => {
        if (!data || !data.actionId) return;
        const cardEl = pendingActionCards.get(data.actionId);
        if (cardEl) {
            chatManager.updateActionCard(cardEl, data.success, data.result || '');
            pendingActionCards.delete(data.actionId);
        }
    });

    // Limpiar action cards pendientes cuando el agente vuelve a idle
    ws.on('agent:status', (data) => {
        if ((data?.status || 'idle') === 'idle') {
            pendingActionCards.clear();
        }
    });

    ws.on('agent:executing', (data) => {
        const active = data?.active || false;
        overlayEffects.setExecutingMode(active);
        
        // Cambiar opacidad de la ventana
        if (window.gmini && window.gmini.setExecutingMode) {
            window.gmini.setExecutingMode(active);
        }
    });

    // ── Connect to backend ────────────────────────────
    ws.connect();
    setInterval(refreshTerminals, 5000);
    setTimeout(refreshTerminals, 1500);

    // ── Input handling ────────────────────────────────

    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    userInput.addEventListener('input', () => {
        // Auto-resize
        userInput.style.height = 'auto';
        userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
        // Char count
        charCount.textContent = userInput.value.length;
    });

    btnSend.addEventListener('click', sendMessage);

    btnAgentStart?.addEventListener('click', () => {
        ws.sendCommand('start');
        if (agentRuntimeState === 'paused') {
            agentRuntimeState = isGenerating ? 'responding' : 'idle';
            updateAgentControls();
        }
    });

    btnAgentPause?.addEventListener('click', () => {
        ws.sendCommand('pause');
        if (isGenerating && agentRuntimeState !== 'paused') {
            agentRuntimeState = 'paused';
            updateAgentControls();
        }
    });

    btnAgentStop?.addEventListener('click', () => {
        ws.sendCommand('stop');
        agentRuntimeState = 'idle';
        setGenerating(false);
    });

    // ── Window controls ───────────────────────────────

    btnMinimize.addEventListener('click', () => {
        if (window.gmini) window.gmini.minimize();
    });

    btnClose.addEventListener('click', () => {
        if (window.gmini) window.gmini.close();
    });

    // ── Helpers ───────────────────────────────────────

    function sendMessage() {
        const text = userInput.value.trim();
        if (!text || isGenerating) return;

        if (!ws.connected) {
            chatManager.addSystemMessage('⚠️ No hay conexión con el backend. Intenta de nuevo.');
            return;
        }

        chatManager.addUserMessage(text);
        ws.sendMessage(text);

        updateComposerValue('');
        userInput.focus();
    }

    function updateComposerValue(value) {
        userInput.value = String(value || '');
        userInput.style.height = 'auto';
        userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
        charCount.textContent = userInput.value.length;
    }

    function setStatus(state, text) {
        statusDot.className = `status-dot ${state}`;
        statusText.textContent = text;
    }

    function setGenerating(value) {
        isGenerating = value;
        btnSend.disabled = value;
        userInput.disabled = value;
        updateAgentControls();
    }

    function updateAgentControls() {
        const paused = agentRuntimeState === 'paused';
        const connected = agentRuntimeState !== 'disconnected' && agentRuntimeState !== 'error';
        const busy = isGenerating || paused;
        const canResume = connected && paused;
        const canPause = connected && isGenerating && !paused;
        const canStop = connected && busy;

        if (btnAgentStart) {
            btnAgentStart.disabled = !canResume;
            btnAgentStart.classList.toggle('active', canResume);
        }
        if (btnAgentPause) {
            btnAgentPause.disabled = !canPause;
            btnAgentPause.classList.toggle('active', canPause);
        }
        if (btnAgentStop) {
            btnAgentStop.disabled = !canStop;
            btnAgentStop.classList.toggle('active', canStop);
        }
    }

    function renderSubagents(data) {
        const items = Array.isArray(data?.items) ? data.items : [];
        const active = items.filter((item) => item.status === 'queued' || item.status === 'running');
        if (active.length === 0) {
            subagentsBar.classList.add('hidden');
            subagentsBar.innerHTML = '';
            return;
        }

        subagentsBar.classList.remove('hidden');
        subagentsBar.innerHTML = active.map((item) => `
            <div class="subagent-pill subagent-${item.status}">
                <span class="subagent-name">${escapeHtml(item.name || item.id)}</span>
                <span class="subagent-status">${escapeHtml(item.status)}</span>
            </div>
        `).join('');
    }

    async function refreshTerminals() {
        try {
            const resp = await fetch('http://127.0.0.1:8765/api/terminals');
            if (!resp.ok) return;
            const data = await resp.json();
            renderTerminals(data);
        } catch (err) {
            // backend not ready
        }
    }

    function renderTerminals(data) {
        const sessions = Array.isArray(data?.sessions) ? data.sessions : [];
        const visible = sessions.slice(0, 5);
        if (visible.length === 0) {
            terminalsBar.classList.add('hidden');
            terminalsBar.innerHTML = '';
            return;
        }

        terminalsBar.classList.remove('hidden');
        terminalsBar.innerHTML = visible.map((item) => {
            const name = escapeHtml(item.shell_name || item.shell_key);
            const status = escapeHtml(item.status || '');
            const lastCmd = item.last_command ? escapeHtml(item.last_command.slice(0, 40)) : '';
            const dur = typeof item.duration_s === 'number' ? `${item.duration_s.toFixed(1)}s` : '';
            const meta = [lastCmd, dur].filter(Boolean).join(' · ');
            return `
                <div class="terminal-pill" title="${escapeHtml(item.last_command || '')}">
                    <span class="subagent-name">${name}</span>
                    <span class="subagent-status">${status}</span>
                    ${meta ? `<span class="terminal-meta">${meta}</span>` : ''}
                </div>
            `;
        }).join('');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = String(text || '');
        return div.innerHTML;
    }

    // ── Voice capture (btn-voice) ───────────────────────
    const btnVoice = document.getElementById('btn-voice');
    let _voiceRecording = false;
    let _mediaRecorder = null;

    ws.on('agent:stt_result', (data) => {
        const text = (data?.text || '').trim();
        if (text) {
            updateComposerValue(text);
            userInput.focus();
        }
    });

    if (btnVoice) {
        btnVoice.addEventListener('click', async () => {
            if (_voiceRecording) {
                // Stop recording
                if (_mediaRecorder && _mediaRecorder.state !== 'inactive') {
                    _mediaRecorder.stop();
                }
                return;
            }
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                _mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
                const chunks = [];

                _mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) chunks.push(e.data);
                };
                _mediaRecorder.onstop = async () => {
                    _voiceRecording = false;
                    btnVoice.classList.remove('recording');
                    btnVoice.textContent = '🎙';
                    stream.getTracks().forEach((t) => t.stop());

                    if (chunks.length === 0) return;
                    const blob = new Blob(chunks, { type: 'audio/webm' });
                    const buf = await blob.arrayBuffer();
                    const bytes = new Uint8Array(buf);
                    let binary = '';
                    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
                    const b64 = btoa(binary);
                    ws.sendAudio(b64);
                };

                _mediaRecorder.start();
                _voiceRecording = true;
                btnVoice.classList.add('recording');
                btnVoice.textContent = '⏹';
            } catch (err) {
                console.error('Mic access error:', err);
                _voiceRecording = false;
                if (btnVoice) {
                    btnVoice.classList.remove('recording');
                    btnVoice.textContent = '🎙';
                }
            }
        });
    }

    // ── Realtime voice (btn-realtime) ───────────────────
    const btnRealtime = document.getElementById('btn-realtime');
    let _realtimeProvider = ''; // provider RT resuelto por el backend
    let _realtimeVoice = ''; // voz seleccionada por el usuario
    let _realtimeVoices = []; // voces disponibles
    let _realtimeMode = '';  // 'native' | 'simulated'

    if (btnRealtime) {
        // Ocultar por defecto hasta que el backend confirme soporte RT
        btnRealtime.style.display = 'none';

        btnRealtime.addEventListener('click', async () => {
            if (voiceRealtime.active) {
                await voiceRealtime.stop();
                btnRealtime.classList.remove('realtime-active', 'realtime-simulated');
                btnRealtime.textContent = _realtimeMode === 'simulated' ? '🎙️' : '📞';
                btnRealtime.title = _realtimeMode === 'simulated'
                    ? 'Conversación por voz (STT → Modelo → TTS)'
                    : 'Conversación en tiempo real';
            } else {
                // Enviar mode al backend para que sepa qué pipeline usar
                const provider = _realtimeProvider || settingsManager?.currentProvider || '';
                const started = await voiceRealtime.start(provider, _realtimeVoice, _realtimeMode);
                if (started) {
                    btnRealtime.classList.add('realtime-active');
                    if (_realtimeMode === 'simulated') {
                        btnRealtime.classList.add('realtime-simulated');
                    }
                    btnRealtime.textContent = '🔴';
                }
            }
        });
    }

    // Selector de voz para realtime (voice-select existente o creado dinámicamente)
    let _voiceSelect = document.getElementById('realtime-voice-select');

    function _updateVoiceSelector(voices) {
        _realtimeVoices = voices || [];
        if (!_voiceSelect && _realtimeVoices.length > 0) {
            // Crear selector de voz junto al botón realtime
            _voiceSelect = document.createElement('select');
            _voiceSelect.id = 'realtime-voice-select';
            _voiceSelect.className = 'realtime-voice-select';
            _voiceSelect.title = 'Voz del asistente';
            if (btnRealtime && btnRealtime.parentElement) {
                btnRealtime.parentElement.insertBefore(_voiceSelect, btnRealtime);
            }
        }
        if (_voiceSelect) {
            _voiceSelect.innerHTML = _realtimeVoices.map((v) =>
                `<option value="${escapeHtml(v)}" ${v === _realtimeVoice ? 'selected' : ''}>${escapeHtml(v)}</option>`
            ).join('');
            _voiceSelect.style.display = _realtimeVoices.length > 0 ? '' : 'none';
            _voiceSelect.onchange = () => { _realtimeVoice = _voiceSelect.value; };
            if (!_realtimeVoice && _realtimeVoices.length > 0) {
                _realtimeVoice = _realtimeVoices[0];
            }
        }
    }

    // Escuchar respuesta del backend sobre disponibilidad RT
    ws.on('agent:realtime_available', (data) => {
        if (!btnRealtime) return;
        if (data?.available) {
            _realtimeProvider = data.provider || '';
            _realtimeMode = data.mode || 'native';
            btnRealtime.style.display = '';

            // Actualizar apariencia según modo
            if (_realtimeMode === 'simulated') {
                btnRealtime.textContent = '🎙️';
                btnRealtime.title = 'Conversación por voz (STT → Modelo → TTS)';
            } else {
                btnRealtime.textContent = '📞';
                btnRealtime.title = 'Conversación en tiempo real';
            }

            _updateVoiceSelector(data.voices || []);

            // Guardar capacidades del modelo para el botón de video
            _modelSupportsVideo = !!data.supports_video;
        } else {
            _realtimeProvider = '';
            _realtimeMode = '';
            btnRealtime.style.display = 'none';
            _updateVoiceSelector([]);
            _modelSupportsVideo = false;
            // Ocultar botón de video si el modelo no es compatible
            if (btnVideoStream) {
                btnVideoStream.style.display = 'none';
            }
            // Si estaba activo, detener
            if (voiceRealtime.active) {
                voiceRealtime.stop();
                btnRealtime.classList.remove('realtime-active', 'realtime-simulated');
                btnRealtime.textContent = '📞';
            }
        }
    });

    // Mostrar transcripción del habla del usuario en el chat
    ws.on('agent:realtime_user_text', (data) => {
        const text = (data?.text || '').trim();
        if (text) {
            // Cerrar burbuja de streaming del agente antes de mostrar mensaje del usuario
            if (chatManager.isStreaming) {
                chatManager.finishStreaming();
            }
            chatManager.addUserMessage(`🎤 ${text}`);
        }
    });

    // Actualizar botón RT según estado
    ws.on('agent:status', (data) => {
        const status = data?.status || '';
        if (status === 'realtime_active') {
            if (btnRealtime) {
                btnRealtime.classList.add('realtime-active');
                if (data?.mode === 'simulated') {
                    btnRealtime.classList.add('realtime-simulated');
                }
                btnRealtime.textContent = '🔴';
            }
            // Mostrar botón de video si el modelo tiene live_api: true (siempre soporta video)
            if (btnVideoStream && _modelSupportsVideo) {
                btnVideoStream.style.display = '';
            }
        } else if (status === 'realtime_stopped') {
            if (btnRealtime) {
                btnRealtime.classList.remove('realtime-active', 'realtime-simulated');
                btnRealtime.textContent = _realtimeMode === 'simulated' ? '🎙️' : '📞';
                btnRealtime.title = _realtimeMode === 'simulated'
                    ? 'Conversación por voz (STT → Modelo → TTS)'
                    : 'Conversación en tiempo real';
            }
            // Ocultar y resetear botón de video stream
            if (btnVideoStream) {
                btnVideoStream.style.display = 'none';
                btnVideoStream.classList.remove('video-stream-active');
                btnVideoStream.textContent = '�️';
                _videoStreamActive = false;
            }
        }
    });

    // ── Video stream toggle (btn-video-stream) ────────────────
    // Visible para cualquier modelo con live_api: true (siempre tienen video + Google Search)
    // Captura la pantalla del PC a ~1fps y la envía al modelo vía Live API realtimeInput.video
    const btnVideoStream = document.getElementById('btn-video-stream');
    let _videoStreamActive = false;
    let _modelSupportsVideo = false;

    if (btnVideoStream) {
        btnVideoStream.addEventListener('click', () => {
            if (!voiceRealtime.active) return;
            _videoStreamActive = !_videoStreamActive;
            ws.toggleScreenStream(_videoStreamActive);
            btnVideoStream.classList.toggle('video-stream-active', _videoStreamActive);
            btnVideoStream.textContent = _videoStreamActive ? '🔴' : '�️';
            btnVideoStream.title = _videoStreamActive
                ? 'Detener streaming de pantalla'
                : 'Mostrar pantalla a la IA (Live API streaming)';
        });
    }

    // Respuesta del backend sobre estado del video stream
    ws.on('agent:screen_stream_status', (data) => {
        _videoStreamActive = !!data?.active;
        if (btnVideoStream) {
            btnVideoStream.classList.toggle('video-stream-active', _videoStreamActive);
            btnVideoStream.textContent = _videoStreamActive ? '🔴' : '🖥️';
            btnVideoStream.title = _videoStreamActive
                ? 'Detener streaming de pantalla'
                : 'Mostrar pantalla a la IA (Live API streaming)';
        }
    });

    window.gminiComposer = {
        setText(text) {
            updateComposerValue(text);
            userInput.focus();
        },
        appendText(text) {
            const addition = String(text || '');
            const nextText = userInput.value
                ? `${userInput.value.trimEnd()}\n\n${addition}`
                : addition;
            updateComposerValue(nextText);
            userInput.focus();
        },
        getText() {
            return userInput.value;
        },
        focus() {
            userInput.focus();
        },
    };
})();
