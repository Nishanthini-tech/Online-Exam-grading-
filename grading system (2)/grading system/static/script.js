/**
 * ExamPro - Main JavaScript
 * Handles: Exam timer, malpractice detection, question navigation,
 *          toast notifications, password utils, confetti, UI helpers.
 */

'use strict';

// ──────────────────────────────────────────────
// SIDEBAR TOGGLE
// ──────────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('open');
}
// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    const toggle  = document.querySelector('.sidebar-toggle');
    if (sidebar && toggle && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});

// ──────────────────────────────────────────────
// TOAST NOTIFICATIONS
// ──────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = { success: 'fa-check-circle', danger: 'fa-exclamation-circle',
                    warning: 'fa-exclamation-triangle', info: 'fa-info-circle' };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(120%)';
        toast.style.transition = '.3s ease';
        setTimeout(() => toast.remove(), 350);
    }, duration);
}

// ──────────────────────────────────────────────
// PASSWORD TOGGLE
// ──────────────────────────────────────────────
function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    const btn = field.nextElementSibling;
    if (field.type === 'password') {
        field.type = 'text';
        if (btn) btn.querySelector('i').className = 'fas fa-eye-slash';
    } else {
        field.type = 'password';
        if (btn) btn.querySelector('i').className = 'fas fa-eye';
    }
}

// Password strength indicator on register page
const pwField = document.getElementById('password');
const strengthWrap = document.getElementById('strengthWrap');
if (pwField && strengthWrap) {
    pwField.addEventListener('input', () => {
        const val = pwField.value;
        strengthWrap.style.display = val.length > 0 ? 'block' : 'none';
        const bar   = document.getElementById('strengthBar');
        const label = document.getElementById('strengthLabel');
        let score = 0;
        if (val.length >= 6)  score++;
        if (val.length >= 10) score++;
        if (/[A-Z]/.test(val)) score++;
        if (/[0-9]/.test(val)) score++;
        if (/[^A-Za-z0-9]/.test(val)) score++;
        const levels = [
            { w: '20%', bg: '#ef4444', label: 'Weak' },
            { w: '40%', bg: '#f97316', label: 'Fair' },
            { w: '60%', bg: '#f59e0b', label: 'Good' },
            { w: '80%', bg: '#22c55e', label: 'Strong' },
            { w: '100%', bg: '#14b8a6', label: 'Excellent' },
        ];
        const level = levels[Math.min(score, 4)];
        bar.style.width      = level.w;
        bar.style.background = level.bg;
        label.textContent    = level.label;
        label.style.color    = level.bg;
    });
}

// ──────────────────────────────────────────────
// EXAM ENGINE
// ──────────────────────────────────────────────
let timerInterval  = null;
let timeLeft       = 0;        // seconds
let violations     = 0;
let answered       = new Set();
let currentQ       = 1;
let totalQuestions = 0;
let examActive     = false;

function initExam(minutes, total) {
    totalQuestions = total;
    timeLeft       = minutes * 60;
    examActive     = true;

    updateTimerDisplay();
    timerInterval = setInterval(tickTimer, 1000);

    // Try fullscreen
    showFullscreenPrompt();

    // Malpractice listeners
    setupMalpracticeDetection();

    // Disable right-click
    document.addEventListener('contextmenu', e => {
        e.preventDefault();
        showToast('Right-click is disabled during exam.', 'warning');
    });

    // Disable copy/paste
    ['copy', 'paste', 'cut'].forEach(evt => {
        document.addEventListener(evt, e => {
            e.preventDefault();
            showToast(`${evt.charAt(0).toUpperCase() + evt.slice(1)} is disabled during exam.`, 'warning');
        });
    });

    goToQuestion(1);
    updateProgress();
}

// ── Timer ──
function tickTimer() {
    if (!examActive) return;
    timeLeft--;
    updateTimerDisplay();

    if (timeLeft <= 0) {
        clearInterval(timerInterval);
        showToast('⏰ Time is up! Submitting exam...', 'danger', 3000);
        setTimeout(submitExam, 1500);
    }
}

function updateTimerDisplay() {
    const el = document.getElementById('timerDisplay');
    if (!el) return;
    const m = Math.floor(timeLeft / 60).toString().padStart(2, '0');
    const s = (timeLeft % 60).toString().padStart(2, '0');
    el.textContent = `${m}:${s}`;

    const wrap = document.getElementById('timerWrap');
    if (!wrap) return;
    wrap.classList.remove('warning', 'danger');
    if (timeLeft <= 60)  wrap.classList.add('danger');
    else if (timeLeft <= 300) wrap.classList.add('warning');
}

// ── Question Navigation ──
function goToQuestion(n) {
    // Hide all
    document.querySelectorAll('.question-card').forEach(c => c.style.display = 'none');
    document.querySelectorAll('.q-nav-btn').forEach(b => b.classList.remove('q-current'));

    const card = document.getElementById(`qCard${n}`);
    const btn  = document.getElementById(`qBtn${n}`);
    if (card) { card.style.display = 'block'; card.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
    if (btn) btn.classList.add('q-current');
    currentQ = n;
    updateProgress();
}

function markAnswered(questionId, optionIndex) {
    answered.add(questionId);

    // Style all labels for this question
    const labels = document.querySelectorAll(`input[name="q_${questionId}"]`);
    labels.forEach(input => {
        const label = input.closest('.option-label');
        if (label) label.classList.remove('selected');
    });
    const chosen = document.getElementById(`q${questionId}_${optionIndex + 1}`);
    if (chosen) chosen.closest('.option-label')?.classList.add('selected');

    // Mark nav button
    const btn = document.getElementById(`qBtn${currentQ}`);
    if (btn) { btn.classList.add('q-answered'); btn.classList.remove('q-current'); }

    updateProgress();
    updateAnsweredCount();
}

function updateProgress() {
    const pct = totalQuestions > 0 ? (answered.size / totalQuestions) * 100 : 0;
    const bar = document.getElementById('examProgressFill');
    if (bar) bar.style.width = pct + '%';
    updateAnsweredCount();
}

function updateAnsweredCount() {
    const el = document.getElementById('answeredCount');
    if (el) el.textContent = answered.size;
}

// ── Submit ──
function confirmSubmit() {
    const modal = document.getElementById('submitModal');
    if (modal) {
        document.getElementById('modalAnswered').textContent = answered.size;
        modal.classList.remove('hidden');
    }
}
function closeModal() {
    const modal = document.getElementById('submitModal');
    if (modal) modal.classList.add('hidden');
}
function submitExam() {
    examActive = false;
    clearInterval(timerInterval);
    document.getElementById('examForm')?.submit();
}

// ──────────────────────────────────────────────
// MALPRACTICE DETECTION
// ──────────────────────────────────────────────
function setupMalpracticeDetection() {
    // Tab visibility change
    document.addEventListener('visibilitychange', () => {
        if (!examActive) return;
        if (document.visibilityState === 'hidden') {
            handleViolation('Tab switch detected');
        }
    });

    // Window blur (clicking outside browser)
    window.addEventListener('blur', () => {
        if (!examActive) return;
        handleViolation('Window focus lost');
    });

    // Fullscreen exit
    document.addEventListener('fullscreenchange', () => {
        if (!examActive) return;
        if (!document.fullscreenElement) {
            handleViolation('Fullscreen exited');
            showFullscreenWarning();
        }
    });
}

function handleViolation(activity) {
    violations++;
    document.getElementById('violationsInput').value = violations;
    document.getElementById('malpracticeFlag').value = 1;

    // Log to server
    fetch('/api/log_malpractice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ activity: `${activity} (violation #${violations})` })
    }).catch(() => {});

    if (violations >= 3) {
        clearInterval(timerInterval);
        showToast('⚠️ 3 violations! Auto-submitting exam.', 'danger', 2000);
        setTimeout(submitExam, 2500);
    } else {
        showWarningOverlay(activity);
    }
}

function showWarningOverlay(activity) {
    const overlay = document.getElementById('warningOverlay');
    const msg     = document.getElementById('warningMessage');
    const cnt     = document.getElementById('violationCount');
    if (!overlay) return;
    if (msg) msg.textContent = `${activity} detected! This activity has been logged.`;
    if (cnt) cnt.textContent = violations;
    overlay.classList.remove('hidden');
}

function dismissWarning() {
    const overlay = document.getElementById('warningOverlay');
    if (overlay) overlay.classList.add('hidden');
    enterFullscreen();
}

function showFullscreenWarning() {
    showToast('⚠️ Please return to fullscreen mode!', 'warning', 3000);
}

// ──────────────────────────────────────────────
// FULLSCREEN
// ──────────────────────────────────────────────
function showFullscreenPrompt() {
    const prompt = document.getElementById('fullscreenPrompt');
    if (prompt) prompt.style.display = 'flex';
}

function enterFullscreen() {
    const prompt = document.getElementById('fullscreenPrompt');
    if (prompt) prompt.style.display = 'none';

    const el = document.documentElement;
    if (el.requestFullscreen)            el.requestFullscreen();
    else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    else if (el.mozRequestFullScreen)    el.mozRequestFullScreen();
}

// ──────────────────────────────────────────────
// CONFETTI (Result Page)
// ──────────────────────────────────────────────
function launchConfetti() {
    const container = document.getElementById('confetti-container');
    if (!container) return;

    const colors = ['#6366f1','#a855f7','#22c55e','#f59e0b','#3b82f6','#ec4899','#14b8a6'];
    const shapes = ['circle','square'];

    for (let i = 0; i < 120; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';

        const color = colors[Math.floor(Math.random() * colors.length)];
        const shape = shapes[Math.floor(Math.random() * shapes.length)];
        const size  = Math.random() * 10 + 6;
        const left  = Math.random() * 100;
        const delay = Math.random() * 3;
        const dur   = Math.random() * 3 + 2;

        piece.style.cssText = `
            left: ${left}%;
            width: ${size}px;
            height: ${size}px;
            background: ${color};
            border-radius: ${shape === 'circle' ? '50%' : '2px'};
            animation-duration: ${dur}s;
            animation-delay: ${delay}s;
        `;
        container.appendChild(piece);
    }

    // Remove after all done
    setTimeout(() => container.innerHTML = '', 7000);
}

// ──────────────────────────────────────────────
// FLASH MESSAGE AUTO-DISMISS
// ──────────────────────────────────────────────
document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transition = '.4s ease';
        setTimeout(() => alert.remove(), 450);
    }, 5000);
});

// ──────────────────────────────────────────────
// LANDING ANIMATIONS (Intersection Observer)
// ──────────────────────────────────────────────
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.style.opacity = '1';
            e.target.style.transform = 'translateY(0)';
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.feature-card, .stat-card').forEach(el => {
    el.style.opacity  = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity .5s ease, transform .5s ease';
    observer.observe(el);
});
