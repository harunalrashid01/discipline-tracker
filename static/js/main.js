/**
 * main.js — Discipline Tracker
 *
 * Handles:
 *   1. Task completion (Done button → AJAX → visual update)
 *   2. Task undo (Undo button → AJAX → visual update)
 *   3. Progress bar live update
 *   4. Moving cards between pending/completed sections
 */

"use strict";

// ─── CSRF and URL helpers ─────────────────────────────────────────
// These are set in home.html's <script> block
function getCsrfToken() {
  return window.CSRF_TOKEN || "";
}

function buildUrl(template, id) {
  return template.replace("{id}", id);
}

// ─── Update Progress Bar ──────────────────────────────────────────
function updateProgress(doneCount, total, pct) {
  const bar = document.getElementById("progress-bar-fill");
  const count = document.getElementById("progress-count");

  if (bar) {
    bar.style.width = pct + "%";
    bar.setAttribute("aria-valuenow", pct);
  }

  if (count) {
    count.textContent = doneCount + " / " + total + " completed";
  }
}

// ─── Check if all tasks are done → show celebration banner ───────
function checkAllDone(total, doneCount) {
  const banner = document.getElementById("all-done-banner");
  if (!banner) return;
  if (doneCount >= total && total > 0) {
    banner.style.display = "block";
    banner.style.animation = "fadeIn 0.5s ease";
  } else {
    banner.style.display = "none";
  }
}

// ─── Complete a Task ──────────────────────────────────────────────
function completeTask(taskId) {
  const card = document.getElementById("task-card-" + taskId);
  const btn  = document.getElementById("done-btn-" + taskId);
  if (!card || !btn) return;

  // Disable button immediately to prevent double-click
  btn.disabled = true;
  card.classList.add("completing");

  const url = buildUrl(window.COMPLETE_URL, taskId);

  fetch(url, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
      "Content-Type": "application/json",
    },
  })
    .then((res) => {
      return res.json().then((data) => ({ ok: res.ok, data }));
    })
    .then(({ ok, data }) => {
      if (ok && data.status === "ok") {
        // Move card from pending list to completed list
        moveCardToCompleted(card, taskId);
        // Update progress bar
        updateProgress(data.done_count, data.total, data.progress_pct);
        checkAllDone(data.total, data.done_count);
      } else {
        // Something went wrong — re-enable button
        btn.disabled = false;
        card.classList.remove("completing");
        if (data && data.message) {
          alert(data.message);
        }
      }
    })
    .catch(() => {
      btn.disabled = false;
      card.classList.remove("completing");
      alert("Could not save. Please check your connection.");
    });
}

// ─── Undo a Task ─────────────────────────────────────────────────
function undoTask(taskId) {
  const card = document.getElementById("task-card-" + taskId);
  const btn  = document.getElementById("undo-btn-" + taskId);
  if (!card || !btn) return;

  btn.disabled = true;
  card.classList.add("undoing");

  const url = buildUrl(window.UNDO_URL, taskId);

  fetch(url, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
      "Content-Type": "application/json",
    },
  })
    .then((res) => {
      return res.json().then((data) => ({ ok: res.ok, data }));
    })
    .then(({ ok, data }) => {
      if (ok && data.status === "ok") {
        // Move card back to pending list
        moveCardToPending(card, taskId);
        // Update progress bar
        updateProgress(data.done_count, data.total, data.progress_pct);
        checkAllDone(data.total, data.done_count);
      } else {
        btn.disabled = false;
        card.classList.remove("undoing");
        if (data && data.message) {
          alert(data.message);
        }
      }
    })
    .catch(() => {
      btn.disabled = false;
      card.classList.remove("undoing");
      alert("Could not undo. Please check your connection.");
    });
}

// ─── Move card to Completed section ──────────────────────────────
function moveCardToCompleted(card, taskId) {
  // Short delay so user sees the animation
  setTimeout(() => {
    card.classList.remove("completing", "task-card--pending");
    card.classList.add("task-card--completed");

    // Change the task number badge style
    const numEl = card.querySelector(".task-number");
    if (numEl) numEl.classList.add("completed-num");

    // Strike through title
    const titleEl = card.querySelector(".task-title");
    if (titleEl) titleEl.classList.add("task-title--done");

    const descEl = card.querySelector(".task-desc");
    if (descEl) descEl.classList.add("task-desc--done");

    // Replace Done button with Undo button
    const oldBtn = card.querySelector(".btn-done");
    if (oldBtn) {
      const undoBtn = document.createElement("button");
      undoBtn.className = "btn-undo";
      undoBtn.id = "undo-btn-" + taskId;
      undoBtn.setAttribute("aria-label", "Undo task");
      undoBtn.textContent = "↩ Undo";
      undoBtn.onclick = function () { undoTask(taskId); };
      oldBtn.replaceWith(undoBtn);
    }

    // Move to completed list — create list if it doesn't exist
    let completedList = document.getElementById("completed-list");

    if (!completedList) {
      // Create the completed group section
      const bookSection = document.querySelector(".book-section");
      const groupDiv = document.createElement("div");
      groupDiv.className = "tasks-group";
      groupDiv.id = "completed-group";
      groupDiv.innerHTML = `
        <h2 class="tasks-group-heading completed-heading">
          <span class="heading-dot dot-completed"></span>
          COMPLETED TASKS
        </h2>
        <div class="task-list" id="completed-list"></div>
      `;
      bookSection.appendChild(groupDiv);
      completedList = document.getElementById("completed-list");
    }

    completedList.appendChild(card);

    // Refresh slot filter visibility
    filterBySlot(window.currentSlotFilter, document.querySelector(".time-tab-btn.active"));
  }, 280);
}

// ─── Move card back to Pending section ───────────────────────────
function moveCardToPending(card, taskId) {
  setTimeout(() => {
    card.classList.remove("undoing", "task-card--completed");
    card.classList.add("task-card--pending");

    // Restore number badge
    const numEl = card.querySelector(".task-number");
    if (numEl) numEl.classList.remove("completed-num");

    // Remove strikethrough
    const titleEl = card.querySelector(".task-title");
    if (titleEl) titleEl.classList.remove("task-title--done");

    const descEl = card.querySelector(".task-desc");
    if (descEl) descEl.classList.remove("task-desc--done");

    // Replace Undo button with Done button
    const oldBtn = card.querySelector(".btn-undo");
    if (oldBtn) {
      const doneBtn = document.createElement("button");
      doneBtn.className = "btn-done";
      doneBtn.id = "done-btn-" + taskId;
      doneBtn.setAttribute("aria-label", "Mark task as done");
      doneBtn.textContent = "✓ Done";
      doneBtn.onclick = function () { completeTask(taskId); };
      oldBtn.replaceWith(doneBtn);
    }

    // Move back to pending list
    let pendingList = document.getElementById("pending-list");
    if (pendingList) {
      pendingList.appendChild(card);
    }

    // Refresh slot filter visibility
    filterBySlot(window.currentSlotFilter, document.querySelector(".time-tab-btn.active"));
  }, 280);
}

// ─── Filter Tasks By Time Slot ──────────────────────────────────
window.currentSlotFilter = "current";

function filterBySlot(slot, btnElement) {
  window.currentSlotFilter = slot;

  // Update tab buttons active state
  const tabBtns = document.querySelectorAll(".time-tab-btn");
  tabBtns.forEach((btn) => btn.classList.remove("active"));
  if (btnElement) {
    btnElement.classList.add("active");
  }

  const activeSlot = window.CURRENT_TIME_SLOT || "morning";
  const targetSlot = (slot === "current") ? activeSlot : slot;

  let visibleCount = 0;
  let pendingVisible = 0;
  let completedVisible = 0;

  const allCards = document.querySelectorAll(".task-card[data-time-slot]");
  allCards.forEach((card) => {
    const cardSlot = card.dataset.timeSlot || "anytime";
    let isVisible = false;

    if (slot === "all") {
      isVisible = true;
    } else {
      isVisible = (cardSlot === targetSlot || cardSlot === "anytime");
    }

    if (isVisible) {
      card.style.display = "";
      visibleCount++;
      if (card.closest("#pending-list")) pendingVisible++;
      if (card.closest("#completed-list")) completedVisible++;
    } else {
      card.style.display = "none";
    }
  });

  // Handle visibility of group containers
  const pendingGroup = document.getElementById("pending-group");
  if (pendingGroup) {
    pendingGroup.style.display = (pendingVisible > 0) ? "" : "none";
  }

  const completedGroup = document.getElementById("completed-group");
  if (completedGroup) {
    completedGroup.style.display = (completedVisible > 0) ? "" : "none";
  }

  // Handle empty slot state
  const emptySlotEl = document.getElementById("empty-slot-state");
  const overallEmptyEl = document.getElementById("overall-empty-state");

  if (emptySlotEl && allCards.length > 0) {
    if (visibleCount === 0) {
      emptySlotEl.style.display = "block";
      const msgEl = document.getElementById("empty-slot-msg");
      if (msgEl) {
        const slotNames = {
          morning: "Morning (5:30 AM – 10:00 AM)",
          afternoon: "Afternoon (10:00 AM – 6:00 PM)",
          evening: "Evening (6:00 PM – 10:00 PM)",
        };
        const name = slotNames[targetSlot] || targetSlot;
        msgEl.textContent = `No tasks scheduled in the ${name} section.`;
      }
    } else {
      emptySlotEl.style.display = "none";
    }
  }
}

// ─── On page load ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
  // Animate progress bar on load
  const bar = document.getElementById("progress-bar-fill");
  if (bar) {
    const width = bar.style.width;
    bar.style.width = "0%";
    setTimeout(() => {
      bar.style.width = width;
    }, 200);
  }

  // Initialize slot filter to current active time slot
  const currentTabBtn = document.getElementById("tab-btn-current");
  if (currentTabBtn) {
    filterBySlot("current", currentTabBtn);
  }
});

