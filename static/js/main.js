$(document).ready(function() {
    $('#addAssetForm').submit(function(event) {
        event.preventDefault();  // Prevent the form from submitting normally

        // Log to verify that the event is triggered
        console.log("Form submitted");

        // Send the form data via AJAX or handle it as needed
        var formData = {
            name: $('#asset-name').val(),
            abbreviation: $('#asset-abbreviation').val(),
            amount: $('#asset-amount').val()
        };

        console.log(formData);

        $.ajax({
            url: '/add_asset',  // Adjust to your correct route
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(response) {
                console.log("Asset saved:", response);

                // Close the modal after success
                $('#addAssetModal').modal('hide');  // Make sure this targets the correct modal

                // Show success message
                showSuccessMessage("Asset successfully added!");

                // Redirect to the previous page after a short delay
                setTimeout(function() {
                    window.location.href = document.referrer;  // Redirects to the previous page
                }, 3000);  // Wait for 3 seconds before redirecting
            },
            error: function(xhr, status, error) {
                console.error("Error saving asset:", error);
            }
        });
    });

    // Function to show the success message
    function showSuccessMessage(message) {
        var successMessage = $('<div>')
            .addClass('alert alert-success')
            .text(message)
            .appendTo('body')
            .fadeIn(500)
            .delay(2000)  // Display for 2 seconds
            .fadeOut(500, function() {
                $(this).remove();  // Remove the success message after fading out
            });
    }
});
