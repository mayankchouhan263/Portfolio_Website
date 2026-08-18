const CHAT_API_URL = "http://127.0.0.1:5000/api/chat";

const chatToggle = document.getElementById("chatToggle");
const chatPanel = document.getElementById("chatPanel");
const chatClose = document.getElementById("chatClose");
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatSend = document.getElementById("chatSend");

let history = []; // [{role: "user"|"assistant", content: "..."}]

function openChat() {
  chatPanel.classList.add("open");
  chatInput.focus();
}
function closeChat() {
  chatPanel.classList.remove("open");
}

chatToggle?.addEventListener("click", () => {
  chatPanel.classList.contains("open") ? closeChat() : openChat();
});
chatClose?.addEventListener("click", closeChat);

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `chat-msg ${role === "user" ? "user" : "bot"}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  addMessage(text, "user");
  history.push({ role: "user", content: text });
  chatInput.value = "";
  chatInput.disabled = true;

  const thinkingEl = addMessage("Thinking…", "bot");

  try {
    const res = await fetch(CHAT_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history }),
    });

    if (!res.ok) throw new Error(`Server responded ${res.status}`);
    const data = await res.json();
    const reply = data.reply || "Sorry, I couldn't generate a response.";
    thinkingEl.textContent = reply;
    history.push({ role: "assistant", content: reply });
  } catch (err) {
    thinkingEl.textContent =
      "I couldn't reach the chatbot server. Make sure the Flask backend is running (see chatbot-backend/README.md).";
    console.error(err);
  } finally {
    chatInput.disabled = false;
    chatInput.focus();
  }
}

chatSend?.addEventListener("click", sendMessage);
chatInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});
