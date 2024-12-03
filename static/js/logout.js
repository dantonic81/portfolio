document.getElementById('logout-btn').addEventListener('click', function(event) {
    event.preventDefault();  // Prevents the default link behavior

    // Send a POST request to the logout endpoint
    fetch('/logout', {
        method: 'POST',
        credentials: 'same-origin'  // Ensure session cookies are sent with the request
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);  // Optionally notify the user that they are logged out
        window.location.href = '/login';  // Redirect to the login page
    })
    .catch(error => {
        console.error('Logout failed', error);
    });
});
