(() => {
    const pages = [
        "home",
        "download",
        "queue",
        "history",
        "settings",
        "about",
        "disclaimer",
        "social",
    ];

    let bridgeReady = false;
    let youLoadBridge = null;
    let currentVideo = null;
    let startupFinished = false;
    let startupUpdateCheckFinished = false;
    let notifications = [];

    const loadingMessages = [];
    let loadingMessageIndex = -1;

    function setLoadingMessage(message) {
        const element = document.getElementById("loadingMessage");

        if (!element || !message) {
            return;
        }

        element.classList.add("is-changing");

        window.setTimeout(() => {
            element.textContent = message;
            element.classList.remove("is-changing");
        }, 220);
    }

    function showNextLoadingMessage() {
        if (!loadingMessages.length) {
            return;
        }

        if (loadingMessages.length === 1) {
            loadingMessageIndex = 0;
        } else {
            let next = Math.floor(Math.random() * loadingMessages.length);

            while (next === loadingMessageIndex) {
                next = Math.floor(Math.random() * loadingMessages.length);
            }

            loadingMessageIndex = next;
        }

        setLoadingMessage(loadingMessages[loadingMessageIndex]);
    }

    function loadLoadingMessages() {
        fetch("assets/messages.json", { cache: "no-store" })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Could not load loading messages.");
                }

                return response.json();
            })
            .then((data) => {
                if (Array.isArray(data?.messages)) {
                    data.messages
                        .filter((message) => typeof message === "string" && message.trim())
                        .forEach((message) => loadingMessages.push(message.trim()));
                }

                showNextLoadingMessage();

                window.setInterval(showNextLoadingMessage, 4500);
            })
            .catch(() => {
                setLoadingMessage("Tip: Choose video and audio quality separately before downloading.");
            });
    }

    function setLoadingStatus(message) {
        const element = document.querySelector(".loading-status-text");

        if (element) {
            element.textContent = message;
        }
    }

    function renderNotifications() {
        const panel = document.getElementById("notificationPanel");
        const list = document.getElementById("notificationList");
        const badge = document.getElementById("notificationBadge");

        if (!panel || !list) {
            return;
        }

        list.innerHTML = notifications.length
            ? notifications
                .map(
                    (notification) => `
                    <article class="notification-item">
                        <span class="notification-dot" aria-hidden="true"></span>
                        <div>
                            <strong>Update available</strong>
                            <p>${notification.name} has a newer version ready.</p>
                        </div>
                    </article>
                `
                )
                .join("")
            : `<div class="notification-empty">You are all caught up.</div>`;

        if (badge) {
            badge.textContent = String(notifications.length);
            badge.classList.toggle("is-hidden", notifications.length === 0);
        }

        panel.classList.toggle("is-hidden", notifications.length === 0);
        document
            .getElementById("notificationToggle")
            ?.setAttribute("aria-expanded", String(notifications.length > 0));
    }

    function toggleNotifications(forceOpen) {
        const panel = document.getElementById("notificationPanel");
        const toggle = document.getElementById("notificationToggle");

        if (!panel || !toggle) {
            return;
        }

        const shouldOpen = forceOpen ?? panel.classList.contains("is-hidden");

        panel.classList.toggle("is-hidden", !shouldOpen);
        toggle.setAttribute("aria-expanded", String(shouldOpen));
    }

    function finishStartup() {
        if (startupFinished || !startupUpdateCheckFinished) {
            return;
        }

        startupFinished = true;
        document.getElementById("loadingScreen")?.classList.add("is-hidden");
        document.getElementById("appShell")?.classList.remove("is-hidden");
        document.getElementById("notificationToggle")?.classList.remove("is-hidden");
        openPage("home");
    }

    function handleStartupUpdates(results) {
        notifications = (Array.isArray(results) ? results : [])
            .filter((item) => item?.status === "update_available")
            .filter((item) => ["FFmpeg", "yt-dlp", "YouLoad"].includes(item.name))
            .map((item) => ({ name: item.name }));

        renderNotifications();
        startupUpdateCheckFinished = true;
        setLoadingStatus("Ready");
        finishStartup();
    }

    function handleStartupUpdateError() {
        startupUpdateCheckFinished = true;
        setLoadingStatus("Ready");
        finishStartup();
    }

    let userData = {
        history: [],
        queue: [],
    };

    const frame = () =>
        document.getElementById(
            "pageFrame"
        );

    function loadStored(key) {
        if (
            key ===
            "youload.history"
        ) {
            return Array.isArray(
                userData.history
            )
                ? userData.history
                : [];
        }

        if (
            key ===
            "youload.queue"
        ) {
            return Array.isArray(
                userData.queue
            )
                ? userData.queue
                : [];
        }

        return [];
    }

    function saveStored(
        key,
        value
    ) {
        if (
            key ===
            "youload.history"
        ) {
            userData.history =
                Array.isArray(value)
                    ? value
                    : [];
        }

        if (
            key ===
            "youload.queue"
        ) {
            userData.queue =
                Array.isArray(value)
                    ? value
                    : [];
        }

        persistUserData();
    }

    function persistUserData() {
        if (
            !bridgeReady ||
            !youLoadBridge ||
            typeof youLoadBridge.saveUserData !==
                "function"
        ) {
            return;
        }

        youLoadBridge.saveUserData(
            JSON.stringify(
                userData.history
            ),
            JSON.stringify(
                userData.queue
            )
        );
    }

    function postToPage(message) {
        const target = frame();

        if (
            target &&
            target.contentWindow
        ) {
            target.contentWindow.postMessage(
                message,
                "*"
            );
        }
    }

    function postContext() {
        postToPage({
            type:
                "page-context",

            history:
                loadStored(
                    "youload.history"
                ),

            queue:
                loadStored(
                    "youload.queue"
                ),
        });
    }

    function setActivePage(
        page
    ) {
        document
            .querySelectorAll(
                ".nav-item[data-page]"
            )
            .forEach(
                (button) => {
                    button.classList.toggle(
                        "active",
                        button.dataset.page ===
                            page
                    );
                }
            );
    }

    function openPage(page) {
        if (
            !pages.includes(page)
        ) {
            return;
        }

        setActivePage(page);

        const target = frame();

        if (target) {
            target.src =
                `pages/${page}.html`;
        }
    }

    function setupNavigation() {
        document
            .querySelectorAll(
                ".nav-item[data-page]"
            )
            .forEach(
                (button) => {
                    button.addEventListener(
                        "click",
                        () => {
                            openPage(
                                button.dataset
                                    .page
                            );
                        }
                    );
                }
            );
    }

    function setupFrame() {
        const target = frame();

        if (!target) {
            return;
        }

        target.addEventListener(
            "load",
            () => {
                postContext();
            }
        );
    }

    function setupBridge() {
        if (
            typeof qt ===
                "undefined" ||
            !qt.webChannelTransport ||
            typeof QWebChannel ===
                "undefined"
        ) {
            handleStartupUpdateError();
            return;
        }

        new QWebChannel(
            qt.webChannelTransport,
            (channel) => {
                youLoadBridge =
                    channel.objects.youLoad;

                bridgeReady =
                    Boolean(
                        youLoadBridge
                    );

                if (
                    bridgeReady &&
                    typeof youLoadBridge.getUserData ===
                        "function"
                ) {
                    youLoadBridge.getUserData();
                }

                if (
                    bridgeReady &&
                    typeof youLoadBridge.checkForUpdates === "function"
                ) {
                    setLoadingStatus("Checking for updates");
                    youLoadBridge.checkForUpdates();
                } else {
                    handleStartupUpdateError();
                }
            }
        );
    }

    function openExternalVideo(
        url
    ) {
        const value =
            String(
                url || ""
            ).trim();

        if (
            !value ||
            !bridgeReady ||
            !youLoadBridge ||
            typeof youLoadBridge.openExternalUrl !==
                "function"
        ) {
            return;
        }

        youLoadBridge.openExternalUrl(
            value
        );
    }

    function checkVideo(url) {
        const value =
            String(
                url || ""
            ).trim();

        if (!value) {
            postToPage({
                type:
                    "video-error",
                message:
                    "Paste a YouTube URL first.",
            });

            return;
        }

        if (
            !/^https?:\/\/(www\.)?(youtube\.com|youtu\.be)\//i.test(
                value
            )
        ) {
            postToPage({
                type:
                    "video-error",
                message:
                    "Please enter a valid YouTube URL.",
            });

            return;
        }

        if (
            !bridgeReady ||
            !youLoadBridge
        ) {
            postToPage({
                type:
                    "video-error",
                message:
                    "YouLoad is still starting. Try again in a moment.",
            });

            return;
        }

        postToPage({
            type:
                "video-loading",
        });

        youLoadBridge.loadVideo(
            value
        );
    }

    function getVideoFormats(
        url
    ) {
        const value =
            String(
                url || ""
            ).trim();

        if (
            !bridgeReady ||
            !youLoadBridge ||
            !value
        ) {
            postToPage({
                type:
                    "formats-error",
                message:
                    "The video engine is not ready.",
            });

            return;
        }

        postToPage({
            type:
                "formats-loading",
        });

        if (
            typeof youLoadBridge.getVideoFormats !==
            "function"
        ) {
            postToPage({
                type:
                    "formats-error",
                message:
                    "Format lookup is not available in this build.",
            });

            return;
        }

        youLoadBridge.getVideoFormats(
            value
        );
    }

    function startDownload(
        url,
        videoSelector,
        audioSelector,
        mode,
        outputDir
    ) {
        if (
            !bridgeReady ||
            !youLoadBridge
        ) {
            postToPage({
                type:
                    "download-error",
                message:
                    "The download engine is not ready.",
            });

            return;
        }

        if (
            typeof youLoadBridge.startDownload !==
            "function"
        ) {
            postToPage({
                type:
                    "download-error",
                message:
                    "Download support is not available in this build.",
            });

            return;
        }

        postToPage({
            type:
                "download-starting",
        });

        youLoadBridge.startDownload(
            String(
                url || ""
            ),
            String(
                videoSelector || ""
            ),
            String(
                audioSelector || ""
            ),
            mode || "video",
            String(
                outputDir || ""
            )
        );
    }

    function cancelDownload() {
        if (
            bridgeReady &&
            youLoadBridge &&
            typeof youLoadBridge.cancelDownload ===
                "function"
        ) {
            youLoadBridge.cancelDownload();
        }
    }

    function chooseDownloadFolder() {
        if (
            bridgeReady &&
            youLoadBridge &&
            typeof youLoadBridge.chooseDownloadFolder ===
                "function"
        ) {
            youLoadBridge.chooseDownloadFolder();
        }
    }

    function getDownloadFolder() {
        if (
            bridgeReady &&
            youLoadBridge &&
            typeof youLoadBridge.getDownloadFolder ===
                "function"
        ) {
            youLoadBridge.getDownloadFolder();
        }
    }

    function openDownloadFolder(
        path
    ) {
        if (
            bridgeReady &&
            youLoadBridge &&
            path &&
            typeof youLoadBridge.openDownloadFolder ===
                "function"
        ) {
            youLoadBridge.openDownloadFolder(
                path
            );
        }
    }

    function checkForUpdates() {
        if (
            !bridgeReady ||
            !youLoadBridge
        ) {
            postToPage({
                type:
                    "updates-error",
                message:
                    "YouLoad is still starting. Try again in a moment.",
            });

            return;
        }

        if (
            typeof youLoadBridge.checkForUpdates !==
            "function"
        ) {
            postToPage({
                type:
                    "updates-error",
                message:
                    "Update support is not available in this build.",
            });

            return;
        }

        postToPage({
            type:
                "updates-loading",
        });

        youLoadBridge.checkForUpdates();
    }

    function updateComponent(
        id
    ) {
        if (
            !bridgeReady ||
            !youLoadBridge ||
            !id
        ) {
            return;
        }

        if (
            typeof youLoadBridge.updateComponent !==
            "function"
        ) {
            postToPage({
                type:
                    "component-update-error",
                message:
                    "Component updating is not available in this build.",
            });

            return;
        }

        postToPage({
            type:
                "component-update-loading",

            id,
        });

        youLoadBridge.updateComponent(
            id
        );
    }

    function updateApplication() {
        if (
            !bridgeReady ||
            !youLoadBridge
        ) {
            return;
        }

        if (
            typeof youLoadBridge.updateApplication !==
            "function"
        ) {
            postToPage({
                type:
                    "application-update-error",
                message:
                    "Application updating is not available in this build.",
            });

            return;
        }

        postToPage({
            type:
                "application-update-loading",
        });

        youLoadBridge.updateApplication();
    }

    function sanitizeText(
        value,
        fallback
    ) {
        return String(
            value || fallback
        )
            .replace(
                /[\u200B\u2060\uFEFF]/g,
                ""
            )
            .trim() ||
            fallback;
    }

    function showVideo(
        data
    ) {
        const title =
            sanitizeText(
                data?.title ||
                    data?.fulltitle ||
                    data?.id,
                "Untitled video"
            );

        const creator =
            sanitizeText(
                data?.creator ||
                    data?.uploader ||
                    data?.channel,
                "Unknown creator"
            );

        currentVideo = {
            ...data,
            title,
            creator,
            loadedAt:
                Date.now(),
        };

        addToHistory(
            currentVideo
        );

        postToPage({
            type:
                "video-loaded",

            data:
                currentVideo,

            history:
                loadStored(
                    "youload.history"
                ),

            queue:
                loadStored(
                    "youload.queue"
                ),
        });
    }

    function addToHistory(
        video
    ) {
        const history =
            loadStored(
                "youload.history"
            );

        const item = {
            title:
                video.title ||
                "Untitled video",

            creator:
                video.creator ||
                "Unknown creator",

            duration:
                video.duration ||
                "",

            thumbnail:
                video.thumbnail ||
                "",

            webpage_url:
                video.webpage_url ||
                "",

            id:
                video.id ||
                "",

            addedAt:
                video.loadedAt ||
                Date.now(),
        };

        const filtered =
            history.filter(
                (entry) =>
                    !(
                        item.id &&
                        entry.id ===
                            item.id
                    )
            );

        filtered.unshift(
            item
        );

        saveStored(
            "youload.history",
            filtered.slice(
                0,
                50
            )
        );
    }

    function addToQueue(
        video
    ) {
        const queue =
            loadStored(
                "youload.queue"
            );

        if (
            video.id &&
            queue.some(
                (entry) =>
                    entry.id ===
                    video.id
            )
        ) {
            return;
        }

        queue.push({
            title:
                video.title ||
                "Untitled video",

            creator:
                video.creator ||
                "Unknown creator",

            duration:
                video.duration ||
                "",

            thumbnail:
                video.thumbnail ||
                "",

            webpage_url:
                video.webpage_url ||
                "",

            id:
                video.id ||
                "",

            addedAt:
                Date.now(),
        });

        saveStored(
            "youload.queue",
            queue
        );
    }

    function removeQueueItem(
        id
    ) {
        const queue =
            loadStored(
                "youload.queue"
            ).filter(
                (entry) =>
                    String(
                        entry.id ||
                            entry.addedAt
                    ) !==
                    String(id)
            );

        saveStored(
            "youload.queue",
            queue
        );

        postContext();
    }

    function removeHistoryItem(
        id
    ) {
        const history =
            loadStored(
                "youload.history"
            ).filter(
                (entry) =>
                    String(
                        entry.id ||
                            entry.addedAt
                    ) !==
                    String(id)
            );

        saveStored(
            "youload.history",
            history
        );

        postContext();
    }

    window.YouLoad = {
        onUserDataReady:
            (data) => {
                userData = {
                    history:
                        Array.isArray(
                            data?.history
                        )
                            ? data.history
                            : [],

                    queue:
                        Array.isArray(
                            data?.queue
                        )
                            ? data.queue
                            : [],
                };

                postContext();
            },

        onVideoLoaded:
            (data) => {
                showVideo(
                    data || {}
                );

                const url =
                    data?.webpage_url ||
                    data?.original_url ||
                    "";

                if (url) {
                    getVideoFormats(
                        url
                    );
                }
            },

        onVideoError:
            (message) => {
                postToPage({
                    type:
                        "video-error",
                    message:
                        message ||
                        "Unable to load video.",
                });
            },

        onFormatsReady:
            (data) => {
                postToPage({
                    type:
                        "formats-ready",
                    data:
                        data || {},
                });
            },

        onFormatsError:
            (message) => {
                postToPage({
                    type:
                        "formats-error",
                    message:
                        message ||
                        "Unable to load formats.",
                });
            },

        onDownloadProgress:
            (data) => {
                postToPage({
                    type:
                        "download-progress",
                    data:
                        data || {},
                });
            },

        onDownloadFinished:
            (data) => {
                postToPage({
                    type:
                        "download-finished",
                    data:
                        data || {},
                });
            },

        onDownloadError:
            (message) => {
                postToPage({
                    type:
                        "download-error",
                    message:
                        message ||
                        "Download failed.",
                });
            },

        onDownloadCancelled:
            () => {
                postToPage({
                    type:
                        "download-cancelled",
                });
            },

        onDownloadFolder:
            (path) => {
                postToPage({
                    type:
                        "download-folder",
                    path:
                        path ||
                        "Downloads",
                });
            },

        onUpdatesReady:
            (data) => {
                handleStartupUpdates(data);
                postToPage({
                    type:
                        "updates-ready",
                    data:
                        Array.isArray(
                            data
                        )
                            ? data
                            : [],
                });
            },

        onUpdatesError:
            (message) => {
                handleStartupUpdateError();
                postToPage({
                    type:
                        "updates-error",
                    message:
                        message ||
                        "Unable to check for updates.",
                });
            },

        onComponentUpdateReady:
            (result) => {
                postToPage({
                    type:
                        "component-update-ready",
                    data:
                        result || {},
                });

                window.setTimeout(
                    checkForUpdates,
                    400
                );
            },

        onComponentUpdateError:
            (message) => {
                postToPage({
                    type:
                        "component-update-error",
                    message:
                        message ||
                        "Component update failed.",
                });
            },

        onApplicationUpdateReady:
            (result) => {
                postToPage({
                    type:
                        "application-update-ready",
                    data:
                        result || {},
                });
            },

        onApplicationUpdateError:
            (message) => {
                postToPage({
                    type:
                        "application-update-error",
                    message:
                        message ||
                        "Application update failed.",
                });
            },
    };

    window.addEventListener(
        "message",
        (event) => {
            const message =
                event.data;

            if (
                !message ||
                typeof message !==
                    "object"
            ) {
                return;
            }

            switch (
                message.type
            ) {
                case "page-ready":
                    postContext();
                    break;

                case "navigate":
                    openPage(
                        message.page
                    );
                    break;

                case "open-video":
                    openExternalVideo(
                        message.url
                    );
                    break;

                case "open-external":
                    openExternalVideo(
                        message.url
                    );
                    break;

                case "check-video":
                    checkVideo(
                        message.url
                    );
                    break;

                case "get-video-formats":
                    getVideoFormats(
                        message.url
                    );
                    break;

                case "start-download":
                    startDownload(
                        message.url,
                        message.videoSelector,
                        message.audioSelector,
                        message.mode,
                        message.outputDir
                    );
                    break;

                case "cancel-download":
                    cancelDownload();
                    break;

                case "choose-download-folder":
                    chooseDownloadFolder();
                    break;

                case "open-download-folder":
                    openDownloadFolder(
                        message.path
                    );
                    break;

                case "request-download-folder":
                    getDownloadFolder();
                    break;

                case "add-to-queue":
                    if (
                        currentVideo
                    ) {
                        addToQueue(
                            currentVideo
                        );

                        postToPage({
                            type:
                                "queue-added",
                        });

                        postContext();
                    }

                    break;

                case "remove-queue":
                    removeQueueItem(
                        message.id
                    );
                    break;

                case "remove-history":
                    removeHistoryItem(
                        message.id
                    );
                    break;

                case "clear-queue":
                    saveStored(
                        "youload.queue",
                        []
                    );

                    postContext();
                    break;

                case "clear-history":
                    saveStored(
                        "youload.history",
                        []
                    );

                    postContext();
                    break;

                case "check-updates":
                case "refresh-updates":
                    checkForUpdates();
                    break;

                case "update-component":
                    updateComponent(
                        message.id
                    );
                    break;

                case "update-application":
                    updateApplication();
                    break;

                default:
                    break;
            }
        }
    );

    document.addEventListener(
        "DOMContentLoaded",
        () => {
            setupNavigation();
            setupFrame();
            setupBridge();
            loadLoadingMessages();

            document
                .getElementById("dismissNotifications")
                ?.addEventListener("click", () => {
                    toggleNotifications(false);
                });

            document
                .getElementById("notificationToggle")
                ?.addEventListener("click", () => {
                    toggleNotifications();
                });
        }
    );
})();