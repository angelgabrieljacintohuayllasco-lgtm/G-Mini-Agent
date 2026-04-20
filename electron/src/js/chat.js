/**
 * G-Mini Agent — Chat Module
 * Renderizado de mensajes, streaming y Markdown básico.
 */

class ChatManager {
    constructor() {
        this.messagesContainer = document.getElementById('messages');
        this.currentStreamingEl = null;
        this.streamingText = '';
        this.isStreaming = false;
        this.approvalCardEl = null;
    }

    init() {
        // Nada extra por ahora
        this._lastScreenshotTime = 0;
    }

    /**
     * Añade un mensaje del usuario al chat.
     */
    addUserMessage(text) {
        const el = this._createMessageEl('user-message');
        el.innerHTML = this._escapeHtml(text);
        this.messagesContainer.appendChild(el);
        this._scrollToBottom();
    }

    addSystemMessage(text) {
        const el = this._createMessageEl('system-message');
        el.innerHTML = this._renderMarkdown(String(text || ''));
        this.messagesContainer.appendChild(el);
        this._scrollToBottom();
    }

    /**
     * Añade un screenshot inline al chat con throttle de 3 segundos.
     */
    addScreenshot(base64Image, caption = '') {
        const now = Date.now();
        // Throttle solo para screenshots idénticos consecutivos (evitar duplicados por refresh)
        // No aplicar throttle a imágenes generadas ni screenshots del agente en voz
        if (!caption && now - this._lastScreenshotTime < 500) return;
        if (!caption) this._lastScreenshotTime = now;

        const isGenerated = caption === 'generated_image';
        const el = this._createMessageEl(isGenerated ? 'generated-image-message' : 'screenshot-message');
        const img = document.createElement('img');
        const src = base64Image.startsWith('data:') ? base64Image : `data:image/png;base64,${base64Image}`;
        img.src = src;
        img.alt = isGenerated ? 'Imagen generada por IA' : 'Screenshot del agente';
        img.addEventListener('click', () => this._showScreenshotModal(src));
        el.appendChild(img);
        if (isGenerated) {
            const label = document.createElement('div');
            label.className = 'generated-image-label';
            label.textContent = '🎨 Imagen generada con IA';
            el.appendChild(label);
        }
        this.messagesContainer.appendChild(el);
        this._scrollToBottom();
    }

    _showScreenshotModal(src) {
        const existing = document.getElementById('screenshot-modal');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'screenshot-modal';
        overlay.className = 'screenshot-modal-overlay';
        overlay.addEventListener('click', () => overlay.remove());

        const img = document.createElement('img');
        img.src = src;
        img.alt = 'Screenshot ampliado';
        overlay.appendChild(img);
        document.body.appendChild(overlay);
    }

    /**
     * Maneja un chunk de respuesta streaming del agente.
     */
    handleAgentMessage(data) {
        const { text, type, done } = data;

        if (type === 'error') {
            this._addErrorMessage(text);
            this.finishStreaming();
            return;
        }

        if (done) {
            this.finishStreaming();
            return;
        }

        if (!this.isStreaming) {
            this.startStreaming();
        }

        // Append text chunk
        this.streamingText += text;
        this._updateStreamingContent();
    }

    /**
     * Inicia un nuevo mensaje streaming.
     */
    startStreaming() {
        this.isStreaming = true;
        this.streamingText = '';
        this.currentStreamingEl = this._createMessageEl('assistant-message streaming-cursor');
        this.messagesContainer.appendChild(this.currentStreamingEl);
    }

    /**
     * Finaliza el streaming actual.
     */
    finishStreaming() {
        if (this.currentStreamingEl) {
            this.currentStreamingEl.classList.remove('streaming-cursor');
            // Parse final markdown
            this.currentStreamingEl.innerHTML = this._renderMarkdown(this.streamingText);
        }
        this.currentStreamingEl = null;
        this.streamingText = '';
        this.isStreaming = false;
        this._scrollToBottom();
    }

    /**
     * Actualiza el contenido del mensaje streaming.
     */
    _updateStreamingContent() {
        if (!this.currentStreamingEl) return;
        // Render parcial (sin markdown completo para performance)
        this.currentStreamingEl.innerHTML = this._renderMarkdown(this.streamingText);
        this._scrollToBottom();
    }

    _addErrorMessage(text) {
        const el = this._createMessageEl('error-message');
        el.textContent = text;
        this.messagesContainer.appendChild(el);
        this._scrollToBottom();
    }

    _createMessageEl(className) {
        const div = document.createElement('div');
        div.className = `message ${className}`;
        return div;
    }

    _scrollToBottom() {
        const container = document.getElementById('chat-container');
        if (!container) return;
        requestAnimationFrame(() => {
            container.scrollTop = container.scrollHeight;
        });
    }

    /**
     * Renderizado básico de Markdown.
     */
    _renderMarkdown(text) {
        if (!text) return '';

        let html = this._escapeHtml(text);

        // Code blocks ```...```
        html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
            return `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`;
        });

        // Inline code `...`
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold **...**
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

        // Italic *...*
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Line breaks
        html = html.replace(/\n/g, '<br>');

        return html;
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    clear() {
        this.messagesContainer.innerHTML = '';
        this.finishStreaming();
        this.approvalCardEl = null;
    }

    // ── Action activity cards ────────────────────────

    /**
     * Muestra una tarjeta de actividad en el chat indicando qué herramienta se ejecutó.
     * @param {string} type - Nombre de la herramienta (click, type, screenshot, etc.)
     * @param {object} params - Parámetros de la herramienta
     * @returns {HTMLElement} El elemento de la card para poder actualizarlo con el resultado
     */
    addActionCard(type, params) {
        const el = this._createMessageEl('action-message');
        const icon = this._getActionIcon(type);
        const label = this._getActionLabel(type, params);

        el.innerHTML = `
            <div class="action-header">
                <span class="action-icon">${icon}</span>
                <span class="action-label">${this._escapeHtml(label)}</span>
                <span class="action-status action-running">ejecutando…</span>
            </div>
            <div class="action-detail">${this._formatActionParams(type, params)}</div>
        `;

        // Timer de progreso: muestra segundos transcurridos después de 2s
        const startTime = Date.now();
        const statusEl = el.querySelector('.action-status');
        el._actionTimer = setInterval(() => {
            const elapsed = Math.round((Date.now() - startTime) / 1000);
            if (elapsed >= 2 && statusEl && statusEl.classList.contains('action-running')) {
                statusEl.textContent = `ejecutando… ${elapsed}s`;
            }
        }, 1000);

        this.messagesContainer.appendChild(el);
        this._scrollToBottom();
        return el;
    }

    /**
     * Actualiza una tarjeta de acción con su resultado.
     * @param {HTMLElement} cardEl - Elemento de la card devuelto por addActionCard
     * @param {boolean} success - Si la acción fue exitosa
     * @param {string} resultText - Texto del resultado
     */
    updateActionCard(cardEl, success, resultText) {
        if (!cardEl) return;
        // Detener timer de progreso si existe
        if (cardEl._actionTimer) {
            clearInterval(cardEl._actionTimer);
            cardEl._actionTimer = null;
        }
        const statusEl = cardEl.querySelector('.action-status');
        if (statusEl) {
            statusEl.textContent = success ? 'COMPLETADO' : 'ERROR';
            statusEl.className = `action-status ${success ? 'action-ok' : 'action-fail'}`;
        }
        if (resultText) {
            let detailEl = cardEl.querySelector('.action-result');
            if (!detailEl) {
                detailEl = document.createElement('div');
                detailEl.className = 'action-result';
                cardEl.appendChild(detailEl);
            }
            // Formatear resultados de generación multimedia de forma limpia
            const formatted = this._formatMediaResult(resultText);
            const maxLen = 500;
            const truncated = formatted.length > maxLen ? formatted.slice(0, maxLen) + '…' : formatted;
            detailEl.textContent = truncated;
            if (!success) detailEl.classList.add('action-result-error');
        }
        this._scrollToBottom();
    }

    /**
     * Formatea resultados de generación multimedia para mostrar de forma legible.
     * Convierte dicts crudos de Python en texto limpio.
     */
    _formatMediaResult(text) {
        if (!text) return '';
        // Detectar dicts de Python serializados: {'success': True, 'model': ...}
        const dictMatch = text.match(/^\{['\"](?:success|model|message|count|files)['\"]:/);
        if (!dictMatch) return text;
        try {
            // Convertir single quotes de Python a double quotes para parsear
            const jsonStr = text
                .replace(/'/g, '"')
                .replace(/\bTrue\b/g, 'true')
                .replace(/\bFalse\b/g, 'false')
                .replace(/\bNone\b/g, 'null');
            const data = JSON.parse(jsonStr);
            const parts = [];
            if (data.model) parts.push(`Modelo: ${data.model}`);
            if (data.message) parts.push(data.message);
            if (data.count) parts.push(`Archivos: ${data.count}`);
            if (Array.isArray(data.files)) {
                for (const f of data.files) {
                    if (f.filename) parts.push(`📁 ${f.filename}`);
                    else if (f.path) parts.push(`📁 ${f.path.split(/[/\\]/).pop()}`);
                }
            }
            if (data.lyrics) parts.push(`🎵 Letra: ${data.lyrics.slice(0, 200)}`);
            return parts.length > 0 ? parts.join(' | ') : text;
        } catch {
            return text;
        }
    }

    _getActionIcon(type) {
        const icons = {
            screenshot: '📸', click: '🖱️', double_click: '🖱️', right_click: '🖱️',
            type: '⌨️', press: '⌨️', hotkey: '⌨️',
            open_application: '🚀', browser_navigate: '🌐',
            browser_click: '🖱️', browser_type: '⌨️', browser_extract: '📄',
            browser_snapshot: '📋', browser_tabs: '📑', browser_new_tab: '➕',
            browser_switch_tab: '🔀', browser_close_tab: '❌',
            browser_go_back: '◀️', browser_go_forward: '▶️', browser_scroll: '🔄',
            terminal_run: '💻', scroll: '🔄', screen_read_text: '👁️',
            move: '↗️', drag: '↕️', wait: '⏳',
            generate_image: '🎨', generate_video: '🎬', generate_music: '🎵',
        };
        return icons[type] || '⚙️';
    }

    _getActionLabel(type, params) {
        switch (type) {
            case 'screenshot': return 'Captura de pantalla';
            case 'screen_read_text': return 'Leyendo texto de pantalla (OCR)';
            case 'click': return `Click en (${params.x}, ${params.y})`;
            case 'double_click': return `Doble click en (${params.x}, ${params.y})`;
            case 'right_click': return `Click derecho en (${params.x}, ${params.y})`;
            case 'type': return `Escribiendo texto`;
            case 'press': return `Tecla: ${params.key || '?'}`;
            case 'hotkey': return `Hotkey: ${params.keys || '?'}`;
            case 'open_application': return `Abriendo: ${params.name || '?'}`;
            case 'browser_navigate': return `Navegando a URL`;
            case 'browser_click': return `Click en elemento web`;
            case 'browser_type': return `Escribiendo en campo web`;
            case 'browser_extract': return `Extrayendo contenido web`;
            case 'browser_snapshot': return `Capturando DOM del navegador`;
            case 'browser_tabs': return `Listando pestañas`;
            case 'browser_new_tab': return `Abriendo nueva pestaña`;
            case 'browser_switch_tab': return `Cambiando de pestaña`;
            case 'browser_close_tab': return `Cerrando pestaña`;
            case 'browser_go_back': return `Volviendo atrás en navegador`;
            case 'browser_go_forward': return `Avanzando en navegador`;
            case 'browser_scroll': return `Scroll en navegador`;
            case 'terminal_run': return 'Ejecutando comando';
            case 'scroll': return `Scroll ${(params.clicks || 0) > 0 ? 'abajo' : 'arriba'} (${Math.abs(params.clicks || 0)} pasos)`;
            case 'move': return `Mover cursor a (${params.x}, ${params.y})`;
            case 'drag': return `Arrastrar a (${params.x}, ${params.y})`;
            case 'wait': return `Esperando ${params.seconds || 1}s`;
            case 'generate_image': return `Generando imagen con IA`;
            case 'generate_video': return `Generando video con IA`;
            case 'generate_music': return `Generando música con IA`;
            default: return type.replace(/_/g, ' ');
        }
    }

    _formatActionParams(type, params) {
        if (!params || Object.keys(params).length === 0) return '';
        switch (type) {
            case 'type': return `<code>${this._escapeHtml(params.text || '')}</code>${params.submit ? ' <span class="action-param-tag">+ Enter</span>' : ''}`;
            case 'terminal_run': return `<code>${this._escapeHtml(params.command || '')}</code>`;
            case 'browser_navigate': return `<code>${this._escapeHtml(params.url || '')}</code>`;
            case 'browser_click': return `selector: <code>${this._escapeHtml(params.selector || '')}</code>${params.force ? ' <span class="action-param-tag">force</span>' : ''}`;
            case 'browser_type': return `selector: <code>${this._escapeHtml(params.selector || '')}</code> → <code>${this._escapeHtml(params.text || '')}</code>`;
            case 'generate_image': return `<code>${this._escapeHtml(params.prompt || '')}</code>${params.aspect_ratio ? ` <span class="action-param-tag">${params.aspect_ratio}</span>` : ''}`;
            case 'generate_video': return `<code>${this._escapeHtml(params.prompt || '')}</code>${params.duration_seconds ? ` <span class="action-param-tag">${params.duration_seconds}s</span>` : ''}`;
            case 'generate_music': return `<code>${this._escapeHtml(params.prompt || '')}</code>`;
            case 'click': return `<span class="action-param-detail">botón: ${params.button || 'left'}${(params.clicks || 1) > 1 ? ` × ${params.clicks}` : ''}</span>`;
            case 'double_click': return `<span class="action-param-detail">botón: ${params.button || 'left'}</span>`;
            case 'right_click': return `<span class="action-param-detail">en (${params.x}, ${params.y})</span>`;
            case 'screenshot': return params.monitor != null ? `<span class="action-param-detail">monitor: ${params.monitor}</span>` : '';
            case 'open_application': return params.name ? `<span class="action-param-detail">${this._escapeHtml(params.name)}</span>` : '';
            case 'hotkey': return `<code>${this._escapeHtml(params.keys || '')}</code>`;
            case 'press': return `<code>${this._escapeHtml(params.key || '')}</code>`;
            case 'scroll': return `<span class="action-param-detail">${Math.abs(params.clicks || 0)} clicks${params.x != null ? ` en (${params.x}, ${params.y})` : ''}</span>`;
            case 'drag': return `<span class="action-param-detail">de (${params.startX || '?'}, ${params.startY || '?'}) a (${params.x}, ${params.y})</span>`;
            case 'browser_switch_tab': return params.tab_id ? `<span class="action-param-detail">tab: ${params.tab_id}</span>` : '';
            default: {
                // Mostrar todos los params como JSON compacto para tools no mapeadas
                const summary = Object.entries(params)
                    .filter(([, v]) => v !== undefined && v !== null && v !== '')
                    .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`)
                    .join(' | ');
                return summary ? `<span class="action-param-detail">${this._escapeHtml(summary)}</span>` : '';
            }
        }
    }

    renderApprovalState(data) {
        if (!data?.pending) {
            if (this.approvalCardEl) {
                this.approvalCardEl.remove();
                this.approvalCardEl = null;
            }
            return;
        }

        if (!this.approvalCardEl) {
            this.approvalCardEl = document.createElement('div');
            this.approvalCardEl.className = 'message approval-message';
            this.messagesContainer.appendChild(this.approvalCardEl);
        }

        const findings = Array.isArray(data.findings) ? data.findings : [];
        const approvalKind = data.kind || 'approval';
        const isDryRun = approvalKind === 'dry_run';
        const findingsHtml = findings.map((item) => {
            const capability = item.capability_label ? `<div class="approval-meta">Permiso: ${this._escapeHtml(item.capability_label)}</div>` : '';
            const confidence = typeof item.confidence === 'number' && typeof item.threshold === 'number'
                ? `<div class="approval-meta">Score ${item.confidence.toFixed(2)} / ${item.threshold.toFixed(2)}</div>`
                : '';
            const spendMode = item.spend_policy_mode
                ? `<div class="approval-meta">Política de gasto: ${this._escapeHtml(item.spend_policy_mode)}</div>`
                : '';
            const spendAmount = typeof item.amount_usd === 'number'
                ? `<div class="approval-meta">Monto detectado: $${this._escapeHtml(item.amount_usd.toFixed(2))} USD</div>`
                : (typeof item.raw_amount === 'number' && item.payment_currency
                    ? `<div class="approval-meta">Monto detectado: ${this._escapeHtml(item.raw_amount.toFixed(2))} ${this._escapeHtml(item.payment_currency)}</div>`
                    : '');
            const paymentAccount = item.payment_account_name
                ? `<div class="approval-meta">Cuenta: ${this._escapeHtml(item.payment_account_name)}${item.payment_account_last4 ? ` • ****${this._escapeHtml(item.payment_account_last4)}` : ''}</div>`
                : (item.payment_account_requested
                    ? `<div class="approval-meta">Cuenta solicitada: ${this._escapeHtml(item.payment_account_requested)}</div>`
                    : '');
            return `
                <div class="approval-finding">
                    <div><strong>${this._escapeHtml(item.action || 'accion')}</strong> <span class="approval-severity">${this._escapeHtml(item.severity || '')}</span></div>
                    <div>${this._escapeHtml(item.reason || '')}</div>
                    ${capability}
                    ${confidence}
                    ${spendMode}
                    ${spendAmount}
                    ${paymentAccount}
                </div>
            `;
        }).join('');

        const title = isDryRun ? 'Dry Run requerido' : 'Aprobacion requerida';
        const approveLabel = isDryRun ? 'Ejecutar' : 'Aprobar';
        const decisionBadge = data.decision
            ? `<div class="approval-meta">Critic: ${this._escapeHtml(data.decision)}</div>`
            : '';

        this.approvalCardEl.innerHTML = `
            <div class="approval-header">
                <div class="approval-title">${title}</div>
                <div class="approval-badge">${this._escapeHtml(data.mode_name || data.mode || 'modo activo')}</div>
            </div>
            ${decisionBadge}
            <div class="approval-summary">${this._renderMarkdown(data.summary || '')}</div>
            <div class="approval-findings">${findingsHtml}</div>
            <div class="approval-actions">
                <button class="approval-btn approval-approve" data-action="approve">${approveLabel}</button>
                <button class="approval-btn approval-cancel" data-action="cancel">Cancelar</button>
            </div>
        `;

        this.approvalCardEl.querySelector('[data-action="approve"]')?.addEventListener('click', () => {
            ws.sendCommand('approve_pending');
        });
        this.approvalCardEl.querySelector('[data-action="cancel"]')?.addEventListener('click', () => {
            ws.sendCommand('cancel_pending');
        });

        this._scrollToBottom();
    }
}

const chatManager = new ChatManager();
