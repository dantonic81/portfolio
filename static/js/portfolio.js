let assetToDelete = null;

// Open the delete confirmation modal when an asset card is clicked
$('.asset-card').on('click', function() {
    // Store the clicked card element
    assetToDelete = $(this);

    const assetId = $(this).data('id');  // Get the ID from the clicked card
    console.log('Asset ID:', assetId);  // Check if the ID is correct

    if (!assetId) {
        console.error("Asset ID is missing or invalid.");
        return;  // Prevent further action if ID is missing
    }

    // Store the assetId into the modal's confirm delete button (or use elsewhere)
    $('#confirmDeleteButton').data('id', assetId);  // Store the ID in the button's data attribute

    // Show the confirmation modal
    $('#deleteAssetModal').modal('show');
});

// Handle the delete confirmation
$('#confirmDeleteButton').on('click', function() {
    const assetId = $(this).data('id');  // Retrieve the asset ID from the button's data attribute

    if (!assetId) {
        console.error("Asset ID is missing.");
        return;  // Prevent deletion if ID is missing
    }

    // Send a request to the backend to delete the asset
    $.ajax({
        url: '/delete_asset',  // This is the route that handles asset deletion
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ id: assetId }),  // Ensure the ID is passed correctly as JSON
        success: function(response) {
            if (response.success) {
                // If deletion is successful, remove the card from the UI
                $(assetToDelete).fadeOut(500, function() {
                    $(assetToDelete).remove();  // Remove the card from the DOM
                });
                alert('Asset deleted successfully!');
            } else {
                alert(response.message || 'Failed to delete the asset.');
            }
        },
        error: function(error) {
            console.error('Error while deleting asset:', error);
            alert('Failed to delete the asset.');
        }
    });

    // Close the modal
    $('#deleteAssetModal').modal('hide');
});
