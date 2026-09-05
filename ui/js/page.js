(() => {
    let context = {
        history: [],
        queue: [],
    };

    function send(message) {
        window.parent.postMessage(
            message,
            "*"
        );
    }

    function setupExternalLinks() {
        document
            .querySelectorAll("[data-external-url]")
            .forEach((link) => {
                link.addEventListener("click", (event) => {
                    event.preventDefault();
                    send({
                        type: "open-external",
                        url: link.dataset.externalUrl,
                    });
                });
            });
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function escapeAttribute(value) {
        return escapeHtml(value).replaceAll(
            "`",
            "&#096;"
        );
    }

    function enablePageScrolling() {
        document.documentElement.style.height =
            "auto";
        document.documentElement.style.minHeight =
            "100%";
        document.documentElement.style.overflowX =
            "hidden";
        document.documentElement.style.overflowY =
            "auto";

        document.body.style.height = "auto";
        document.body.style.minHeight = "100%";
        document.body.style.overflowX = "hidden";
        document.body.style.overflowY = "auto";

        const style = document.createElement(
            "style"
        );

        style.textContent = `
            html {
                scrollbar-width: none !important;
                -ms-overflow-style: none !important;
            }

            body {
                scrollbar-width: none !important;
                -ms-overflow-style: none !important;
            }

            html::-webkit-scrollbar,
            body::-webkit-scrollbar {
                width: 0 !important;
                height: 0 !important;
                display: none !important;
            }
        `;

        document.head.appendChild(style);
    }

    function setCurrentYear() {
        const year = new Date().getFullYear();

        document
            .querySelectorAll(
                "[data-current-year]"
            )
            .forEach((node) => {
                node.textContent = year;
            });
    }

    function formatDate(timestamp) {
        const date = new Date(timestamp);

        if (Number.isNaN(date.getTime())) {
            return "";
        }

        return date.toLocaleString([], {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
        });
    }

    function formatBytes(value) {
        const bytes = Number(value || 0);

        if (!bytes) {
            return "";
        }

        const units = [
            "B",
            "KB",
            "MB",
            "GB",
        ];

        let amount = bytes;
        let index = 0;

        while (
            amount >= 1024 &&
            index < units.length - 1
        ) {
            amount /= 1024;
            index += 1;
        }

        if (index === 0) {
            return `${Math.round(amount)} ${units[index]}`;
        }

        return `${amount.toFixed(1)} ${units[index]}`;
    }

    function formatSpeed(value) {
        if (!value) {
            return "";
        }

        return `${formatBytes(value)}/s`;
    }

    function formatEta(value) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return "";
        }

        const total = Number(value);

        if (!Number.isFinite(total)) {
            return "";
        }

        const minutes = Math.floor(total / 60);
        const seconds = Math.floor(total % 60);

        if (minutes <= 0) {
            return `${seconds}s left`;
        }

        return `${minutes}m ${seconds
            .toString()
            .padStart(2, "0")}s left`;
    }

    function setMessage(
        text,
        error = false
    ) {
        const node = document.getElementById(
            "urlMessage"
        );

        if (!node) {
            return;
        }

        node.textContent = text;
        node.style.color = error
            ? "#ff6b6b"
            : "";
    }

    function showVideo(data) {
        document
            .getElementById("loaderView")
            ?.classList.add("is-hidden");

        document
            .getElementById("videoView")
            ?.classList.remove("is-hidden");

        const title = document.getElementById(
            "videoTitle"
        );
        const creator = document.getElementById(
            "videoCreator"
        );
        const duration = document.getElementById(
            "videoDuration"
        );
        const thumbnail = document.getElementById(
            "videoThumbnail"
        );
        const videoSelect = document.getElementById(
            "videoQualitySelect"
        );

        const audioSelect = document.getElementById(
            "audioQualitySelect"
        );
        const download = document.getElementById(
            "downloadButton"
        );

        if (title) {
            title.textContent =
                data.title ||
                data.fulltitle ||
                data.id ||
                "Untitled video";
        }

        if (creator) {
            creator.textContent =
                data.creator ||
                data.uploader ||
                data.channel ||
                "Unknown creator";
        }

        if (duration) {
            duration.textContent =
                data.duration ||
                "Unknown duration";
        }

        if (thumbnail) {
            thumbnail.src =
                data.thumbnail || "";
            thumbnail.alt =
                data.title ||
                "Video thumbnail";
        }if (videoSelect) {
            videoSelect.innerHTML = `
                <option value="">
                    Loading qualities...
                </option>
            `;
        }

        if (audioSelect) {
            audioSelect.innerHTML = `
                <option value="">
                    Loading audio...
                </option>
            `;
        }

        setDownloadControlsEnabled(false);

        document
            .getElementById("downloadProgress")
            ?.classList.add("is-hidden");

        setMessage(
            "Loading available qualities..."
        );
    }

    function setDownloadControlsEnabled(
        enabled
    ) {
        const download =
            document.getElementById(
                "downloadButton"
            );

        const audioOnly =
            document.getElementById(
                "audioOnlyButton"
            );

        const videoSelect =
            document.getElementById(
                "videoQualitySelect"
            );

        const audioSelect =
            document.getElementById(
                "audioQualitySelect"
            );

        if (download) {
            download.disabled =
                !enabled;
        }

        if (audioOnly) {
            audioOnly.disabled =
                !enabled;
        }

        if (videoSelect) {
            videoSelect.disabled =
                !enabled;
        }

        if (audioSelect) {
            audioSelect.disabled =
                !enabled;
        }
    }

    function renderFormats(data) {
        const videoSelect =
            document.getElementById(
                "videoQualitySelect"
            );

        const audioSelect =
            document.getElementById(
                "audioQualitySelect"
            );

        if (!videoSelect || !audioSelect) {
            return;
        }

        const videoFormats =
            Array.isArray(
                data?.video
            )
                ? data.video
                : [];

        const audioFormats =
            Array.isArray(
                data?.audio
            )
                ? data.audio
                : [];

        videoSelect.innerHTML = "";

        audioSelect.innerHTML = "";

        if (!videoFormats.length) {
            videoSelect.innerHTML = `
                <option value="">
                    No video qualities found
                </option>
            `;
        } else {
            videoFormats.forEach(
                (item) => {
                    const option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        item.format_id ||
                        "";

                    option.dataset.height =
                        item.height ?? "";

                    option.dataset.fallback =
                        item.fallback_selector ||
                        "";

                    option.textContent =
                        item.detail
                            ? `${item.label} • ${item.detail}`
                            : item.label ||
                              "Available quality";

                    videoSelect.appendChild(
                        option
                    );
                }
            );
        }

        if (!audioFormats.length) {
            audioSelect.innerHTML = `
                <option value="">
                    Original audio unavailable
                </option>
            `;
        } else {
            audioFormats.forEach(
                (item) => {
                    const option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        item.format_id ||
                        "";

                    option.textContent =
                        item.detail
                            ? `${item.label} • ${item.detail}`
                            : item.label ||
                              "Original audio";

                    if (
                        item.format_id ===
                        data.default_audio
                    ) {
                        option.selected =
                            true;
                    }

                    audioSelect.appendChild(
                        option
                    );
                }
            );

            if (
                data.default_audio &&
                audioSelect.querySelector(
                    `option[value="${CSS.escape(
                        data.default_audio
                    )}"]`
                )
            ) {
                audioSelect.value =
                    data.default_audio;
            } else if (
                audioSelect.options.length
            ) {
                audioSelect.selectedIndex =
                    0;
            }
        }

        if (
            videoSelect.options.length
        ) {
            videoSelect.selectedIndex =
                0;
        }

        setDownloadControlsEnabled(
            Boolean(
                videoSelect.value &&
                audioSelect.value
            )
        );

        if (
            data.has_explicit_original
        ) {
            setMessage(
                "Original audio detected. Choose your video and audio quality."
            );
        } else {
            setMessage(
                "Original audio is selected using yt-dlp's language preference. Choose your video and audio quality."
            );
        }
    }

    function resetDownloadProgress() {
        const progress = document.getElementById(
            "downloadProgress"
        );
        const bar = document.getElementById(
            "downloadProgressBar"
        );
        const percent = document.getElementById(
            "downloadProgressPercent"
        );
        const title = document.getElementById(
            "downloadProgressTitle"
        );
        const speed = document.getElementById(
            "downloadProgressSpeed"
        );
        const eta = document.getElementById(
            "downloadProgressEta"
        );
        const openFolder = document.getElementById(
            "openDownloadFolderButton"
        );

        progress?.classList.remove(
            "is-hidden"
        );

        if (bar) {
            bar.style.width = "0%";
        }

        if (percent) {
            percent.textContent = "0%";
        }

        if (title) {
            title.textContent =
                "Starting download";
        }

        if (speed) {
            speed.textContent = "Preparing";
        }

        if (eta) {
            eta.textContent = "";
        }

        openFolder?.classList.add(
            "is-hidden"
        );
    }

    function setupDownload() {
        const input =
            document.getElementById(
                "videoUrl"
            );

        const check =
            document.getElementById(
                "checkButton"
            );

        const videoSelect =
            document.getElementById(
                "videoQualitySelect"
            );

        const audioSelect =
            document.getElementById(
                "audioQualitySelect"
            );

        const download =
            document.getElementById(
                "downloadButton"
            );

        const audioOnly =
            document.getElementById(
                "audioOnlyButton"
            );

        const folder =
            document.getElementById(
                "chooseFolderButton"
            );

        const cancel =
            document.getElementById(
                "cancelDownloadButton"
            );

        const openFolder =
            document.getElementById(
                "openDownloadFolderButton"
            );

        check?.addEventListener(
            "click",
            () => {
                send({
                    type: "check-video",
                    url:
                        input?.value.trim() ||
                        "",
                });
            }
        );

        input?.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key ===
                    "Enter"
                ) {
                    check?.click();
                }
            }
        );

        const updateDownloadState =
            () => {
                const hasVideo =
                    Boolean(
                        videoSelect?.value
                    );

                const hasAudio =
                    Boolean(
                        audioSelect?.value
                    );

                setDownloadControlsEnabled(
                    hasVideo &&
                    hasAudio
                );

                if (audioOnly) {
                    audioOnly.disabled =
                        !hasAudio;
                }
            };

        videoSelect?.addEventListener(
            "change",
            updateDownloadState
        );

        audioSelect?.addEventListener(
            "change",
            updateDownloadState
        );

        folder?.addEventListener(
            "click",
            () => {
                send({
                    type:
                        "choose-download-folder",
                });
            }
        );

        download?.addEventListener(
            "click",
            () => {
                if (
                    !videoSelect?.value ||
                    !audioSelect?.value ||
                    !input?.value.trim()
                ) {
                    setMessage(
                        "Choose a video quality and an audio quality first.",
                        true
                    );
                    return;
                }

                resetDownloadProgress();

                send({
                    type:
                        "start-download",
                    url:
                        input.value.trim(),
                    videoSelector:
                        videoSelect.value,
                    audioSelector:
                        audioSelect.value,
                    mode:
                        "video",
                    outputDir:
                        folder?.dataset.path ||
                        "",
                });
            }
        );

        audioOnly?.addEventListener(
            "click",
            () => {
                if (
                    !audioSelect?.value ||
                    !input?.value.trim()
                ) {
                    setMessage(
                        "Choose an audio quality first.",
                        true
                    );
                    return;
                }

                resetDownloadProgress();

                send({
                    type:
                        "start-download",
                    url:
                        input.value.trim(),
                    videoSelector:
                        "",
                    audioSelector:
                        audioSelect.value,
                    mode:
                        "audio",
                    outputDir:
                        folder?.dataset.path ||
                        "",
                });
            }
        );

        cancel?.addEventListener(
            "click",
            () => {
                send({
                    type:
                        "cancel-download",
                });
            }
        );

        openFolder?.addEventListener(
            "click",
            () => {
                if (
                    openFolder.dataset.path
                ) {
                    send({
                        type:
                            "open-download-folder",
                        path:
                            openFolder.dataset.path,
                    });
                }
            }
        );

        send({
            type:
                "request-download-folder",
        });
    }

    function renderQueue() {
        const container = document.getElementById(
            "queueList"
        );

        if (!container) {
            return;
        }

        const queue = context.queue || [];

        if (!queue.length) {
            container.className =
                "list-panel empty-panel";
            container.innerHTML = `
                <div class="empty-title">
                    Your queue is empty
                </div>
                <div class="empty-subtitle">
                    Add a video from the Download page.
                </div>
            `;
            return;
        }

        container.className = "list-panel";
        container.innerHTML = queue
            .map(
                (item) => `
                    <div class="list-item">
                        <img
                            class="list-thumb"
                            src="${escapeAttribute(
                                item.thumbnail || ""
                            )}"
                            alt=""
                        >

                        <div class="list-content">
                            <div class="list-title">
                                ${escapeHtml(
                                    item.title
                                )}
                            </div>

                            <div class="list-meta">
                                ${escapeHtml(
                                    item.creator
                                )}
                                ${
                                    item.duration
                                        ? ` • ${escapeHtml(
                                              item.duration
                                          )}`
                                        : ""
                                }
                            </div>
                        </div>

                        <button
                            class="list-action"
                            data-remove-queue="${escapeAttribute(
                                item.id ||
                                    String(
                                        item.addedAt
                                    )
                            )}"
                        >
                            Remove
                        </button>
                    </div>
                `
            )
            .join("");

        container
            .querySelectorAll(
                "[data-remove-queue]"
            )
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        send({
                            type:
                                "remove-queue",
                            id:
                                button.dataset
                                    .removeQueue,
                        });
                    }
                );
            });
    }

    function renderHistory() {
        const container = document.getElementById(
            "historyList"
        );

        if (!container) {
            return;
        }

        const history = context.history || [];

        if (!history.length) {
            container.className =
                "list-panel empty-panel";
            container.innerHTML = `
                <div class="empty-title">
                    No history yet
                </div>
                <div class="empty-subtitle">
                    Checked videos will appear here.
                </div>
            `;
            return;
        }

        container.className = "list-panel";
        container.innerHTML = history
            .map(
                (item) => `
                    <div class="list-item">
                        <img
                            class="list-thumb"
                            src="${escapeAttribute(
                                item.thumbnail || ""
                            )}"
                            alt=""
                        >

                        <div class="list-content">
                            <div class="list-title">
                                ${escapeHtml(
                                    item.title
                                )}
                            </div>

                            <div class="list-meta">
                                ${escapeHtml(
                                    item.creator
                                )}
                                ${
                                    item.duration
                                        ? ` • ${escapeHtml(
                                              item.duration
                                          )}`
                                        : ""
                                }
                                ${
                                    item.addedAt
                                        ? ` • ${escapeHtml(
                                              formatDate(
                                                  item.addedAt
                                              )
                                          )}`
                                        : ""
                                }
                            </div>
                        </div>

                        <button
                            class="list-action"
                            data-remove-history="${escapeAttribute(
                                item.id ||
                                    String(
                                        item.addedAt
                                    )
                            )}"
                        >
                            Remove
                        </button>
                    </div>
                `
            )
            .join("");

        container
            .querySelectorAll(
                "[data-remove-history]"
            )
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        send({
                            type:
                                "remove-history",
                            id:
                                button.dataset
                                    .removeHistory,
                        });
                    }
                );
            });
    }

    function renderHome() {
        const history = context.history || [];

        const count = document.getElementById(
            "homeDownloadCount"
        );
        const queue = document.getElementById(
            "homeQueueCount"
        );
        const last = document.getElementById(
            "homeLastActivity"
        );
        const recent = document.getElementById(
            "homeRecent"
        );

        if (count) {
            count.textContent = history.length;
        }

        if (queue) {
            queue.textContent = (
                context.queue || []
            ).length;
        }

        if (last) {
            last.textContent = history[0]
                ? formatDate(history[0].addedAt)
                : "Nothing yet";
        }

        if (!recent) {
            return;
        }

        if (!history.length) {
            recent.className =
                "list-panel empty-panel";
            recent.innerHTML = `
                <div class="empty-title">
                    No activity yet
                </div>
                <div class="empty-subtitle">
                    Checked videos will appear here.
                </div>
            `;
            return;
        }

        recent.className = "list-panel";
        recent.innerHTML = history
            .slice(0, 5)
            .map(
                (item) => `
                    <div class="list-item">
                        <img
                            class="list-thumb"
                            src="${escapeAttribute(
                                item.thumbnail || ""
                            )}"
                            alt=""
                        >
                        <div class="list-content">
                            <div class="list-title">
                                ${escapeHtml(
                                    item.title
                                )}
                            </div>

                            <div class="list-meta">
                                ${escapeHtml(
                                    item.creator
                                )}
                            </div>
                        </div>

                        ${
                            item.webpage_url
                                ? `
                                    <button
                                        class="list-action"
                                        type="button"
                                        data-open-video="${escapeAttribute(
                                            item.webpage_url
                                        )}"
                                    >
                                        Open video
                                    </button>
                                `
                                : ""
                        }
                    </div>
                `
            )
            .join("");

        recent
            .querySelectorAll(
                "[data-open-video]"
            )
            .forEach(
                (button) => {
                    button.addEventListener(
                        "click",
                        () => {
                            send({
                                type:
                                    "open-video",
                                url:
                                    button
                                        .dataset
                                        .openVideo,
                            });
                        }
                    );
                }
            );
    }

    function statusLabel(status) {
        const labels = {
            up_to_date: "Up to date",
            update_available:
                "Update available",
            not_installed:
                "Not installed",
            unavailable: "Unavailable",
            unknown: "Unknown",
            newer_installed:
                "Newer installed",
        };

        return (
            labels[status] ||
            "Unknown"
        );
    }

    function statusClass(status) {
        if (status === "up_to_date") {
            return "update-status-ok";
        }

        if (status === "update_available") {
            return "update-status-update";
        }

        if (status === "not_installed") {
            return "update-status-missing";
        }

        return "update-status-muted";
    }

    function renderUpdates(results) {
        const container = document.getElementById(
            "updateResults"
        );

        if (!container) {
            return;
        }

        if (
            !Array.isArray(results) ||
            !results.length
        ) {
            container.innerHTML = `
                <div class="update-empty">
                    No update information was returned.
                </div>
            `;
            return;
        }

        container.innerHTML = results
            .map((item) => {
                const bundled =
                    item.component_type ===
                        "python-package" &&
                    item.status ===
                        "update_available" &&
                    !item.can_update;

                const status = bundled
                    ? "Included in app update"
                    : statusLabel(
                          item.status
                      );

                const action =
                    item.can_update &&
                    item.update_id
                        ? `
                            <button
                                class="update-action"
                                data-update-component="${escapeAttribute(
                                    item.update_id
                                )}"
                            >
                                Update
                            </button>
                        `
                        : "";

                return `
                    <div class="update-row">
                        <div class="update-component">
                            <div class="update-name">
                                ${escapeHtml(
                                    item.name
                                )}
                            </div>
                            <div class="update-source">
                                ${escapeHtml(
                                    item.source || ""
                                )}
                            </div>
                        </div>

                        <div class="update-version">
                            ${escapeHtml(
                                item.current ||
                                    "Not installed"
                            )}
                            <span class="update-arrow">→</span>
                            ${escapeHtml(
                                item.latest ||
                                    "Unavailable"
                            )}
                        </div>

                        <div class="update-status ${
                            bundled
                                ? "update-status-update"
                                : statusClass(
                                      item.status
                                  )
                        }">
                            ${escapeHtml(status)}
                        </div>

                        ${action}
                    </div>
                `;
            })
            .join("");

        container
            .querySelectorAll(
                "[data-update-component]"
            )
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        button.disabled = true;
                        button.textContent =
                            "Updating...";

                        send({
                            type:
                                "update-component",
                            id:
                                button.dataset
                                    .updateComponent,
                        });
                    }
                );
            });
    }

    function setupUpdates() {
        const request = () => {
            send({
                type:
                    "check-updates",
            });
        };

        document
            .getElementById(
                "checkUpdatesButton"
            )
            ?.addEventListener(
                "click",
                request
            );

        document
            .getElementById(
                "refreshUpdatesButton"
            )
            ?.addEventListener(
                "click",
                request
            );
    }

    function setupUpdatesInfo() {
        const modal = document.getElementById(
            "updatesInfoModal"
        );
        const open = document.getElementById(
            "updatesInfoButton"
        );
        const close = document.getElementById(
            "closeUpdatesInfo"
        );

        if (!modal || !open) {
            return;
        }

        const show = () => {
            modal.classList.remove(
                "is-hidden"
            );
            modal.setAttribute(
                "aria-hidden",
                "false"
            );
            close?.focus();
        };

        const hide = () => {
            if (modal.contains(document.activeElement)) {
                open.focus();
            }

            modal.classList.add(
                "is-hidden"
            );
            modal.setAttribute(
                "aria-hidden",
                "true"
            );
        };

        open.addEventListener("click", show);
        close?.addEventListener("click", hide);

        modal
            .querySelectorAll(
                "[data-close-updates-info]"
            )
            .forEach((item) => {
                item.addEventListener(
                    "click",
                    hide
                );
            });

        document.addEventListener(
            "keydown",
            (event) => {
                if (
                    event.key === "Escape" &&
                    !modal.classList.contains(
                        "is-hidden"
                    )
                ) {
                    hide();
                }
            }
        );
    }

    function setupDataButtons() {
        document
            .getElementById(
                "clearQueueButton"
            )
            ?.addEventListener(
                "click",
                () => {
                    send({
                        type: "clear-queue",
                    });
                }
            );

        document
            .getElementById(
                "clearHistoryButton"
            )
            ?.addEventListener(
                "click",
                () => {
                    send({
                        type: "clear-history",
                    });
                }
            );

        document
            .getElementById(
                "clearAllDataButton"
            )
            ?.addEventListener(
                "click",
                () => {
                    send({
                        type: "clear-queue",
                    });
                    send({
                        type: "clear-history",
                    });
                }
            );
    }

    function initPage() {
        enablePageScrolling();
        setCurrentYear();
        setupExternalLinks();

        const page = document.querySelector(
            ".page"
        )?.dataset.view;

        if (page === "home") {
            renderHome();
        }

        if (page === "download") {
            setupDownload();
        }

        if (page === "queue") {
            renderQueue();
        }

        if (page === "history") {
            renderHistory();
        }

        if (page === "settings") {
            setupDataButtons();
            setupUpdates();
            setupUpdatesInfo();
        }

        document
            .querySelectorAll(
                "[data-go-to]"
            )
            .forEach((button) => {
                button.addEventListener(
                    "click",
                    () => {
                        send({
                            type:
                                "navigate",
                            page:
                                button.dataset
                                    .goTo,
                        });
                    }
                );
            });

        send({
            type: "page-ready",
            page,
        });
    }

    window.addEventListener(
        "message",
        (event) => {
            if (
                !event.data ||
                typeof event.data !== "object"
            ) {
                return;
            }

            const message = event.data;

            if (
                message.type ===
                "page-context"
            ) {
                context = {
                    history:
                        Array.isArray(
                            message.history
                        )
                            ? message.history
                            : [],
                    queue:
                        Array.isArray(
                            message.queue
                        )
                            ? message.queue
                            : [],
                };

                renderHome();
                renderQueue();
                renderHistory();
                return;
            }

            if (
                message.type ===
                "video-loading"
            ) {
                document
                    .getElementById(
                        "videoView"
                    )
                    ?.classList.add(
                        "is-hidden"
                    );

                document
                    .getElementById(
                        "loaderView"
                    )
                    ?.classList.remove(
                        "is-hidden"
                    );

                setMessage(
                    "Fetching video information..."
                );
                return;
            }

            if (
                message.type ===
                "video-loaded"
            ) {
                showVideo(
                    message.data || {}
                );
                return;
            }

            if (
                message.type ===
                "video-error"
            ) {
                document
                    .getElementById(
                        "loaderView"
                    )
                    ?.classList.add(
                        "is-hidden"
                    );

                setMessage(
                    message.message ||
                        "Unable to load video.",
                    true
                );
                return;
            }

            if (
                message.type ===
                "formats-loading"
            ) {
                const videoSelect =
                    document.getElementById(
                        "videoQualitySelect"
                    );

                const audioSelect =
                    document.getElementById(
                        "audioQualitySelect"
                    );

                if (videoSelect) {
                    videoSelect.innerHTML = `
                        <option value="">
                            Loading qualities...
                        </option>
                    `;
                }

                if (audioSelect) {
                    audioSelect.innerHTML = `
                        <option value="">
                            Loading audio...
                        </option>
                    `;
                }

                return;
            }

            if (
                message.type ===
                "formats-ready"
            ) {
                renderFormats(
                    message.data || {}
                );
                return;
            }

            if (
                message.type ===
                "formats-error"
            ) {
                renderFormats({});
                setMessage(
                    message.message ||
                        "Unable to load formats.",
                    true
                );
                return;
            }

            if (
                message.type ===
                "download-starting"
            ) {
                resetDownloadProgress();

                document
                    .getElementById(
                        "downloadButton"
                    )
                    ?.setAttribute(
                        "disabled",
                        "disabled"
                    );

                document
                    .getElementById(
                        "checkButton"
                    )
                    ?.setAttribute(
                        "disabled",
                        "disabled"
                    );
                return;
            }

            if (
                message.type ===
                "download-progress"
            ) {
                const data =
                    message.data || {};

                const bar =
                    document.getElementById(
                        "downloadProgressBar"
                    );
                const percent =
                    document.getElementById(
                        "downloadProgressPercent"
                    );
                const title =
                    document.getElementById(
                        "downloadProgressTitle"
                    );
                const speed =
                    document.getElementById(
                        "downloadProgressSpeed"
                    );
                const eta =
                    document.getElementById(
                        "downloadProgressEta"
                    );

                const progress = Math.max(
                    0,
                    Math.min(
                        100,
                        Number(
                            data.percent || 0
                        )
                    )
                );

                if (bar) {
                    bar.style.width =
                        `${progress}%`;
                }

                if (percent) {
                    percent.textContent =
                        `${Math.round(
                            progress
                        )}%`;
                }

                if (
                    data.status ===
                    "processing"
                ) {
                    if (title) {
                        title.textContent =
                            "Finishing download";
                    }
                    if (speed) {
                        speed.textContent =
                            "Processing media";
                    }
                    if (eta) {
                        eta.textContent = "";
                    }
                } else if (
                    data.status ===
                    "starting"
                ) {
                    if (title) {
                        title.textContent =
                            "Starting download";
                    }
                    if (speed) {
                        speed.textContent =
                            "Preparing";
                    }
                } else {
                    if (title) {
                        title.textContent =
                            "Downloading";
                    }
                    if (speed) {
                        speed.textContent =
                            formatSpeed(
                                data.speed
                            ) ||
                            "Downloading";
                    }
                    if (eta) {
                        eta.textContent =
                            formatEta(
                                data.eta
                            );
                    }
                }
                return;
            }

            if (
                message.type ===
                "download-finished"
            ) {
                const data =
                    message.data || {};

                const title =
                    document.getElementById(
                        "downloadProgressTitle"
                    );
                const percent =
                    document.getElementById(
                        "downloadProgressPercent"
                    );
                const bar =
                    document.getElementById(
                        "downloadProgressBar"
                    );
                const speed =
                    document.getElementById(
                        "downloadProgressSpeed"
                    );
                const eta =
                    document.getElementById(
                        "downloadProgressEta"
                    );
                const openFolder =
                    document.getElementById(
                        "openDownloadFolderButton"
                    );

                if (title) {
                    title.textContent =
                        "Download complete";
                }
                if (percent) {
                    percent.textContent =
                        "100%";
                }
                if (bar) {
                    bar.style.width =
                        "100%";
                }
                if (speed) {
                    speed.textContent =
                        "Saved successfully";
                }
                if (eta) {
                    eta.textContent =
                        data.path || "";
                }
                if (openFolder) {
                    openFolder.dataset.path =
                        data.path || "";
                    openFolder.classList.remove(
                        "is-hidden"
                    );
                }

                document
                    .getElementById(
                        "checkButton"
                    )
                    ?.removeAttribute(
                        "disabled"
                    );

                document
                    .getElementById(
                        "downloadButton"
                    )
                    ?.removeAttribute(
                        "disabled"
                    );

                document
                    .getElementById(
                        "audioOnlyButton"
                    )
                    ?.removeAttribute(
                        "disabled"
                    );

                setMessage(
                    "Download complete."
                );
                return;
            }

            if (
                message.type ===
                "download-error"
            ) {
                const title =
                    document.getElementById(
                        "downloadProgressTitle"
                    );

                if (title) {
                    title.textContent =
                        "Download failed";
                }

                const download =
                    document.getElementById(
                        "downloadButton"
                    );

                if (download) {
                    download.disabled = false;
                }

                document
                    .getElementById(
                        "checkButton"
                    )
                    ?.removeAttribute(
                        "disabled"
                    );

                setMessage(
                    message.message ||
                        "Download failed.",
                    true
                );
                return;
            }

            if (
                message.type ===
                "download-cancelled"
            ) {
                const title =
                    document.getElementById(
                        "downloadProgressTitle"
                    );

                if (title) {
                    title.textContent =
                        "Download cancelled";
                }

                const download =
                    document.getElementById(
                        "downloadButton"
                    );

                if (download) {
                    download.disabled = false;
                }

                document
                    .getElementById(
                        "checkButton"
                    )
                    ?.removeAttribute(
                        "disabled"
                    );

                setMessage(
                    "Download cancelled."
                );
                return;
            }

            if (
                message.type ===
                "download-folder"
            ) {
                const button =
                    document.getElementById(
                        "chooseFolderButton"
                    );
                const label =
                    document.getElementById(
                        "downloadFolder"
                    );

                if (button) {
                    button.dataset.path =
                        message.path || "";
                }

                if (label) {
                    label.textContent =
                        message.path ||
                        "Downloads";
                }
                return;
            }

            if (
                message.type ===
                "updates-loading"
            ) {
                const button =
                    document.getElementById(
                        "checkUpdatesButton"
                    );

                const note =
                    document.getElementById(
                        "updateCheckTime"
                    );

                if (button) {
                    button.disabled = true;
                    button.textContent =
                        "Checking...";
                }

                if (note) {
                    note.textContent =
                        "Checking for updates...";
                }
                return;
            }

            if (
                message.type ===
                "updates-ready"
            ) {
                const button =
                    document.getElementById(
                        "checkUpdatesButton"
                    );

                const note =
                    document.getElementById(
                        "updateCheckTime"
                    );

                if (button) {
                    button.disabled = false;
                    button.textContent =
                        "Check for updates";
                }

                if (note) {
                    note.textContent =
                        `Last checked ${formatDate(
                            Date.now()
                        )}`;
                }

                renderUpdates(
                    message.data || []
                );
                return;
            }

            if (
                message.type ===
                "updates-error"
            ) {
                const button =
                    document.getElementById(
                        "checkUpdatesButton"
                    );

                const note =
                    document.getElementById(
                        "updateCheckTime"
                    );

                if (button) {
                    button.disabled = false;
                    button.textContent =
                        "Check for updates";
                }

                if (note) {
                    note.textContent =
                        "Update check failed";
                }

                const container =
                    document.getElementById(
                        "updateResults"
                    );

                if (container) {
                    container.innerHTML = `
                        <div class="update-empty update-error">
                            ${escapeHtml(
                                message.message ||
                                    "Unable to check for updates."
                            )}
                        </div>
                    `;
                }
                return;
            }

            if (
                message.type ===
                "component-update-loading"
            ) {
                return;
            }

            if (
                message.type ===
                "component-update-ready"
            ) {
                const result =
                    message.data || {};

                const note =
                    document.getElementById(
                        "updateCheckTime"
                    );

                if (note) {
                    note.textContent =
                        `${result.name || "Component"} updated to ${result.version || "latest"}.`;
                }

                send({
                    type:
                        "check-updates",
                });
                return;
            }

            if (
                message.type ===
                "component-update-error"
            ) {
                const note =
                    document.getElementById(
                        "updateCheckTime"
                    );

                if (note) {
                    note.textContent =
                        "Component update failed";
                }
                return;
            }

            if (
                message.type ===
                "application-update-loading"
            ) {
                const note =
                    document.getElementById(
                        "updateCheckTime"
                    );

                if (note) {
                    note.textContent =
                        "Preparing YouLoad update...";
                }
                return;
            }

            if (
                message.type ===
                "application-update-ready"
            ) {
                const note =
                    document.getElementById(
                        "updateCheckTime"
                    );

                if (note) {
                    note.textContent =
                        message.data?.message ||
                        "Update downloaded.";
                }
            }
        }
    );

    document.addEventListener(
        "DOMContentLoaded",
        initPage
    );
})();
