(() => {
    let installPrompt = null;

    const button = document.getElementById("install-app-button");
    const status = document.getElementById("install-app-status");

    if (!button || !status) return;

    const isStandalone = () =>
        window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true;

    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

    if (isStandalone()) {
        button.hidden = true;
    } else if (isIOS) {
        button.hidden = false;
        button.textContent = "How to Install";
    }

    window.addEventListener("beforeinstallprompt", (event) => {
        event.preventDefault();
        installPrompt = event;

        if (!isStandalone()) {
            button.hidden = false;
            button.textContent = "Install App";
        }
    });

    button.addEventListener("click", async () => {
        if (isStandalone()) {
            status.textContent = "Umuotuto Registry is already installed.";
            button.hidden = true;
            return;
        }

        if (installPrompt) {
            const prompt = installPrompt;
            installPrompt = null;

            try {
                await prompt.prompt();
                const result = await prompt.userChoice;

                status.textContent = result.outcome === "accepted"
                    ? "You accepted the installation prompt."
                    : "Installation cancelled. You can try again later.";
            } catch (error) {
                console.error("PWA installation failed:", error);
                status.textContent =
                    "Installation was unavailable. Try your browser menu.";
            }

            return;
        }

        if (isIOS) {
            status.textContent =
                "In Safari, tap Share, choose Add to Home Screen, then tap Add.";
        } else {
            status.textContent =
                "Open your browser menu and look for Install app or Add to Home Screen.";
        }
    });

    window.addEventListener("appinstalled", () => {
        button.hidden = true;
        status.textContent = "Umuotuto Registry was installed successfully.";
        installPrompt = null;
    });

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => {
            navigator.serviceWorker.register("/service-worker.js")
                .catch((error) => {
                    console.error("Service worker registration failed:", error);
                });
        });
    }
})();
