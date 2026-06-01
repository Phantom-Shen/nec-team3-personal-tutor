const chatContainer = document.getElementById('chat-container');
const masteryDashboard = document.getElementById('mastery-dashboard');
const activityLog = document.getElementById('activity-log');
const tutorMode = document.getElementById('tutor-mode');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

const API_URL = 'http://localhost:8000';

function addMessage(text, sender) {
  const div = document.createElement('div');
  div.className = `message ${sender}`;
  div.innerText = text;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return div;
}

function updateModeUI(mode) {
    tutorMode.innerText = `Mode: ${mode}`;
    tutorMode.style.background = mode === 'Remedial' ? '#ffebee' : (mode === 'Mastery' ? '#e8f5e9' : '#e3f2fd');
}

async function fetchMastery() {
  try {
    const response = await fetch(`${API_URL}/mastery`);
    if (!response.ok) return;
    const data = await response.json();
    masteryDashboard.innerHTML = '';
    
    if (data.length > 0) {
        const avg = data.reduce((acc, curr) => acc + curr.score, 0) / data.length;
        const mode = avg < 0.4 ? "Remedial" : (avg > 0.7 ? "Mastery" : "Scaffolding");
        updateModeUI(mode);
    } else {
        updateModeUI("Scaffolding");
    }

    data.slice(0, 2).forEach(item => {
      const card = document.createElement('div');
      card.className = 'mastery-card';
      card.innerHTML = `
        <strong>${item.concept}</strong>
        <div class="mastery-bar">
          <div class="mastery-fill" style="width: ${item.score * 100}%"></div>
        </div>
      `;
      masteryDashboard.appendChild(card);
    });

    const histResponse = await fetch(`${API_URL}/history`);
    if (!histResponse.ok) return;
    const histData = await histResponse.json();
    activityLog.innerHTML = '<strong>Recent Activity:</strong><br>';
    histData.slice(0, 3).forEach(h => {
      const color = h.delta > 0 ? 'green' : (h.delta < 0 ? 'red' : 'gray');
      activityLog.innerHTML += `<span style="color: ${color}">${h.delta > 0 ? '+' : ''}${h.delta}</span> ${h.concept}<br>`;
    });
  } catch (e) {
    console.error('Failed to fetch stats', e);
  }
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  // Capture history BEFORE adding the new user message to the UI
  const history = Array.from(chatContainer.querySelectorAll('.message:not(.thinking)')).map(div => ({
    sender: div.classList.contains('user') ? 'user' : 'tutor',
    text: div.innerText
  }));

  addMessage(text, 'user');
  userInput.value = '';
  
  // Show thinking indicator
  const thinkingDiv = addMessage('Tutor is thinking...', 'thinking');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    let context = {};
    try {
      context = await chrome.tabs.sendMessage(tab.id, { action: "getContext" });
    } catch (e) {}

    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message: text, 
        context: context,
        history: history 
      })
    });
    
    // Remove thinking indicator
    thinkingDiv.remove();

    const data = await response.json();
    
    if (!response.ok) {
        addMessage(`Error: ${data.detail || 'Unknown error'}`, 'tutor');
        return;
    }

    addMessage(data.reply, 'tutor');
    updateModeUI(data.mode);
    fetchMastery();
  } catch (e) {
    if (typeof thinkingDiv !== 'undefined') thinkingDiv.remove();
    addMessage('Error: Connection to backend failed.', 'tutor');
  }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendMessage();
});

// Initial load
fetchMastery();
setInterval(fetchMastery, 5000); // Poll for updates

// Listen for messages from Content Script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "explainRequest") {
    userInput.value = `Can you explain this: "${request.text}"?`;
    sendMessage(); // Auto-send the request
  }
});
