const promptLibrary = [
  "Gia đình tôi có 4 người, muốn đi cắm trại cuối tuần gần Hà Nội và có trẻ nhỏ. Gợi ý địa điểm và đồ cần chuẩn bị.",
  "Nếu trời có mưa nhẹ thì lịch trình cắm trại 2 ngày 1 đêm nên điều chỉnh thế nào cho an toàn?",
  "So sánh nhanh giúp tôi giữa một kế hoạch tối giản và một kế hoạch đầy đủ cho chuyến cắm trại gia đình.",
  "Tôi đi từ Gia Lâm, ngân sách vừa phải, ưu tiên nơi sạch sẽ và dễ di chuyển. Hãy lên kế hoạch cụ thể.",
];

const metricTemplates = {
  baseline: [
    { label: "Provider / Model", value: "Gemini / Flash", caption: "Chế độ trả lời một lần" },
    { label: "Độ trễ", value: "1.2s", caption: "Phản hồi nhanh" },
    { label: "Số lần gọi tool", value: "0", caption: "Không dùng công cụ ngoài" },
    { label: "Tokens / Bước", value: "~420 / 1", caption: "One-shot completion" },
  ],
  agent: [
    { label: "Provider / Model", value: "Gemini / Flash", caption: "Agent điều phối theo bước" },
    { label: "Độ trễ", value: "3.8s", caption: "Có thời gian phân tích và gọi tool" },
    { label: "Số lần gọi tool", value: "3", caption: "Địa điểm, thời tiết, gợi ý đồ đạc" },
    { label: "Tokens / Bước", value: "~1180 / 4", caption: "Minh bạch hơn nhưng tốn tài nguyên hơn" },
  ],
};

const dom = {
  modeSelector: document.querySelector("#mode-selector"),
  promptChips: document.querySelector("#prompt-chips"),
  chatStream: document.querySelector("#chat-stream"),
  emptyState: document.querySelector("#empty-state"),
  composerForm: document.querySelector("#composer-form"),
  promptInput: document.querySelector("#prompt-input"),
  sendButton: document.querySelector("#send-button"),
  activeModeBadge: document.querySelector("#active-mode-badge"),
  activeStateBadge: document.querySelector("#active-state-badge"),
  statusPill: document.querySelector("#status-pill"),
  traceModeLabel: document.querySelector("#trace-mode-label"),
  metricsGrid: document.querySelector("#metrics-grid"),
  traceTimeline: document.querySelector("#trace-timeline"),
  toolList: document.querySelector("#tool-list"),
  runStatusText: document.querySelector("#run-status-text"),
  runStatusDetail: document.querySelector("#run-status-detail"),
};

const state = {
  mode: "baseline",
  messages: [],
  traceSteps: [],
  toolCalls: [],
  metrics: metricTemplates.baseline,
  status: "ready",
};

const apiEndpoint = `${window.location.origin}/api/chat`;

function renderPromptChips() {
  dom.promptChips.innerHTML = "";
  promptLibrary.forEach((prompt) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "prompt-chip";
    button.textContent = prompt;
    button.addEventListener("click", () => {
      dom.promptInput.value = prompt;
      autoResizeTextarea();
      dom.promptInput.focus();
    });
    dom.promptChips.appendChild(button);
  });
}

function setMode(mode) {
  state.mode = mode;
  state.metrics = metricTemplates[mode];
  state.traceSteps = [];
  state.toolCalls = [];
  state.messages = [];
  updateStatus("ready");
  renderModeSelector();
  renderMetrics();
  renderTrace();
  renderTools();
  renderHeaderState();
  renderMessages();
}

function renderModeSelector() {
  const buttons = dom.modeSelector.querySelectorAll(".mode-card");
  buttons.forEach((button) => {
    const active = button.dataset.mode === state.mode;
    button.classList.toggle("active", active);
  });
  dom.activeModeBadge.textContent =
    state.mode === "baseline" ? "Chatbot Baseline" : "ReAct Agent";
  dom.traceModeLabel.textContent =
    state.mode === "baseline" ? "Ẩn trong Baseline" : "Hiển thị theo từng bước";
}

function updateStatus(status) {
  state.status = status;
  const statusMap = {
    ready: {
      label: "Sẵn sàng",
      detail: "Chọn chế độ và gửi câu hỏi để bắt đầu phiên demo.",
    },
    running: {
      label: "Đang xử lý",
      detail: "Hệ thống đang tạo phản hồi và cập nhật tiến trình thực thi.",
    },
    done: {
      label: "Hoàn tất",
      detail: "Phiên vừa chạy xong và sẵn sàng cho lượt so sánh tiếp theo.",
    },
  };
  const meta = statusMap[status];
  dom.activeStateBadge.textContent = meta.label;
  dom.statusPill.textContent = meta.label;
  dom.runStatusText.textContent = meta.label;
  dom.runStatusDetail.textContent = meta.detail;
}

function renderMetrics() {
  dom.metricsGrid.innerHTML = "";
  state.metrics.forEach((metric) => {
    const item = document.createElement("div");
    item.className = "metric-item";
    item.innerHTML = `
      <div class="section-kicker">${metric.label}</div>
      <div class="metric-value">${metric.value}</div>
      <div class="metric-caption">${metric.caption}</div>
    `;
    dom.metricsGrid.appendChild(item);
  });
}

function renderTrace() {
  dom.traceTimeline.innerHTML = "";
  if (state.mode === "baseline") {
    dom.traceTimeline.innerHTML = `
      <div class="trace-empty">
        <h3>Baseline không hiển thị trace</h3>
        <p>
          Đây là điểm khác biệt quan trọng trong demo: hệ thống chỉ trả lời đầu
          ra cuối cùng, không cho thấy quá trình suy nghĩ hay dùng tool.
        </p>
      </div>
    `;
    return;
  }
  if (state.traceSteps.length === 0) {
    dom.traceTimeline.innerHTML = `
      <div class="trace-empty">
        <h3>Chưa có trace</h3>
        <p>Gửi một câu hỏi để xem agent xử lý theo từng bước.</p>
      </div>
    `;
    return;
  }
  state.traceSteps.forEach((step) => {
    const item = document.createElement("article");
    item.className = `trace-step ${step.kind === "final" ? "final" : ""}`;
    item.innerHTML = `
      <div class="trace-step-header">
        <span class="trace-kind">${step.title}</span>
        <span class="trace-kind-label">${step.badge}</span>
      </div>
      <div class="trace-content">${step.content}</div>
    `;
    dom.traceTimeline.appendChild(item);
  });
}

function renderTools() {
  dom.toolList.innerHTML = "";
  if (state.toolCalls.length === 0) {
    dom.toolList.innerHTML = `
      <div class="tool-empty">Chưa có tool nào được gọi trong phiên hiện tại.</div>
    `;
    return;
  }
  state.toolCalls.forEach((tool, index) => {
    const item = document.createElement("article");
    item.className = "tool-item";
    item.innerHTML = `
      <div class="tool-item-header">
        <span class="tool-name">${tool.name}</span>
        <span class="tool-tag">Lần ${index + 1}</span>
      </div>
      <div class="tool-json">${tool.summary}</div>
    `;
    dom.toolList.appendChild(item);
  });
}

function renderMessages() {
  dom.chatStream.innerHTML = "";
  if (state.messages.length === 0) {
    dom.chatStream.appendChild(dom.emptyState);
    return;
  }
  state.messages.forEach((message) => {
    const item = document.createElement("article");
    item.className = `message ${message.role}`;
    item.innerHTML = `
      <div class="message-meta">${message.label}</div>
      <div class="bubble">${message.content}</div>
    `;
    dom.chatStream.appendChild(item);
  });
  dom.chatStream.scrollTop = dom.chatStream.scrollHeight;
}

function renderHeaderState() {
  const running = state.status === "running";
  dom.statusPill.innerHTML = running
    ? `<span class="running-indicator">Đang xử lý</span>`
    : state.status === "done"
      ? "Hoàn tất"
      : "Sẵn sàng";
}

function autoResizeTextarea() {
  dom.promptInput.style.height = "auto";
  dom.promptInput.style.height = `${Math.min(dom.promptInput.scrollHeight, 200)}px`;
}

function appendMessage(role, content, label) {
  state.messages.push({ role, content: cleanAssistantText(content), label });
  renderMessages();
}

function cleanAssistantText(text) {
  if (!text) {
    return "";
  }

  return String(text)
    .replace(/\r/g, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/`{1,3}/g, "")
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/^\s*\d+\.\s+/gm, (match) => match.trim())
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function formatMetrics(metrics) {
  if (!metrics) {
    return metricTemplates[state.mode];
  }
  const usage = metrics.usage || {};
  return [
    {
      label: "Provider / Model",
      value: `${metrics.provider || "unknown"} / ${metrics.model || "unknown"}`,
      caption: state.mode === "baseline" ? "Phản hồi một lần" : "Điều phối theo vòng lặp ReAct",
    },
    {
      label: "Độ trễ",
      value: `${metrics.latency_ms || 0} ms`,
      caption: "Tổng thời gian xử lý",
    },
    {
      label: "Số lần gọi tool",
      value: String(metrics.tool_calls || 0),
      caption: "Số hành động có dùng công cụ",
    },
    {
      label: "Tokens / Bước",
      value: `${usage.total_tokens || 0} / ${metrics.steps || 1}`,
      caption: "Tổng tokens và số bước thực thi",
    },
  ];
}

function formatTrace(trace) {
  return (trace || []).map((step) => ({
    title: step.title,
    badge:
      step.type === "thought"
        ? `Bước ${step.step}`
        : step.type === "action"
          ? "Tool"
          : step.type === "observation"
            ? "Kết quả"
            : "Final Answer",
    kind: step.type,
    content: step.content,
  }));
}

function formatTools(toolCalls) {
  return (toolCalls || []).map((tool) => ({
    name: tool.name,
    summary: `Đầu vào:\n${tool.arguments}\n\nQuan sát:\n${tool.observation}`,
  }));
}

async function requestChat(question) {
  const response = await fetch(apiEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      mode: state.mode,
    }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.error || "Yêu cầu thất bại.");
  }
  return data;
}

async function handleSubmit(event) {
  event.preventDefault();
  const question = dom.promptInput.value.trim();
  if (!question || state.status === "running") {
    return;
  }

  updateStatus("running");
  renderHeaderState();
  dom.sendButton.disabled = true;

  appendMessage("user", question, "Bạn");
  appendMessage(
    "system",
    state.mode === "baseline"
      ? "Hệ thống đang tạo câu trả lời trực tiếp cho yêu cầu của bạn."
      : "Agent đang phân tích yêu cầu, gọi tool và cập nhật trace theo từng bước.",
    "Trạng thái hệ thống",
  );

  dom.promptInput.value = "";
  autoResizeTextarea();

  try {
    const data = await requestChat(question);
    state.metrics = formatMetrics(data.metrics);
    renderMetrics();

    if (state.mode === "agent") {
      state.traceSteps = formatTrace(data.trace);
      state.toolCalls = formatTools(data.tool_calls);
      renderTrace();
      renderTools();
    } else {
      state.traceSteps = [];
      state.toolCalls = [];
      renderTrace();
      renderTools();
    }

    appendMessage(
      "assistant",
      data.answer,
      state.mode === "baseline" ? "Trợ lý Baseline" : "Trợ lý Agent",
    );
    updateStatus("done");
  } catch (error) {
    appendMessage(
      "assistant",
      `Không thể lấy phản hồi từ backend.\n\nChi tiết: ${error.message}\n\nHãy kiểm tra API key trong file .env và chạy server bằng lệnh \`python web_demo.py\`.`,
      "Lỗi hệ thống",
    );
    updateStatus("ready");
  } finally {
    renderHeaderState();
    dom.sendButton.disabled = false;
  }
}

dom.modeSelector.addEventListener("click", (event) => {
  const target = event.target.closest("[data-mode]");
  if (!target || state.status === "running") {
    return;
  }
  setMode(target.dataset.mode);
});

dom.composerForm.addEventListener("submit", handleSubmit);
dom.promptInput.addEventListener("input", autoResizeTextarea);

renderPromptChips();
setMode("baseline");
renderMessages();
