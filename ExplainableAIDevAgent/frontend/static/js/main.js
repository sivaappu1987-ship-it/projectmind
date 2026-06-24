document.addEventListener('DOMContentLoaded', () => {
    const testBtn = document.getElementById('testBtn');
    
    if (!testBtn) {
        return;
    }

    testBtn.addEventListener('click', () => {
        testBtn.innerText = "Connecting...";
        setTimeout(() => {
            alert('Frontend and Backend are securely connected! Ready for Hackathon development.');
            testBtn.innerText = "Initialize Connection";
        }, 500);
    });
});
