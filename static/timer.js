const Key = "{{ key }}";
let timerInterval;

function updateTimer() {
    clearInterval(timerInterval);

    timerInterval = setInterval(() => {
        fetch(`/get_timer/${Key}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    clearInterval(timerInterval);
                    alert(data.error);
                } else {
                    const time = Math.round(data.remaining_time);
                    const hours = Math.floor(time / 3600);
                    const minutes = Math.floor((time % 3600) / 60);
                    const seconds = time % 60;
                    document.getElementById('timer').innerText = `Remaining Time: ${hours}h ${minutes}m ${seconds}s`;
                    if (!data.running) {
                        clearInterval(timerInterval);
                    }
                }
            });
    }, 1000);
}

function stopTimer() {
    fetch(`/stop_timer/${Key}`, {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            clearInterval(timerInterval);
            document.getElementById('timer').innerText = 'Timer stopped';
        }
    });
}

updateTimer();
