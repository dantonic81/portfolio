// Fetch and render active alerts
function fetchAndRenderAlerts() {
    const alertListContainer = document.getElementById('alertListContainer');

    // Clear existing content
    alertListContainer.innerHTML = '<p>Loading alerts...</p>';

    fetch('/api/active_alerts')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            alertListContainer.innerHTML = ''; // Clear loading message

            if (data.length === 0) {
                alertListContainer.innerHTML = '<p>No active alerts.</p>';
            } else {
                data.forEach(alert => {
                    const alertDiv = document.createElement('div');
                    alertDiv.classList.add('alert', 'alert-info');
                    alertDiv.id = `alert-${alert.id}`;

                    // Check if created_at exists and format it
                    let createdAtFormatted = '';
                    if (alert.created_at) {
                        createdAtFormatted = new Date(alert.created_at).toLocaleString();
                    } else {
                        createdAtFormatted = 'Unknown date';
                    }

                    alertDiv.innerHTML = `
                        <div class="alert-header">
                            <span class="alert-title">${alert.name}</span>
                            <button class="btn btn-danger" onclick="deleteAlert(${alert.id})">Delete</button>
                        </div>
                        <div class="alert-type">
                            <strong>Type:</strong> ${alert.alert_type === 'more' ? 'More than' : 'Less than'} ${alert.threshold} USD
                        </div>
                        <div class="alert-date">
                            <strong>Created at:</strong> ${createdAtFormatted}
                        </div>
                    `;
                    console.log(alert);
                    alertListContainer.appendChild(alertDiv);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching active alerts:', error);
            alertListContainer.innerHTML = '<p>Error loading alerts. Please try again later.</p>';
        });
}

// Delete an alert
function deleteAlert(alertId) {
    if (confirm('Are you sure you want to delete this alert?')) {
        fetch(`/api/alert/${alertId}`, { method: 'DELETE' })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                fetchAndRenderAlerts(); // Refresh the alert list
            })
            .catch(error => {
                console.error('Error deleting alert:', error);
                alert('Failed to delete alert. Please try again later.');
            });
        alert('Alert deleted successfully!');
    }
}

// Listen for when the modal is shown, and fetch active alerts
$('#openEditAlertsModal').on('shown.bs.modal', function () {
    fetchAndRenderAlerts(); // Fetch and render alerts when the modal is shown
});
