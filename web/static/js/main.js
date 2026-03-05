// web/static/js/main.js
// BracketClick Photo Booth - Frontend Logic
// GDG AI Committee - Project 01

// ==================== Global State ====================
let emailSubmitted = false;
let statusPollingInterval = null;
let cooldownInterval = null;

// ==================== Email Submission ====================
async function submitEmail() {
    const emailInput = document.getElementById('email-input');
    const email = emailInput.value.trim();
    
    // Validate email
    if (!email || !email.includes('@')) {
        alert('Please enter a valid email address');
        return;
    }
    
    try {
        const response = await fetch('/set_email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log('[OK] Email submitted:', email);
            emailSubmitted = true;
            
            // Hide email section, show camera section
            document.getElementById('email-section').style.display = 'none';
            document.getElementById('camera-section').style.display = 'block';
            
            const video = document.getElementById('video-feed');
            if (video) {
            const feedUrl = video.getAttribute('data-src');

            // ✅ always set src after switching sections
            video.setAttribute('src', feedUrl);

            // ✅ optional: avoid browser caching weirdness
            // video.setAttribute('src', feedUrl + "?t=" + Date.now());
            }
            // Start polling for status updates
            startStatusPolling();
            
        } else {
            alert('Error: ' + data.message);
        }
    } catch (error) {
        console.error('[ERROR] Failed to submit email:', error);
        alert('Failed to connect to server. Please try again.');
    }
}

// ==================== Status Polling ====================
function startStatusPolling() {
    // Poll server every 500ms for status updates
    statusPollingInterval = setInterval(updateStatus, 500);
}

function stopStatusPolling() {
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
        statusPollingInterval = null;
    }
}

async function updateStatus() {
    try {
        const response = await fetch('/status');
        const status = await response.json();
        
        updateUI(status);
        
    } catch (error) {
        console.error('[ERROR] Failed to fetch status:', error);
    }
}

// ==================== UI Updates ====================
function updateUI(status) {
    // Update gesture indicators
    updateGestureIndicators(status);
    
    // Update status message
    updateStatusMessage(status);
    
    // Countdown and cooldown are drawn in the video frame by the backend.
    // Do not show frontend overlay divs (would duplicate and cause ghosting).
    
    // Handle capture complete
    if (status.capture_complete && !status.cooldown_active) {
        showSuccess();
    }
}

function updateGestureIndicators(status) {
    // Note: Backend doesn't send individual hand status yet
    // For now, we show overall gesture detection
    const leftStatus = document.getElementById('left-hand-status');
    const rightStatus = document.getElementById('right-hand-status');
    
    if (status.gesture_detected) {
        // Both hands detected
        leftStatus.classList.add('ready');
        rightStatus.classList.add('ready');
        
        // Update checkmarks
        leftStatus.querySelector('.hand-check').textContent = '✓';
        rightStatus.querySelector('.hand-check').textContent = '✓';
    } else {
        // No gesture detected
        leftStatus.classList.remove('ready');
        rightStatus.classList.remove('ready');
        
        leftStatus.querySelector('.hand-check').textContent = '✗';
        rightStatus.querySelector('.hand-check').textContent = '✗';
    }
}

function updateStatusMessage(status) {
    const statusText = document.getElementById('status-text');
    
    if (!status.email_set) {
        statusText.textContent = 'Please enter your email first';
    } else if (status.cooldown_active) {
        statusText.textContent = 'Photo captured! Please wait...';
    } else if (status.countdown_active) {
        statusText.textContent = `Capturing in ${status.countdown_value}...`;
    } else if (status.gesture_detected) {
        statusText.textContent = 'Perfect! Hold the gesture...';
    } else {
        statusText.textContent = 'Form <> with BOTH hands to capture!';
    }
}

// ==================== Countdown Display ====================
function showCountdown(value) {
    const overlay = document.getElementById('countdown-overlay');
    overlay.textContent = value;
    overlay.style.display = 'block';
    
    // Visual feedback
    if (value <= 3) {
        overlay.style.color = '#FFD700'; // Gold
    }
    if (value <= 1) {
        overlay.style.color = '#34A853'; // Green
    }
}

function hideCountdown() {
    const overlay = document.getElementById('countdown-overlay');
    overlay.style.display = 'none';
}

// ==================== Cooldown Display ====================
function showCooldown() {
    const overlay = document.getElementById('cooldown-overlay');
    const cooldownText = document.getElementById('cooldown-text');
    
    overlay.style.display = 'block';
    cooldownText.textContent = 'Wait...';
    
    // Start countdown timer for cooldown
    let seconds = 3;
    cooldownText.textContent = `Wait ${seconds}s...`;
    
    if (cooldownInterval) clearInterval(cooldownInterval);
    
    cooldownInterval = setInterval(() => {
        seconds--;
        if (seconds > 0) {
            cooldownText.textContent = `Wait ${seconds}s...`;
        } else {
            clearInterval(cooldownInterval);
        }
    }, 1000);
}

function hideCooldown() {
    const overlay = document.getElementById('cooldown-overlay');
    overlay.style.display = 'none';
    
    if (cooldownInterval) {
        clearInterval(cooldownInterval);
        cooldownInterval = null;
    }
}

// ==================== Success Display ====================
function showSuccess() {
    stopStatusPolling();
    
    // Hide camera section, show success section
    document.getElementById('camera-section').style.display = 'none';
    document.getElementById('success-section').style.display = 'block';
    
    // Show confirmed email
    const emailInput = document.getElementById('email-input');
    document.getElementById('confirmed-email').textContent = emailInput.value;
    
    console.log('[OK] Photo captured successfully!');
}

// ==================== Reset Booth ====================
async function resetBooth() {
    try {
        // Call reset endpoint
        await fetch('/reset');
        
        // Reset UI
        document.getElementById('success-section').style.display = 'none';
        document.getElementById('email-section').style.display = 'block';
        
        // Clear email input
        document.getElementById('email-input').value = '';
        
        // Reset state
        emailSubmitted = false;
        
        // Restart polling
        startStatusPolling();
        
        console.log('[OK] Booth reset for next photo');
        
    } catch (error) {
        console.error('[ERROR] Failed to reset:', error);
    }
}

// ==================== Allow Enter Key for Email ====================
document.addEventListener('DOMContentLoaded', () => {
    const emailInput = document.getElementById('email-input');
    
    if (emailInput) {
        emailInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
              e.preventDefault();   // ✅ يمنع أي submit/reload
              submitEmail();
            }
          });
    }
    
    console.log('[OK] BracketClick Photo Booth loaded');
    console.log('[INFO] Ready to capture brackets <>');
});

// ==================== Error Handling ====================
window.addEventListener('error', (e) => {
    console.error('[ERROR] Global error:', e.error);
});

// ==================== Debug Mode (Optional) ====================
// Uncomment to enable debug logging
// window.DEBUG = true;
// function debugLog(msg) {
//     if (window.DEBUG) console.log('[DEBUG]', msg);
// }