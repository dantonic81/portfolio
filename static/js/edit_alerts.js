// Event listener to fetch alerts when the modal is about to be shown
$('#openEditAlertsModal').on('show.bs.modal', function () {
    fetch('/api/active_alerts')  // Assuming you have an endpoint to fetch alerts
        .then(response => response.json())
        .then(data => {
            const alertListContainer = document.getElementById('alertListContainer');
            alertListContainer.innerHTML = '';  // Clear existing content

            if (data.length === 0) {
                alertListContainer.innerHTML = '<p>No active alerts.</p>';
            } else {
                data.forEach(alert => {
                    const alertDiv = document.createElement('div');
                    alertDiv.classList.add('alert', 'alert-info');
                    alertDiv.id = `alert-${alert.id}`; // Ensure each alert div has a unique ID

                    // Create the alert display and buttons
                    alertDiv.innerHTML = `
                        <strong>${alert.name}</strong><br>
                        Type: ${alert.alert_type === 'more' ? 'Above' : 'Below'} ${alert.threshold} USD<br>
                        <button class="btn btn-warning" onclick="editAlert(${alert.id})">Edit</button>
                        <button class="btn btn-danger" onclick="deleteAlert(${alert.id})">Delete</button>
                    `;
                    alertListContainer.appendChild(alertDiv);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching active alerts:', error);
        });
});

// Function to handle editing the alert
function editAlert(alertId) {
    fetch(`/api/alert/${alertId}`)
        .then(response => response.json())
        .then(data => {
            const formContainer = document.createElement('div');
            formContainer.innerHTML = `
                <form id="editAlertForm">
                    <div class="form-group">
                        <label for="alertName">Alert Name</label>
                        <input type="text" class="form-control" id="alertName" value="${data.name}" required>
                    </div>
                    <div class="form-group">
                        <label for="alertThreshold">Threshold</label>
                        <input type="number" class="form-control" id="alertThreshold" value="${data.threshold}" required>
                    </div>
                    <div class="form-group">
                        <label for="alertType">Alert Type</label>
                        <select class="form-control" id="alertType" required>
                            <option value="more" ${data.alert_type === 'more' ? 'selected' : ''}>Above</option>
                            <option value="less" ${data.alert_type === 'less' ? 'selected' : ''}>Below</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary">Save changes</button>
                </form>
            `;

            // Append the form to the modal or open a new modal to display the form
            const modalBody = document.querySelector('#openEditAlertsModal .modal-body');
            modalBody.innerHTML = '';  // Clear existing content in modal body
            modalBody.appendChild(formContainer);

            // Handle form submission for updating the alert
            const form = document.getElementById('editAlertForm');
            form.onsubmit = function(e) {
                e.preventDefault();  // Prevent form submission

                const updatedAlert = {
                    name: document.getElementById('alertName').value,
                    threshold: document.getElementById('alertThreshold').value,
                    alert_type: document.getElementById('alertType').value
                };

                // Send updated data to the backend
                fetch(`/api/alert/${alertId}`, {
                    method: 'PUT',  // Assuming PUT method for updating
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(updatedAlert)
                })
                .then(response => response.json())
                .then(updatedAlertData => {
                    console.log('Updated alert:', updatedAlertData);
                    $('#openEditAlertsModal').modal('hide');  // Close the modal after successful update
                    // Optionally, re-fetch active alerts to refresh the list
                    $('#openEditAlertsModal').trigger('show.bs.modal');
                })
                .catch(error => {
                    console.error('Error updating alert:', error);
                });
            };
        })
        .catch(error => {
            console.error('Error fetching alert details:', error);
        });
}

// Function to handle deleting an alert
function deleteAlert(alertId) {
    if (confirm('Are you sure you want to delete this alert?')) {
        fetch(`/api/alert/${alertId}`, { method: 'DELETE' })
            .then(response => {
                if (response.ok) {
                    // Remove the alert from the UI
                    const alertDiv = document.getElementById(`alert-${alertId}`);
                    if (alertDiv) {
                        alertDiv.remove();
                    }
                } else {
                    alert('Error deleting alert.');
                }
            })
            .catch(error => {
                console.error('Error deleting alert:', error);
            });
    }
}
