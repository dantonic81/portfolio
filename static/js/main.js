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
            },
            error: function(xhr, status, error) {
                console.error("Error saving asset:", error);
            }
        });
    });
});
