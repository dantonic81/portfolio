// Function to update the unread notifications count
function updateUnreadCount() {
  fetch('/notifications/unread-count')
    .then(response => response.json())
    .then(data => {
      const unreadCount = data.unread_count;
      const badge = document.getElementById('unread-count');

      if (unreadCount > 0) {
        badge.textContent = unreadCount;
        badge.style.display = 'inline';  // Make the badge visible
      } else {
        badge.style.display = 'none';  // Hide the badge if no unread notifications
      }
    })
    .catch(error => {
      console.error('Error fetching unread notifications:', error);
    });
}

// Call the function to update the count when the page loads
window.addEventListener('load', updateUnreadCount);

// Fetch notifications and display them in the modal
document.getElementById('notification-bell').addEventListener('click', function(event) {
  event.preventDefault();  // Prevent default behavior, like page navigation

  // Open the modal with the list of notifications
  fetch('/notifications')
    .then(response => response.json())
    .then(notifications => {
      const notificationList = document.getElementById('notification-list');
      notificationList.innerHTML = '';  // Clear existing list

      notifications.forEach(notification => {
        const listItem = document.createElement('li');
        // Use the notification_text for the list item
        listItem.textContent = notification.notification_text;  // Display the notification message
        notificationList.appendChild(listItem);
      });

      // Show the modal
      document.getElementById('notification-modal').style.display = 'block';
    })
    .catch(error => {
      console.error('Error fetching notifications:', error);
    });
});
// Close the modal when the close button is clicked
document.getElementById('close-modal').addEventListener('click', function() {
  document.getElementById('notification-modal').style.display = 'none';
});

// Close the modal when the user clicks outside the modal
window.addEventListener('click', function(event) {
  const modal = document.getElementById('notification-modal');
  if (event.target === modal) {
    modal.style.display = 'none';
  }
});
