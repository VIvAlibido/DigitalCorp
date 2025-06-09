console.log("Script loaded");

document.addEventListener('DOMContentLoaded', function() {
    const banner = document.getElementById('cookie-consent-banner');
    const acceptButton = document.getElementById('accept-cookies');

    // Check if consent was already given
    if (banner && !getCookie('user_consent')) { // check if banner exists
        banner.style.display = 'block';
    }

    if (acceptButton) { // check if acceptButton exists
        acceptButton.addEventListener('click', function() {
            setCookie('user_consent', 'true', 365); // Cookie expires in 365 days
            if (banner) banner.style.display = 'none';
        });
    }


    function setCookie(name, value, days) {
        let expires = "";
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days*24*60*60*1000));
            expires = "; expires=" + date.toUTCString();
        }
        document.cookie = name + "=" + (value || "")  + expires + "; path=/";
    }

    function getCookie(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for(let i=0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0)==' ') c = c.substring(1,c.length);
            if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
        }
        return null;
    }
});
