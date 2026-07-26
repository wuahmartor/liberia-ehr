document.addEventListener("alpine:init", () => {
    Alpine.data("ehrShell", () => ({
        mobileMenuOpen: false,
        profileOpen: false,
        patientSidebarOpen: false,
    }));
});

document.body.addEventListener("htmx:responseError", () => {
    console.error("The EHR request could not be completed.");
});
