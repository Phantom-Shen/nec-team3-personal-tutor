// This script runs on Canvas pages
console.log("Personal Tutor: Canvas Integration Active");

function getPageContext() {
    // 1. Try to get the main content of the page
    const content = document.querySelector('#content') || document.body;
    const text = content.innerText.slice(0, 5000); // Limit context size
    
    // 2. Look for Quiz questions specifically
    const quizQuestions = Array.from(document.querySelectorAll('.question_text')).map(q => q.innerText);
    
    // 3. Get Course/Module Name
    const crumbs = Array.from(document.querySelectorAll('.ic-app-crumbs')).map(c => c.innerText).join(' > ');

    return {
        text: text,
        quizzes: quizQuestions,
        path: crumbs,
        url: window.location.href
    };
}

// Listen for messages from the Popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getContext") {
        sendResponse(getPageContext());
    }
});

// --- NEW: UI INJECTION ---
function injectExplainButtons() {
    const questions = document.querySelectorAll('.question_text');
    questions.forEach(q => {
        if (q.querySelector('.tutor-explain-btn')) return; // Avoid duplicates

        const btn = document.createElement('button');
        btn.innerText = "💡 Explain";
        btn.className = 'tutor-explain-btn';
        btn.style.marginLeft = "10px";
        btn.style.padding = "2px 8px";
        btn.style.fontSize = "12px";
        btn.style.cursor = "pointer";
        btn.style.borderRadius = "4px";
        btn.style.border = "1px solid #007bff";
        btn.style.background = "white";
        btn.style.color = "#007bff";

        btn.onclick = () => {
            const text = q.innerText.replace("💡 Explain", "").trim();
            chrome.runtime.sendMessage({ action: "explainRequest", text: text });
            // Alert user to check the extension popup
            btn.innerText = "✅ Sent to Tutor";
            setTimeout(() => btn.innerText = "💡 Explain", 3000);
        };

        q.appendChild(btn);
    });
}

// Run injection periodically as Canvas loads content dynamically
setInterval(injectExplainButtons, 2000);
