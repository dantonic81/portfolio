let assetToDelete = null;

// Open the delete confirmation modal when an asset card is clicked
function openDeleteModal(cardElement) {
    assetToDelete = cardElement;  // Store the clicked card element

    // Show the confirmation modal
    $('#deleteAssetModal').modal('show');
}

// Handle the delete confirmation
$('#confirmDeleteButton').on('click', function() {
    if (assetToDelete) {
        const assetId = $(assetToDelete).data('id');  // Get the ID from the clicked card

        // Send a request to the backend to delete the asset
        $.ajax({
            url: '/delete_asset',  // This is the route that handles asset deletion
            type: 'POST',
            contentType: 'application/json',  // Specify the content type as JSON
            data: JSON.stringify({ id: assetId }),  // Send the data as JSON
            success: function(response) {
                // If deletion is successful, remove the card from the UI
                if (response.success) {
                    $(assetToDelete).fadeOut(500, function() {
                        $(assetToDelete).remove();  // Remove the card from the DOM
                    });

                    // Optionally, you can show a success message or refresh the page
                    alert('Asset deleted successfully!');
                } else {
                    alert('Failed to delete the asset: ' + response.message);
                }
            },
            error: function(error) {
                // Handle any errors that occur during the deletion
                alert('An error occurred while trying to delete the asset.');
            }
        });
    }

    // Close the modal
    $('#deleteAssetModal').modal('hide');
});
