// Session management
let sessionId = localStorage.getItem('aura_session_id');
if (!sessionId) {
    sessionId = 'session_' + Math.random().toString(36).substring(2, 9);
    localStorage.setItem('aura_session_id', sessionId);
}

const chatForm = document.getElementById('chatForm');

const userInput = document.getElementById('userInput');
const chatBody = document.getElementById('chatBody');

function scrollToBottom() {
    chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });
}

function clearChat() {
    const messages = chatBody.querySelectorAll('.message');
    // Keep only the first welcome message
    for (let i = 1; i < messages.length; i++) {
        messages[i].remove();
    }
}

function appendMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    
    // For bots, we can render basic HTML by stripping quotes or handling simple breaks if needed
    // But for a secure approach, we will just use TextNode, except if you want bolding
    const bubble = document.createElement('div');
    bubble.classList.add('bubble');
    bubble.textContent = text;
    
    msgDiv.appendChild(bubble);
    chatBody.appendChild(msgDiv);
    scrollToBottom();
}

function appendLoading() {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', 'bot', 'loading-msg');
    
    const bubble = document.createElement('div');
    bubble.classList.add('bubble');
    
    const dots = document.createElement('div');
    dots.classList.add('loading-dots');
    dots.innerHTML = '<span></span><span></span><span></span>';
    
    bubble.appendChild(dots);
    msgDiv.appendChild(bubble);
    chatBody.appendChild(msgDiv);
    scrollToBottom();
    
    return msgDiv;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const text = userInput.value.trim();
    if (!text) return;
    
    // 1. Add user message
    appendMessage(text, 'user');
    userInput.value = '';
    
    // 2. Add loading animation
    const loadingMessage = appendLoading();
    
    try {
        // 3. Fetch from our Python Flask Backend
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: text,
                session_id: sessionId 
            })
        });
        
        const data = await response.json();
        
        // Remove loading
        loadingMessage.remove();
        
        // 4. Add bot response
        if (data.response) {
            appendMessage(data.response, 'bot');
        } else {
            appendMessage(data.error || "Something went wrong.", 'bot');
        }
        
    } catch (err) {
        loadingMessage.remove();
        appendMessage("Unable to connect to the server. Is it running?", 'bot');
    }
});
